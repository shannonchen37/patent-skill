from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from collections.abc import Callable
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path, PurePosixPath
from typing import Any
from xml.etree import ElementTree

from .claims import (
    independent_claim_numbers,
    parse_claim_blocks,
    validate_abstract_cn,
    validate_claims_cn,
)
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
    APPLICATION_DRAFT = "APPLICATION_DRAFT"
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
FINAL_SEARCH_FIELDS = {"claim_id", "limitation_ids", "search_scope"}
FINAL_SEARCH_SCOPES = {"claim_combination", "distinguishing_limitation"}
TRACE_LABEL_RE = re.compile(r"\[(I\d+-L\d+)\]")
TRACE_LINE_RE = re.compile(r"^[；;、]?\s*\[(I\d+-L\d+)\]\s*(.+)$")
MIN_DOCX_SIZE = 1024
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

STAGE_ARTIFACTS: dict[CaseStage, tuple[str, ...]] = {
    CaseStage.EVIDENCE_MAP: ("01-code-evidence-map.json", "01-code-evidence-map.md"),
    CaseStage.INVENTION_CANDIDATES: (
        "02-invention-candidates.json",
        "02-invention-candidates.md",
    ),
    CaseStage.FIRST_SEARCH: ("03-prior-art-search",),
    CaseStage.CANDIDATE_RANKING: ("02-candidate-ranking.json",),
    CaseStage.FEATURE_MATRIX: ("04-feature-matrix.json", "04-feature-matrix.md"),
    CaseStage.CLAIMS_V1: ("05-claims-v1.md",),
    CaseStage.SPECIFICATION_V1: ("06-specification-v1.md",),
    CaseStage.SUPPORT_CANDIDATES: ("07-support-candidates.md",),
    CaseStage.CLAIMS_V2: ("08-claims-v2.md", "08-claims-v2-structure.json"),
    CaseStage.CLAIM_SUPPORT_MAP: ("09-claim-support-map.md",),
    CaseStage.FINAL_SEARCH: ("10-final-search",),
    CaseStage.APPLICATION_DRAFT: ("12-application",),
    CaseStage.FINAL_AUDIT: ("13-final-audit.json", "13-final-audit.md"),
    CaseStage.INDEPENDENT_AUDIT: ("filing-package",),
}

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
        "单独换行并添加内部追踪标记，如 `[I1-L1]`；DOCX 输出时移除标记。\n",
    ),
    CaseStage.CLAIM_SUPPORT_MAP: (
        "09-claim-support-map.md",
        """# 权利要求支持映射

| Claims V2 独立权利要求限定 | 工程来源 | 说明书明确支持 | 技术效果 | 状态 |
|---|---|---|---|---|
""",
    ),
    CaseStage.FINAL_AUDIT: (
        "13-final-audit.md",
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
        "revision": 0,
        "revision_history": [],
        "stage_history": [
            {
                "stage": CaseStage.PROJECT_SNAPSHOT.value,
                "entered_at": now,
                "event": "initialize",
                "revision": 0,
            }
        ],
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
        {
            "stage": target.value,
            "entered_at": datetime.now(UTC).isoformat(),
            "event": "advance",
            "revision": status.get("revision", 0),
        }
    )
    _prepare_stage_artifact(case_dir, target)
    _write_json(case_dir / "case-status.json", status)
    return status


def revise_case_stage(case_dir: Path, target_stage: str, reason: str) -> dict[str, Any]:
    case_dir = case_dir.resolve()
    status = _load_status(case_dir)
    history_errors = _validate_history(status)
    if history_errors:
        raise ValueError("Case state is not revisable: " + "; ".join(history_errors))
    if not reason.strip():
        raise ValueError("A substantive revision reason is required")
    try:
        current = CaseStage(status["current_stage"])
        target = CaseStage(target_stage)
    except ValueError as exc:
        raise ValueError(f"Unknown case stage: {target_stage}") from exc
    if target == CaseStage.PROJECT_SNAPSHOT:
        raise ValueError("Project snapshot cannot be reopened; initialize a new case instead")
    if CASE_STAGE_ORDER.index(target) >= CASE_STAGE_ORDER.index(current):
        raise ValueError("Revision target must be earlier than the current stage")

    revision = int(status.get("revision", 0)) + 1
    revision_id = f"R{revision:03d}"
    revision_dir = case_dir / "revisions" / revision_id
    if revision_dir.exists():
        raise ValueError(f"Revision archive already exists: {revision_id}")
    artifact_archive = revision_dir / "artifacts"
    artifact_archive.mkdir(parents=True)
    for stage in CASE_STAGE_ORDER[CASE_STAGE_ORDER.index(target) :]:
        for relative in STAGE_ARTIFACTS.get(stage, ()):
            source = case_dir / relative
            if not source.exists():
                continue
            destination = artifact_archive / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(source), str(destination))

    created_at = datetime.now(UTC).isoformat()
    revision_record = {
        "revision_id": revision_id,
        "reopened_stage": target.value,
        "reason": reason.strip(),
        "trigger": current.value,
        "created_at": created_at,
        "archived_under": str(revision_dir.relative_to(case_dir)),
    }
    _write_json(revision_dir / "reason.json", revision_record)
    status["revision"] = revision
    status.setdefault("revision_history", []).append(revision_record)
    status["current_stage"] = target.value
    status.setdefault("stage_history", []).append(
        {
            "stage": target.value,
            "entered_at": created_at,
            "event": "revise",
            "revision": revision,
            "reason": reason.strip(),
            "trigger": current.value,
        }
    )
    _prepare_stage_artifact(case_dir, target)
    _write_json(case_dir / "case-status.json", status)
    return status


def export_case_package(case_dir: Path, output_dir: Path) -> Path:
    case_dir = case_dir.resolve()
    output_dir = output_dir.resolve()
    status = _load_status(case_dir)
    current = CaseStage(status["current_stage"])
    if CASE_STAGE_ORDER.index(current) < CASE_STAGE_ORDER.index(
        CaseStage.CONTENT_READY_FOR_ATTORNEY_REVIEW
    ):
        raise ValueError("Case content is not ready for export")
    errors = validate_case_workspace(case_dir)
    if errors:
        raise ValueError("Case export gate failed: " + "; ".join(errors))
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError(f"Export directory is not empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    for relative in (
        "12-application/claims-final.md",
        "12-application/specification-final.md",
        "12-application/abstract.md",
        "12-application/drawings-description.md",
        "12-application/application-metadata.json",
        "09-claim-support-map.md",
        "13-final-audit.md",
    ):
        source = case_dir / relative
        destination = output_dir / Path(relative).name
        shutil.copy2(source, destination)
    _write_json(
        output_dir / "export-manifest.json",
        {
            "canonical_source": "patent-skill",
            "source_case": str(case_dir),
            "source_revision": status.get("revision", 0),
            "exported_at": datetime.now(UTC).isoformat(),
            "files": [
                {
                    "path": path.name,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
                for path in sorted(output_dir.iterdir())
                if path.is_file() and path.name != "export-manifest.json"
            ],
        },
    )
    return output_dir


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
        CaseStage.CLAIMS_V1: lambda root, _: _validate_claims_stage(root / "05-claims-v1.md"),
        CaseStage.SPECIFICATION_V1: lambda root, _: _validate_draft(
            root / "06-specification-v1.md"
        ),
        CaseStage.SUPPORT_CANDIDATES: lambda root, _: _validate_table(
            root / "07-support-candidates.md", 1
        ),
        CaseStage.CLAIMS_V2: lambda root, _: _validate_claims_stage(
            root / "08-claims-v2.md",
            root / "08-claims-v2-structure.json",
        ),
        CaseStage.CLAIM_SUPPORT_MAP: _validate_support_map,
        CaseStage.FINAL_SEARCH: _validate_final_search,
        CaseStage.APPLICATION_DRAFT: _validate_application_draft,
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
    elif stage == CaseStage.APPLICATION_DRAFT:
        _prepare_application_draft(case_dir)
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
        if stage == CaseStage.CLAIMS_V2:
            _write_json(
                case_dir / "08-claims-v2-structure.json",
                {"independent_claims": []},
            )


def _prepare_search_dir(path: Path) -> None:
    (path / "shannon").mkdir(parents=True, exist_ok=True)
    (path / "yjmm10").mkdir(parents=True, exist_ok=True)
    (path / "README.md").write_text(
        "# 检索记录\n\n将结构化记录逐行写入 search-records.jsonl。"
        "每行必须包含 database、search_date、query、candidate_id、result_count、"
        "reviewed_reference_ids、verified_urls、coverage_limitations。"
        "第二次检索还必须记录 claim_id、limitation_ids 和 search_scope。\n",
        encoding="utf-8",
    )


def _prepare_application_draft(case_dir: Path) -> None:
    application = case_dir / "12-application"
    application.mkdir(parents=True, exist_ok=True)
    claims_v2 = case_dir / "08-claims-v2.md"
    claims_text = claims_v2.read_text(encoding="utf-8") if claims_v2.exists() else ""
    claims_final = TRACE_LABEL_RE.sub("", claims_text)
    (application / "claims-final.md").write_text(claims_final, encoding="utf-8")
    specification_v1 = case_dir / "06-specification-v1.md"
    specification_seed = (
        specification_v1.read_text(encoding="utf-8") if specification_v1.exists() else ""
    )
    (application / "specification-final.md").write_text(
        "# 最终说明书\n\n> 【待同步 Claims V2 后完成】\n\n" + specification_seed,
        encoding="utf-8",
    )
    (application / "abstract.md").write_text(
        "# 说明书摘要\n\n【待根据最终权利要求和最终说明书撰写】\n",
        encoding="utf-8",
    )
    (application / "drawings-description.md").write_text(
        "# 附图说明\n\n【待根据最终说明书确认附图及标记】\n",
        encoding="utf-8",
    )
    _write_json(
        application / "application-metadata.json",
        {
            "source_claims_v2_sha256": _sha256_text(claims_text),
            "claims_final_sha256": _sha256_text(claims_final),
            "specification_final_sha256": "",
            "abstract_sha256": "",
            "drawings_description_sha256": "",
            "limitation_sync": [],
        },
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
    errors, numbered_records = _read_search_records(path)
    records = [record for _, record in numbered_records]
    if required_candidate_ids:
        searched = {str(record.get("candidate_id", "")) for record in records}
        missing_candidates = sorted(required_candidate_ids - searched)
        if missing_candidates:
            errors.append(
                "First search does not cover candidates: " + ", ".join(missing_candidates)
            )
    return errors


def _read_search_records(
    path: Path, additional_fields: set[str] | None = None
) -> tuple[list[str], list[tuple[int, dict[str, Any]]]]:
    records_path = path / "search-records.jsonl"
    if not records_path.exists():
        return [f"Missing structured search log: {records_path.relative_to(path.parent)}"], []
    errors: list[str] = []
    records: list[tuple[int, dict[str, Any]]] = []
    required_fields = SEARCH_FIELDS | (additional_fields or set())
    for line_number, line in enumerate(records_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            errors.append(f"Invalid search JSON at line {line_number}")
            continue
        if not isinstance(record, dict):
            errors.append(f"Search line {line_number} must be a JSON object")
            continue
        missing = sorted(required_fields - record.keys())
        if missing:
            errors.append(f"Search line {line_number} missing fields: {', '.join(missing)}")
        if not isinstance(record.get("reviewed_reference_ids"), list):
            errors.append(f"Search line {line_number} reviewed_reference_ids must be a list")
        if not isinstance(record.get("verified_urls"), list):
            errors.append(f"Search line {line_number} verified_urls must be a list")
        if not isinstance(record.get("query"), str) or not record["query"].strip():
            errors.append(f"Search line {line_number} query must be non-empty")
        records.append((line_number, record))
    if not records:
        errors.append("Structured search log must contain at least one record")
    return errors, records


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


def _validate_claims_stage(path: Path, structure_path: Path | None = None) -> list[str]:
    errors = _validate_draft(path)
    if errors:
        return errors
    text = path.read_text(encoding="utf-8")
    errors.extend(validate_claims_cn(text))
    if structure_path is not None:
        errors.extend(_validate_claim_structure(text, structure_path))
    return errors


def _validate_claim_structure(text: str, structure_path: Path) -> list[str]:
    try:
        structure = _load_json(structure_path, "Claims V2 structure")
    except ValueError as exc:
        return [str(exc)]
    entries = structure.get("independent_claims")
    if not isinstance(entries, list) or not entries:
        return ["Claims V2 structure must contain independent_claims"]

    blocks = parse_claim_blocks(text)
    independent_numbers = independent_claim_numbers(text)
    parsed: dict[str, list[str]] = {}
    errors: list[str] = []
    for number in sorted(independent_numbers):
        claim_id = f"I{number}"
        labels, label_errors = _parse_independent_limitation_lines(number, blocks[number])
        parsed[claim_id] = labels
        errors.extend(label_errors)

    structured: dict[str, list[str]] = {}
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            errors.append(f"Claims V2 structure entry {index} must be an object")
            continue
        claim_id = entry.get("claim_id")
        claim_number = entry.get("claim_number")
        limitation_ids = entry.get("limitation_ids")
        distinguishing_ids = entry.get("distinguishing_limitation_ids")
        if claim_id != f"I{claim_number}":
            errors.append(f"Claims V2 structure entry {index} has inconsistent claim ID")
        if not isinstance(limitation_ids, list) or not limitation_ids:
            errors.append(f"Claims V2 structure entry {index} requires limitation_ids")
            continue
        if len(limitation_ids) != len(set(limitation_ids)):
            errors.append(f"Claims V2 structure entry {index} contains duplicate limitation IDs")
        if not isinstance(distinguishing_ids, list) or not distinguishing_ids:
            errors.append(
                f"Claims V2 structure entry {index} requires distinguishing_limitation_ids"
            )
            distinguishing_ids = []
        if not set(distinguishing_ids) <= set(limitation_ids):
            errors.append(
                f"Claims V2 structure entry {index} has distinguishing IDs outside the claim"
            )
        if isinstance(claim_id, str):
            if claim_id in structured:
                errors.append(f"Claims V2 structure contains duplicate claim ID {claim_id}")
            structured[claim_id] = limitation_ids

    if set(parsed) != set(structured):
        errors.append("Claims V2 structure must cover exactly all independent claims")
    for claim_id in sorted(set(parsed) & set(structured)):
        if parsed[claim_id] != structured[claim_id]:
            errors.append(
                f"{claim_id} parser limitation IDs must exactly match the structured limitation IDs"
            )
    return errors


def _parse_independent_limitation_lines(
    claim_number: int, lines: list[str]
) -> tuple[list[str], list[str]]:
    claim_id = f"I{claim_number}"
    labels: list[str] = []
    errors: list[str] = []
    for line_index, line in enumerate(lines):
        line_labels = TRACE_LABEL_RE.findall(line)
        if line_index == 0:
            if line_labels:
                errors.append(
                    f"Independent claim {claim_number} must place its preamble on a separate "
                    "line before trace-labelled limitations"
                )
            if len(lines) == 1 or not line.rstrip().endswith(("：", ":")):
                errors.append(
                    f"Independent claim {claim_number} preamble must end with a colon "
                    "before separately labelled limitations"
                )
            continue
        if not line_labels:
            errors.append(
                f"Independent claim {claim_number} has an unlabelled substantive limitation line"
            )
            continue
        if len(line_labels) > 1:
            errors.append(
                f"Independent claim {claim_number} must place exactly one trace label "
                "on each substantive limitation line"
            )
            continue
        if line_index > 0 and not TRACE_LINE_RE.match(line):
            errors.append(
                f"Independent claim {claim_number} has an unlabelled substantive limitation line"
            )
            continue
        label = line_labels[0]
        if not label.startswith(f"{claim_id}-L"):
            errors.append(
                f"Trace label {label} does not belong to independent claim {claim_number}"
            )
        labels.append(label)
    expected = [f"{claim_id}-L{index}" for index in range(1, len(labels) + 1)]
    if labels != expected:
        errors.append(
            f"Independent claim {claim_number} trace labels must be unique and consecutive"
        )
    if not labels:
        errors.append(f"Independent claim {claim_number} has no trace-labelled limitations")
    return labels, errors


def _validate_support_map(case_dir: Path, _: dict[str, Any]) -> list[str]:
    path = case_dir / "09-claim-support-map.md"
    table_errors = _validate_table(path, 1)
    if table_errors:
        return table_errors
    structure_path = case_dir / "08-claims-v2-structure.json"
    try:
        structure = _load_json(structure_path, "Claims V2 structure")
    except ValueError as exc:
        return [str(exc)]
    labels = {
        limitation_id
        for entry in structure.get("independent_claims", [])
        if isinstance(entry, dict)
        for limitation_id in entry.get("limitation_ids", [])
    }
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
        row_labels = re.findall(r"I\d+-L\d+", cells[0])
        if len(row_labels) != 1:
            errors.append(f"Claim support row {row_number} must map exactly one limitation ID")
            continue
        label = row_labels[0]
        if label in mapped_labels:
            errors.append(f"Claim support limitation {label} is mapped more than once")
        if label not in labels:
            errors.append(f"Claim support row {row_number} maps unknown limitation {label}")
        mapped_labels.add(label)
    missing_labels = sorted(labels - mapped_labels)
    if missing_labels:
        errors.append(
            "Claim support map is missing independent-claim limitations: "
            + ", ".join(missing_labels)
        )
    if len(_markdown_data_rows(path)) != len(labels):
        errors.append("Claim support row count must equal the structured limitation count")
    return errors


def _validate_final_search(case_dir: Path, _: dict[str, Any]) -> list[str]:
    path = case_dir / "10-final-search"
    errors, records = _read_search_records(path, FINAL_SEARCH_FIELDS)
    try:
        structure = _load_json(case_dir / "08-claims-v2-structure.json", "Claims V2 structure")
    except ValueError as exc:
        return errors + [str(exc)]

    claims: dict[str, set[str]] = {}
    distinguishing: set[str] = set()
    for entry in structure.get("independent_claims", []):
        if not isinstance(entry, dict):
            continue
        claim_id = entry.get("claim_id")
        if not isinstance(claim_id, str):
            continue
        claims[claim_id] = set(entry.get("limitation_ids", []))
        distinguishing.update(entry.get("distinguishing_limitation_ids", []))
    if not claims:
        errors.append("Final search requires at least one structured independent claim")

    combination_coverage: set[str] = set()
    limitation_coverage: set[str] = set()
    for line_number, record in records:
        scope = record.get("search_scope")
        if scope not in FINAL_SEARCH_SCOPES:
            errors.append(f"Final search line {line_number} has invalid search_scope")
        limitation_ids = record.get("limitation_ids")
        if not isinstance(limitation_ids, list) or not limitation_ids:
            errors.append(
                f"Final search line {line_number} limitation_ids must be a non-empty list"
            )
            continue
        claim_id = record.get("claim_id")
        if claim_id not in claims:
            errors.append(f"Final search line {line_number} references unknown independent claim")
            continue
        unknown = set(limitation_ids) - claims[claim_id]
        if unknown:
            errors.append(
                f"Final search line {line_number} references unknown limitations: "
                + ", ".join(sorted(unknown))
            )
        limitation_coverage.update(limitation_ids)
        if scope == "claim_combination" and claims[claim_id] <= set(limitation_ids):
            combination_coverage.add(claim_id)

    missing_claims = sorted(set(claims) - combination_coverage)
    if missing_claims:
        errors.append(
            "Final search lacks a full combination query for independent claims: "
            + ", ".join(missing_claims)
        )
    missing_distinctions = sorted(distinguishing - limitation_coverage)
    if missing_distinctions:
        errors.append(
            "Final search does not cover distinguishing limitations: "
            + ", ".join(missing_distinctions)
        )
    return errors


def _validate_application_draft(case_dir: Path, _: dict[str, Any]) -> list[str]:
    application = case_dir / "12-application"
    claims_path = application / "claims-final.md"
    specification_path = application / "specification-final.md"
    abstract_path = application / "abstract.md"
    drawings_path = application / "drawings-description.md"
    metadata_path = application / "application-metadata.json"
    errors: list[str] = []
    for path in (
        claims_path,
        specification_path,
        abstract_path,
        drawings_path,
        metadata_path,
    ):
        if not path.exists():
            errors.append(f"Missing application draft artifact: {path.name}")
    if errors:
        return errors

    claims_v2 = (case_dir / "08-claims-v2.md").read_text(encoding="utf-8")
    claims_final = claims_path.read_text(encoding="utf-8")
    expected_claims = TRACE_LABEL_RE.sub("", claims_v2)
    if claims_final != expected_claims:
        errors.append(
            "claims-final.md must be generated exactly from Claims V2 without trace labels"
        )
    if TRACE_LABEL_RE.search(claims_final):
        errors.append("claims-final.md still contains internal trace labels")
    errors.extend(validate_claims_cn(claims_final))

    specification = specification_path.read_text(encoding="utf-8")
    abstract = abstract_path.read_text(encoding="utf-8")
    drawings = drawings_path.read_text(encoding="utf-8")
    for name, content in (
        ("specification-final.md", specification),
        ("abstract.md", abstract),
        ("drawings-description.md", drawings),
    ):
        if "【待" in content or "待同步" in content:
            errors.append(f"{name} still contains pending application-draft content")
    errors.extend(validate_abstract_cn(abstract))
    if not _meaningful_markdown(drawings):
        errors.append("drawings-description.md has no substantive content")
    if not _meaningful_markdown(specification):
        errors.append("specification-final.md has no substantive content")

    try:
        metadata = _load_json(metadata_path, "application metadata")
        structure = _load_json(case_dir / "08-claims-v2-structure.json", "Claims V2 structure")
    except ValueError as exc:
        return errors + [str(exc)]
    expected_hashes = {
        "source_claims_v2_sha256": _sha256_text(claims_v2),
        "claims_final_sha256": _sha256_text(claims_final),
        "specification_final_sha256": _sha256_text(specification),
        "abstract_sha256": _sha256_text(abstract),
        "drawings_description_sha256": _sha256_text(drawings),
    }
    for field, expected in expected_hashes.items():
        if metadata.get(field) != expected:
            errors.append(f"Application metadata hash is stale or missing: {field}")

    expected_ids = {
        limitation_id
        for entry in structure.get("independent_claims", [])
        if isinstance(entry, dict)
        for limitation_id in entry.get("limitation_ids", [])
    }
    sync_entries = metadata.get("limitation_sync")
    if not isinstance(sync_entries, list):
        errors.append("Application metadata limitation_sync must be a list")
        return errors
    seen: set[str] = set()
    required_truths = (
        "terminology_synced",
        "protected_subject_synced",
        "embodiment_supported",
        "technical_effect_supported",
    )
    for index, entry in enumerate(sync_entries, 1):
        if not isinstance(entry, dict):
            errors.append(f"Application limitation sync entry {index} must be an object")
            continue
        limitation_id = entry.get("limitation_id")
        if limitation_id in seen:
            errors.append(f"Application limitation sync duplicates {limitation_id}")
        seen.add(limitation_id)
        if not entry.get("specification_sections"):
            errors.append(f"Application limitation {limitation_id} lacks specification sections")
        if any(entry.get(field) is not True for field in required_truths):
            errors.append(f"Application limitation {limitation_id} is not fully synchronized")
        if entry.get("drawing_reference_status") not in {"checked", "not_applicable"}:
            errors.append(f"Application limitation {limitation_id} lacks drawing review")
        if entry.get("status") != "synced":
            errors.append(f"Application limitation {limitation_id} status must be synced")
    if seen != expected_ids:
        errors.append("Application limitation_sync must cover exactly all Claims V2 limitations")
    return errors


def _validate_final_audit(case_dir: Path, _: dict[str, Any]) -> list[str]:
    path = case_dir / "13-final-audit.md"
    if not path.exists():
        return ["Missing case artifact: 13-final-audit.md"]
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
    documents = list(path.glob("*.docx")) if path.exists() else []
    errors: list[str] = []
    used_documents: set[Path] = set()
    for subject in sorted(REQUIRED_DOCX_SUBJECTS, key=len, reverse=True):
        matches = sorted(
            (
                document
                for document in documents
                if subject in document.stem and document not in used_documents
            ),
            key=lambda document: len(document.stem),
        )
        if not matches:
            errors.append(f"Missing rendered DOCX subject: {subject}")
            continue
        selected = matches[0]
        used_documents.add(selected)
        errors.extend(_validate_docx_file(selected))
    return errors


def _validate_docx_file(path: Path) -> list[str]:
    errors: list[str] = []
    if path.stat().st_size < MIN_DOCX_SIZE:
        errors.append(f"DOCX is implausibly small: {path.name}")
    if not zipfile.is_zipfile(path):
        return errors + [f"DOCX is not a valid OOXML ZIP: {path.name}"]
    try:
        with zipfile.ZipFile(path) as archive:
            corrupt = archive.testzip()
            if corrupt:
                errors.append(f"DOCX contains a corrupt ZIP member: {path.name}:{corrupt}")
            names = set(archive.namelist())
            for required in ("[Content_Types].xml", "word/document.xml"):
                if required not in names:
                    errors.append(f"DOCX missing {required}: {path.name}")
            if "word/document.xml" in names:
                try:
                    root = ElementTree.fromstring(archive.read("word/document.xml"))
                except ElementTree.ParseError:
                    errors.append(f"DOCX has invalid word/document.xml: {path.name}")
                else:
                    body = "".join(
                        node.text or "" for node in root.iter() if node.tag.endswith("}t")
                    ).strip()
                    if not body:
                        errors.append(f"DOCX document body is empty: {path.name}")
    except (OSError, zipfile.BadZipFile):
        errors.append(f"DOCX cannot be opened as OOXML: {path.name}")
    return errors


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


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _meaningful_markdown(text: str) -> list[str]:
    return [
        line
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith(("#", ">"))
    ]


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
    history = status.get("stage_history", [])
    if not isinstance(history, list) or not history:
        return ["stage_history must contain an initialization event"]
    errors: list[str] = []
    previous: CaseStage | None = None
    revision = 0
    for index, entry in enumerate(history):
        if not isinstance(entry, dict):
            errors.append(f"stage_history event {index + 1} must be an object")
            continue
        try:
            stage = CaseStage(entry.get("stage", ""))
        except ValueError:
            errors.append(f"stage_history event {index + 1} has an unknown stage")
            continue
        event = entry.get("event") or ("initialize" if index == 0 else "advance")
        if index == 0:
            if event != "initialize" or stage != CaseStage.PROJECT_SNAPSHOT:
                errors.append("stage_history must begin with PROJECT_SNAPSHOT initialization")
        elif previous is not None and event == "advance":
            expected_index = CASE_STAGE_ORDER.index(previous) + 1
            if expected_index >= len(CASE_STAGE_ORDER) or CASE_STAGE_ORDER[expected_index] != stage:
                errors.append(f"stage_history event {index + 1} is not a sequential advance")
        elif previous is not None and event == "revise":
            if CASE_STAGE_ORDER.index(stage) >= CASE_STAGE_ORDER.index(previous):
                errors.append(f"stage_history event {index + 1} is not a backward revision")
            revision += 1
            if entry.get("revision") != revision or not str(entry.get("reason", "")).strip():
                errors.append(f"stage_history revision event {index + 1} is incomplete")
        elif index > 0:
            errors.append(f"stage_history event {index + 1} has an invalid event type")
        previous = stage
    if previous != current:
        errors.append("stage_history must end at current_stage")
    if status.get("revision", 0) != revision:
        errors.append("case revision counter does not match stage_history")
    if len(status.get("revision_history", [])) != revision:
        errors.append("revision_history count does not match revision counter")
    return errors


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
