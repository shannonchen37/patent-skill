from __future__ import annotations

import hashlib
import json
import re
import subprocess
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Any

from .scanner import scan_repository


class CaseStage(StrEnum):
    PROJECT_SNAPSHOT = "PROJECT_SNAPSHOT"
    EVIDENCE_MAP = "EVIDENCE_MAP"
    INVENTION_CANDIDATES = "INVENTION_CANDIDATES"
    FIRST_SEARCH = "FIRST_SEARCH"
    CANDIDATE_RANKING = "CANDIDATE_RANKING"
    FEATURE_MATRIX = "FEATURE_MATRIX"
    CLAIMS_V1 = "CLAIMS_V1"
    SPECIFICATION_V1 = "SPECIFICATION_V1"
    SUPPORT_CANDIDATES = "SUPPORT_CANDIDATES"
    CLAIMS_V2 = "CLAIMS_V2"
    CLAIM_SUPPORT_MAP = "CLAIM_SUPPORT_MAP"
    FINAL_SEARCH = "FINAL_SEARCH"
    FINAL_AUDIT = "FINAL_AUDIT"
    CONTENT_READY_FOR_ATTORNEY_REVIEW = "CONTENT_READY_FOR_ATTORNEY_REVIEW"
    INDEPENDENT_AUDIT = "INDEPENDENT_AUDIT"
    DOCX_PACKAGE_RENDERED = "DOCX_PACKAGE_RENDERED"


CASE_STAGE_ORDER = list(CaseStage)
SNAPSHOT_TYPES = {"git_commit", "uploaded_archive", "directory_manifest"}
SEARCH_FIELDS = {
    "database",
    "search_date",
    "query",
    "candidate_id",
    "result_count",
    "reviewed_reference_ids",
    "verified_urls",
    "coverage_limitations",
}
REQUIRED_DOCX_SUBJECTS = (
    "技术交底书",
    "权利要求书",
    "说明书",
    "说明书摘要",
    "说明书附图",
    "摘要附图",
    "初步查新",
    "请求书信息确认",
    "提交文件清单",
)

CONTEXT_LEDGER = """# 上下文确认记录

## 技术内容待确认问题

| 优先级 | 当前证据 | 不确定内容 | 对保护范围的影响 | 状态 |
|---|---|---|---|---|

## 申请与法律背景待确认问题

> 公开日期、贡献人和申请主体等信息可稍后补充；除非直接影响当前判断，否则不阻断技术内容工作。

| 问题 | 当前状态 | 最晚确认阶段 |
|---|---|---|
| 公开历史 | 待确认 | 提交前 |
| 核心技术贡献人 | 待确认 | 提交前 |

## 已确认事实

| 日期 | 事实 | 来源 | 影响文档 |
|---|---|---|---|
"""

ARTIFACT_TEMPLATES = {
    CaseStage.EVIDENCE_MAP: (
        "01-code-evidence-map.md",
        """# 技术证据地图

> 当前阶段只记录代码证据、处理步骤、数据或状态变化及技术效果，不写权利要求。

| 证据编号 | 代码/文档证据 | 处理步骤 | 数据或状态变化 | 技术效果 | 证据状态 |
|---|---|---|---|---|---|
""",
    ),
    CaseStage.INVENTION_CANDIDATES: (
        "02-invention-candidates.md",
        """# 候选发明

> 从技术证据地图提取 3–5 个完整候选。先检索全部候选，再决定主发明。

| 候选 | 技术问题 | 核心技术机制 | 关键区别特征 | 技术效果 | 代码证据 | 主要风险 |
|---|---|---|---|---|---|---|
""",
    ),
    CaseStage.CANDIDATE_RANKING: (
        "02-candidate-ranking.json",
        json.dumps(
            {
                "ranked_candidates": [],
                "selected_candidate_id": "",
                "strategic_ambiguity": False,
                "human_confirmation_required": False,
                "human_confirmation": "",
                "selection_reason": "",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
    ),
    CaseStage.FEATURE_MATRIX: (
        "04-feature-matrix.md",
        """# 区别特征矩阵

| 技术特征 | 工程证据 | D1 | D2 | D3 | 区别与技术效果 |
|---|---|---|---|---|---|
""",
    ),
    CaseStage.CLAIMS_V1: (
        "05-claims-v1.md",
        "# Claims V1\n\n> 每项限定必须回溯到技术证据地图。\n",
    ),
    CaseStage.SPECIFICATION_V1: (
        "06-specification-v1.md",
        "# 说明书 V1\n\n"
        "> 围绕 Claims V1 补充替代方案、参数、数据结构、模块交互、"
        "异常路径和部署方式。\n",
    ),
    CaseStage.SUPPORT_CANDIDATES: (
        "07-support-candidates.md",
        """# 支持候选

> 这是 Claims V2 起草前的候选支持池，不是最终 claim-support map。

| 候选限定 | 工程来源 | 说明书候选段落 | 技术效果 | 风险/待确认 |
|---|---|---|---|---|
""",
    ),
    CaseStage.CLAIMS_V2: (
        "08-claims-v2.md",
        "# Claims V2\n\n"
        "> 在完整说明书和支持候选池基础上修订。为每个独立权利要求限定"
        "添加内部追踪标记，如 `[I1-L1]`；DOCX 输出时移除标记。\n",
    ),
    CaseStage.CLAIM_SUPPORT_MAP: (
        "09-claim-support-map.md",
        """# 权利要求支持映射

| Claims V2 独立权利要求限定 | 工程来源 | 说明书明确支持 | 技术效果 | 状态 |
|---|---|---|---|---|
""",
    ),
    CaseStage.FINAL_AUDIT: (
        "11-final-audit.md",
        """# 最终审计

## 新颖性

## 创造性

## 专利客体

## 清楚性与支持性

## 充分公开

## 单一性与拆案

## 修改依据

## 敏感信息
""",
    ),
}


def init_case_workspace(case_dir: Path, project: Path, title: str = "") -> dict[str, Any]:
    case_dir = case_dir.resolve()
    project = project.resolve()
    if not project.exists() or not (project.is_dir() or zipfile.is_zipfile(project)):
        raise ValueError(f"Project directory or ZIP archive not found: {project}")
    status_path = case_dir / "case-status.json"
    if status_path.exists():
        raise ValueError(f"Patent case already exists: {case_dir}")

    snapshot_dir = case_dir / "00-project-snapshot"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    snapshot = _create_snapshot(project)
    _write_json(snapshot_dir / "snapshot-manifest.json", snapshot)
    (snapshot_dir / "README.md").write_text(
        "# 专利证据版本\n\n该清单冻结本案分析所依据的工程材料。"
        "snapshot_type 可为 git_commit、uploaded_archive 或 directory_manifest。\n",
        encoding="utf-8",
    )
    (snapshot_dir / "disclosure-history.md").write_text(
        "# 公开历史（申请与法律背景，技术内容阶段可待确认）\n\n"
        "- 项目开始时间：【待确认】\n- 核心机制首次实现时间：【待确认】\n"
        "- 首次公开时间与范围：【待确认】\n",
        encoding="utf-8",
    )
    (snapshot_dir / "contributors.md").write_text(
        "# 核心技术贡献人（提交前确认）\n\n"
        "| 姓名 | 实质性技术贡献 | 证据 | 是否拟列发明人 |\n|---|---|---|---|\n",
        encoding="utf-8",
    )
    (case_dir / "context-ledger.md").write_text(CONTEXT_LEDGER, encoding="utf-8")

    now = datetime.now(UTC).isoformat()
    status = {
        "canonical_source": "patent-skill",
        "case_dir": str(case_dir),
        "project_source": str(project),
        "proposed_title": title,
        "current_stage": CaseStage.PROJECT_SNAPSHOT.value,
        "technical_questions_open": True,
        "filing_context_questions_open": True,
        "stage_history": [{"stage": CaseStage.PROJECT_SNAPSHOT.value, "entered_at": now}],
        "external_roles": {
            "yjmm10/patent-skills": "CNIPA_SEARCH_ONLY",
            "HuangXinzhe/cn-patent-drafting": "INDEPENDENT_AUDIT_AND_DOCX_ONLY",
        },
    }
    _write_json(status_path, status)
    return {"status": status, "snapshot": snapshot}


def advance_stage(
    case_dir: Path,
    target_stage: str,
    *,
    confirmation: str = "",
    close_technical_questions: bool = False,
) -> dict[str, Any]:
    case_dir = case_dir.resolve()
    status = _load_status(case_dir)
    history_errors = _validate_history(status)
    if history_errors:
        raise ValueError("Case state is not advanceable: " + "; ".join(history_errors))
    if target_stage == "FILING_READY":
        raise ValueError("FILING_READY is never a patent-skill state")
    try:
        current = CaseStage(status["current_stage"])
        target = CaseStage(target_stage)
    except ValueError as exc:
        raise ValueError(f"Unknown case stage: {target_stage}") from exc
    expected_index = CASE_STAGE_ORDER.index(current) + 1
    if expected_index >= len(CASE_STAGE_ORDER) or CASE_STAGE_ORDER[expected_index] != target:
        expected = (
            CASE_STAGE_ORDER[expected_index].value
            if expected_index < len(CASE_STAGE_ORDER)
            else "none"
        )
        raise ValueError(
            f"Illegal stage transition {current.value} -> {target.value}; expected {expected}"
        )

    if target == CaseStage.FEATURE_MATRIX:
        ranking = _load_json(case_dir / "02-candidate-ranking.json", "candidate ranking")
        if confirmation:
            ranking["human_confirmation"] = confirmation
            _write_json(case_dir / "02-candidate-ranking.json", ranking)
    errors = _validate_stage(case_dir, status, current)
    if errors:
        raise ValueError("Current stage gate failed: " + "; ".join(errors))
    if close_technical_questions:
        status["technical_questions_open"] = False
    if target == CaseStage.CONTENT_READY_FOR_ATTORNEY_REVIEW and status.get(
        "technical_questions_open"
    ):
        raise ValueError("Technical content questions remain open")
    if target == CaseStage.DOCX_PACKAGE_RENDERED:
        docx_errors = _validate_docx_package(case_dir, status)
        if docx_errors:
            raise ValueError("DOCX render gate failed: " + "; ".join(docx_errors))

    status["current_stage"] = target.value
    status.setdefault("stage_history", []).append(
        {"stage": target.value, "entered_at": datetime.now(UTC).isoformat()}
    )
    _prepare_stage_artifact(case_dir, target)
    _write_json(case_dir / "case-status.json", status)
    return status


def validate_case_workspace(case_dir: Path) -> list[str]:
    case_dir = case_dir.resolve()
    status_path = case_dir / "case-status.json"
    if not status_path.exists():
        return ["Missing case artifact: case-status.json"]
    try:
        status = _load_json(status_path, "case status")
    except ValueError as exc:
        return [str(exc)]
    errors: list[str] = []
    if status.get("canonical_source") != "patent-skill":
        errors.append("canonical_source must be patent-skill")
    if status.get("current_stage") == "FILING_READY":
        errors.append("FILING_READY cannot be set by this tool")
        return errors
    try:
        current = CaseStage(status.get("current_stage", ""))
    except ValueError:
        errors.append(f"Unknown current_stage: {status.get('current_stage')}")
        return errors

    errors.extend(_validate_history(status))
    for stage in CASE_STAGE_ORDER[: CASE_STAGE_ORDER.index(current) + 1]:
        errors.extend(_validate_stage(case_dir, status, stage))
    return _dedupe(errors)


def _validate_stage(case_dir: Path, status: dict[str, Any], stage: CaseStage) -> list[str]:
    validators: dict[CaseStage, Callable[[Path, dict[str, Any]], list[str]]] = {
        CaseStage.PROJECT_SNAPSHOT: _validate_snapshot,
        CaseStage.EVIDENCE_MAP: lambda root, _: _validate_table(
            root / "01-code-evidence-map.md", 1
        ),
        CaseStage.INVENTION_CANDIDATES: lambda root, _: _validate_table(
            root / "02-invention-candidates.md", 3, 5
        ),
        CaseStage.FIRST_SEARCH: lambda root, _: _validate_search(
            root / "03-prior-art-search",
            {row[0] for row in _markdown_data_rows(root / "02-invention-candidates.md") if row},
        ),
        CaseStage.CANDIDATE_RANKING: _validate_ranking,
        CaseStage.FEATURE_MATRIX: lambda root, _: _validate_table(root / "04-feature-matrix.md", 1),
        CaseStage.CLAIMS_V1: lambda root, _: _validate_draft(root / "05-claims-v1.md"),
        CaseStage.SPECIFICATION_V1: lambda root, _: _validate_draft(
            root / "06-specification-v1.md"
        ),
        CaseStage.SUPPORT_CANDIDATES: lambda root, _: _validate_table(
            root / "07-support-candidates.md", 1
        ),
        CaseStage.CLAIMS_V2: lambda root, _: _validate_draft(root / "08-claims-v2.md"),
        CaseStage.CLAIM_SUPPORT_MAP: _validate_support_map,
        CaseStage.FINAL_SEARCH: lambda root, _: _validate_search(root / "10-final-search"),
        CaseStage.FINAL_AUDIT: _validate_final_audit,
        CaseStage.CONTENT_READY_FOR_ATTORNEY_REVIEW: _validate_content_ready,
        CaseStage.INDEPENDENT_AUDIT: _validate_independent_audit,
        CaseStage.DOCX_PACKAGE_RENDERED: _validate_docx_package,
    }
    return validators[stage](case_dir, status)


def _prepare_stage_artifact(case_dir: Path, stage: CaseStage) -> None:
    if stage == CaseStage.FIRST_SEARCH:
        _prepare_search_dir(case_dir / "03-prior-art-search")
    elif stage == CaseStage.FINAL_SEARCH:
        _prepare_search_dir(case_dir / "10-final-search")
    elif stage == CaseStage.INDEPENDENT_AUDIT:
        directory = case_dir / "filing-package" / "huang-audit"
        directory.mkdir(parents=True, exist_ok=True)
        (case_dir / "filing-package" / "docx").mkdir(parents=True, exist_ok=True)
        (directory / "independent-audit.md").write_text(
            "# 独立审稿\n\n> 不得重选发明点；只审计中国专利撰写质量。\n",
            encoding="utf-8",
        )
    elif stage == CaseStage.DOCX_PACKAGE_RENDERED:
        (case_dir / "filing-package" / "docx").mkdir(parents=True, exist_ok=True)
    elif stage in ARTIFACT_TEMPLATES:
        relative, content = ARTIFACT_TEMPLATES[stage]
        path = case_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


def _prepare_search_dir(path: Path) -> None:
    (path / "shannon").mkdir(parents=True, exist_ok=True)
    (path / "yjmm10").mkdir(parents=True, exist_ok=True)
    (path / "README.md").write_text(
        "# 检索记录\n\n将结构化记录逐行写入 search-records.jsonl。"
        "每行必须包含 database、search_date、query、candidate_id、result_count、"
        "reviewed_reference_ids、verified_urls、coverage_limitations。\n",
        encoding="utf-8",
    )


def _validate_snapshot(case_dir: Path, _: dict[str, Any]) -> list[str]:
    path = case_dir / "00-project-snapshot" / "snapshot-manifest.json"
    if not path.exists():
        return ["Missing case artifact: 00-project-snapshot/snapshot-manifest.json"]
    try:
        snapshot = _load_json(path, "snapshot manifest")
    except ValueError as exc:
        return [str(exc)]
    errors = []
    if snapshot.get("snapshot_type") not in SNAPSHOT_TYPES:
        errors.append("snapshot_type must be git_commit, uploaded_archive, or directory_manifest")
    if not re.fullmatch(r"[0-9a-f]{64}", str(snapshot.get("snapshot_sha256", ""))):
        errors.append("Snapshot must contain snapshot_sha256")
    if not isinstance(snapshot.get("files"), list):
        errors.append("Snapshot must contain a files list")
    elif any(not item.get("sha256") for item in snapshot["files"]):
        errors.append("Every snapshot file must contain sha256")
    elif snapshot.get("file_count") != len(snapshot["files"]):
        errors.append("Snapshot file_count must equal the files list length")
    if snapshot.get("snapshot_type") == "git_commit" and not snapshot.get("git", {}).get("head"):
        errors.append("git_commit snapshot must contain Git HEAD")
    if snapshot.get("snapshot_type") == "uploaded_archive" and not snapshot.get("archive_sha256"):
        errors.append("uploaded_archive snapshot must contain archive_sha256")
    return errors


def _validate_table(path: Path, minimum: int, maximum: int | None = None) -> list[str]:
    if not path.exists():
        return [f"Missing case artifact: {path.name}"]
    rows = _markdown_data_rows(path)
    if len(rows) < minimum:
        return [f"{path.name} requires at least {minimum} completed data row(s)"]
    if maximum is not None and len(rows) > maximum:
        return [f"{path.name} permits at most {maximum} candidate rows"]
    return []


def _validate_search(path: Path, required_candidate_ids: set[str] | None = None) -> list[str]:
    records_path = path / "search-records.jsonl"
    if not records_path.exists():
        return [f"Missing structured search log: {records_path.relative_to(path.parent)}"]
    errors: list[str] = []
    records = []
    for line_number, line in enumerate(records_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"Invalid search JSON at line {line_number}")
            continue
        missing = sorted(SEARCH_FIELDS - record.keys())
        if missing:
            errors.append(f"Search line {line_number} missing fields: {', '.join(missing)}")
        if not isinstance(record.get("reviewed_reference_ids"), list):
            errors.append(f"Search line {line_number} reviewed_reference_ids must be a list")
        if not isinstance(record.get("verified_urls"), list):
            errors.append(f"Search line {line_number} verified_urls must be a list")
        records.append(record)
    if not records:
        errors.append("Structured search log must contain at least one record")
    if required_candidate_ids:
        searched = {str(record.get("candidate_id", "")) for record in records}
        missing_candidates = sorted(required_candidate_ids - searched)
        if missing_candidates:
            errors.append(
                "First search does not cover candidates: " + ", ".join(missing_candidates)
            )
    return errors


def _validate_ranking(case_dir: Path, _: dict[str, Any]) -> list[str]:
    path = case_dir / "02-candidate-ranking.json"
    if not path.exists():
        return ["Missing case artifact: 02-candidate-ranking.json"]
    try:
        ranking = _load_json(path, "candidate ranking")
    except ValueError as exc:
        return [str(exc)]
    errors = []
    if not ranking.get("ranked_candidates"):
        errors.append("Candidate ranking must include ranked_candidates")
    if not ranking.get("selected_candidate_id"):
        errors.append("Candidate ranking must select a candidate")
    ranked_ids = {
        item.get("candidate_id") if isinstance(item, dict) else item
        for item in ranking.get("ranked_candidates", [])
    }
    if ranking.get("selected_candidate_id") not in ranked_ids:
        errors.append("selected_candidate_id must appear in ranked_candidates")
    ambiguous = ranking.get("strategic_ambiguity")
    required = ranking.get("human_confirmation_required")
    if not isinstance(ambiguous, bool) or not isinstance(required, bool):
        errors.append("Ranking ambiguity and confirmation flags must be boolean")
    elif ambiguous != required:
        errors.append("human_confirmation_required must equal strategic_ambiguity")
    if ambiguous and not ranking.get("human_confirmation"):
        errors.append("Strategically ambiguous ranking requires human_confirmation")
    return errors


def _validate_draft(path: Path) -> list[str]:
    if not path.exists():
        return [f"Missing case artifact: {path.name}"]
    meaningful = [
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith(("#", ">"))
    ]
    return [] if meaningful else [f"{path.name} has no draft content"]


def _validate_support_map(case_dir: Path, _: dict[str, Any]) -> list[str]:
    path = case_dir / "09-claim-support-map.md"
    table_errors = _validate_table(path, 1)
    if table_errors:
        return table_errors
    claims_path = case_dir / "08-claims-v2.md"
    labels = (
        set(re.findall(r"\[(I\d+-L\d+)\]", claims_path.read_text(encoding="utf-8")))
        if claims_path.exists()
        else set()
    )
    errors = []
    if not labels:
        errors.append("Claims V2 must label every independent-claim limitation with [I<n>-L<n>]")
    mapped_labels: set[str] = set()
    for row_number, cells in enumerate(_markdown_data_rows(path), 1):
        if len(cells) < 5 or any(not cell.strip() for cell in cells[:5]):
            errors.append(
                f"Claim support row {row_number} must map limitation, engineering source, "
                "specification support, technical effect, and status"
            )
            continue
        if cells[4].strip().lower() in {"unsupported", "unresolved", "待支持", "待确认", "不支持"}:
            errors.append(f"Claim support row {row_number} remains unsupported or unresolved")
        mapped_labels.update(re.findall(r"I\d+-L\d+", cells[0]))
    missing_labels = sorted(labels - mapped_labels)
    if missing_labels:
        errors.append(
            "Claim support map is missing independent-claim limitations: "
            + ", ".join(missing_labels)
        )
    return errors


def _validate_final_audit(case_dir: Path, _: dict[str, Any]) -> list[str]:
    path = case_dir / "11-final-audit.md"
    if not path.exists():
        return ["Missing case artifact: 11-final-audit.md"]
    text = path.read_text(encoding="utf-8")
    required = (
        "新颖性",
        "创造性",
        "专利客体",
        "清楚性与支持性",
        "充分公开",
        "单一性与拆案",
        "修改依据",
        "敏感信息",
    )
    errors = []
    for section in required:
        heading = f"## {section}"
        if heading not in text:
            errors.append(f"Final audit missing section: {section}")
            continue
        body = text.split(heading, 1)[1].split("\n## ", 1)[0].strip()
        if not body:
            errors.append(f"Final audit section has no conclusion: {section}")
    if "待复核" in text or "【待" in text:
        errors.append("Final audit still contains pending conclusions")
    return errors


def _validate_content_ready(_: Path, status: dict[str, Any]) -> list[str]:
    return (
        ["Technical content questions remain open"]
        if status.get("technical_questions_open")
        else []
    )


def _validate_independent_audit(case_dir: Path, _: dict[str, Any]) -> list[str]:
    return _validate_draft(case_dir / "filing-package" / "huang-audit" / "independent-audit.md")


def _validate_docx_package(case_dir: Path, _: dict[str, Any]) -> list[str]:
    path = case_dir / "filing-package" / "docx"
    names = [item.name for item in path.glob("*.docx")] if path.exists() else []
    return [
        f"Missing rendered DOCX subject: {subject}"
        for subject in REQUIRED_DOCX_SUBJECTS
        if not any(subject in name for name in names)
    ]


def _create_snapshot(project: Path) -> dict[str, Any]:
    if project.is_file():
        return _archive_snapshot(project)
    scan = scan_repository(project)
    files = [_file_record(project, item) for item in scan["files"]]
    git = _git_snapshot(project)
    snapshot_type = (
        "git_commit"
        if git.get("is_repository") and git.get("worktree_clean")
        else "directory_manifest"
    )
    digest = _manifest_digest(files)
    return {
        "snapshot_type": snapshot_type,
        "captured_at": datetime.now(UTC).isoformat(),
        "project_source": str(project),
        "snapshot_sha256": digest,
        "manifest_sha256": digest,
        "git": git,
        "file_count": scan["file_count"],
        "languages": scan["languages"],
        "security_warnings": scan["security_warnings"],
        "files": files,
    }


def _archive_snapshot(project: Path) -> dict[str, Any]:
    files = []
    with zipfile.ZipFile(project) as archive:
        for info in sorted(archive.infolist(), key=lambda item: item.filename):
            name = PurePosixPath(info.filename)
            if info.is_dir() or name.is_absolute() or ".." in name.parts:
                continue
            content = archive.read(info)
            files.append(
                {
                    "path": str(name),
                    "size": info.file_size,
                    "sha256": hashlib.sha256(content).hexdigest(),
                }
            )
    archive_sha = hashlib.sha256(project.read_bytes()).hexdigest()
    return {
        "snapshot_type": "uploaded_archive",
        "captured_at": datetime.now(UTC).isoformat(),
        "project_source": str(project),
        "snapshot_sha256": archive_sha,
        "archive_sha256": archive_sha,
        "manifest_sha256": _manifest_digest(files),
        "file_count": len(files),
        "languages": {},
        "security_warnings": [],
        "files": files,
    }


def _git_snapshot(project: Path) -> dict[str, Any]:
    def run(*args: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(project), *args], check=False, capture_output=True, text=True
        )
        return completed.stdout.strip() if completed.returncode == 0 else ""

    head = run("rev-parse", "--verify", "HEAD")
    if not head:
        return {"is_repository": False}
    status = run("status", "--porcelain")
    return {
        "is_repository": True,
        "head": head,
        "branch": run("branch", "--show-current"),
        "exact_tag": run("describe", "--tags", "--exact-match", "HEAD"),
        "origin": run("remote", "get-url", "origin"),
        "worktree_clean": not bool(status),
        "worktree_status": status.splitlines(),
    }


def _file_record(project: Path, item: dict[str, Any]) -> dict[str, Any]:
    path = project / item["path"]
    return {**item, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def _manifest_digest(files: list[dict[str, Any]]) -> str:
    normalized = "\n".join(
        f"{item['path']}\0{item['sha256']}" for item in sorted(files, key=lambda row: row["path"])
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _markdown_data_rows(path: Path) -> list[list[str]]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and all(set(cell) <= {"-", ":", " "} for cell in cells):
            continue
        rows.append(cells)
    return rows[1:] if rows else []


def _load_status(case_dir: Path) -> dict[str, Any]:
    return _load_json(case_dir / "case-status.json", "case status")


def _validate_history(status: dict[str, Any]) -> list[str]:
    try:
        current = CaseStage(status.get("current_stage", ""))
    except ValueError:
        return [f"Unknown current_stage: {status.get('current_stage')}"]
    history = [
        entry.get("stage") for entry in status.get("stage_history", []) if isinstance(entry, dict)
    ]
    expected = [stage.value for stage in CASE_STAGE_ORDER[: CASE_STAGE_ORDER.index(current) + 1]]
    return (
        []
        if history == expected
        else ["stage_history must be the exact ordered prefix ending at current_stage"]
    )


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.exists():
        raise ValueError(f"Missing {label}: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid {label}: {exc}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Invalid {label}: expected an object")
    return value


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
