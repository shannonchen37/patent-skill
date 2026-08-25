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
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from .claims import (
    TRACE_LABEL_RE,
    claim_dependencies,
    independent_claim_numbers,
    parse_claim_blocks,
    render_filing_claims,
    validate_abstract_cn,
    validate_claims_cn,
    validate_no_internal_prose_inside_claim_body,
)
from .scanner import scan_archive, scan_repository
from .schema_validation import validate_schema


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
    "record_id",
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
TRACE_LINE_RE = re.compile(r"^[；;、]?\s*\[((?:I|D)\d+-L\d+)\]\s*(.+)$")
MIN_DOCX_SIZE = 1024
BASE_REQUIRED_DOCX_SUBJECTS = (
    "技术交底书",
    "权利要求书",
    "说明书",
    "说明书摘要",
    "初步查新",
    "请求书信息确认",
    "提交文件清单",
)

STAGE_ARTIFACTS: dict[CaseStage, tuple[str, ...]] = {
    CaseStage.EVIDENCE_MAP: (
        "01-code-evidence-map.json",
        "01-code-evidence-map.md",
        "01-technical-disclosures.json",
        "01-technical-disclosures.md",
    ),
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
    CaseStage.CLAIM_SUPPORT_MAP: ("09-claim-support-map.json", "09-claim-support-map.md"),
    CaseStage.FINAL_SEARCH: ("10-final-search",),
    CaseStage.APPLICATION_DRAFT: ("12-application",),
    CaseStage.FINAL_AUDIT: ("13-final-audit.json", "13-final-audit.md"),
    CaseStage.INDEPENDENT_AUDIT: ("filing-package",),
}

ARTIFACT_TEMPLATES = {
    CaseStage.EVIDENCE_MAP: (
        "01-code-evidence-map.md",
        """# 技术证据地图

> 当前阶段记录可哈希的工程证据；发明人确认但未编码的设计另存为 TD，不写权利要求。

| 证据编号 | 代码/文档证据 | 处理步骤 | 数据或状态变化 | 技术效果 | 证据状态 |
|---|---|---|---|---|---|
""",
    ),
    CaseStage.INVENTION_CANDIDATES: (
        "02-invention-candidates.md",
        """# 候选发明

> 从可追溯工程证据与充分公开的技术披露中提取 3–5 个完整候选。先检索全部候选，再决定主发明。

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
        "# Claims V1\n\n> 每项实质限定必须回溯到 E### 或已通过充分公开校验的 TD###。\n",
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
    questions = {
        "questions": [
            {
                "id": "Q001",
                "category": "filing_context",
                "question": "项目的首次公开日期和公开范围是什么？",
                "blocking": False,
                "impact": "用于提交前的新颖性法律背景复核",
                "status": "open",
                "resolution": None,
                "evidence_refs": [],
                "source": None,
            },
            {
                "id": "Q002",
                "category": "filing_context",
                "question": "哪些人员对核心技术方案作出实质性贡献？",
                "blocking": False,
                "impact": "用于提交前确认发明人",
                "status": "open",
                "resolution": None,
                "evidence_refs": [],
                "source": None,
            },
        ]
    }
    _write_json(case_dir / "context-questions.json", questions)
    _render_context_questions(case_dir, questions)

    now = datetime.now(UTC).isoformat()
    status = {
        "canonical_source": "patent-skill",
        "case_dir": str(case_dir),
        "project_source": str(project),
        "proposed_title": title,
        "current_stage": CaseStage.PROJECT_SNAPSHOT.value,
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
    if target == CaseStage.CONTENT_READY_FOR_ATTORNEY_REVIEW:
        question_errors = _validate_content_ready(case_dir, status)
        if question_errors:
            raise ValueError("; ".join(question_errors))
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
    _prepare_stage_artifact(case_dir, target, revision=status.get("revision", 0))
    _write_json(case_dir / "case-status.json", status)
    return status


def resolve_case_question(
    case_dir: Path,
    question_id: str,
    answer: str,
    source: str,
    *,
    resolution_type: str | None = None,
    resulting_disclosure_ids: list[str] | None = None,
) -> dict[str, Any]:
    case_dir = case_dir.resolve()
    if not answer.strip() or not source.strip():
        raise ValueError("Question resolution requires a non-empty answer and source")
    path = case_dir / "context-questions.json"
    questions = _load_json(path, "context questions")
    matches = [item for item in questions.get("questions", []) if item.get("id") == question_id]
    if len(matches) != 1:
        raise ValueError(f"Unknown or duplicate context question: {question_id}")
    question = matches[0]
    question.update(
        {
            "status": "resolved",
            "resolution": answer.strip(),
            "source": source.strip(),
            "resolved_at": datetime.now(UTC).isoformat(),
        }
    )
    completion = question.get("candidate_completion")
    if resolution_type is not None:
        allowed = {
            "candidate_confirmed",
            "candidate_modified",
            "candidate_rejected",
            "unknown",
        }
        if question.get("category") != "technical" or resolution_type not in allowed:
            raise ValueError("resolution_type is only valid for technical questions")
        question["resolution_type"] = resolution_type
        if completion:
            if resolution_type in {"candidate_confirmed", "candidate_modified"}:
                if not resulting_disclosure_ids:
                    raise ValueError("Confirmed candidate completion requires resulting TD IDs")
                completion["status"] = "confirmed_and_promoted"
                if resolution_type == "candidate_modified":
                    completion["user_modified_statement"] = answer.strip()
                question["resulting_disclosure_ids"] = resulting_disclosure_ids
            elif resolution_type == "candidate_rejected":
                completion["status"] = "rejected"
                question["resulting_disclosure_ids"] = []
            else:
                completion["status"] = "unknown"
                question["resulting_disclosure_ids"] = []
        elif resulting_disclosure_ids:
            raise ValueError("TD promotion requires a candidate completion")
    errors = validate_schema(questions, "context-questions.schema.json")
    if errors:
        raise ValueError("Invalid context questions: " + "; ".join(errors))
    _write_json(path, questions)
    _render_context_questions(case_dir, questions)
    return question


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
    if target == CaseStage.EVIDENCE_MAP:
        for relative in ("context-questions.json", "context-ledger.md"):
            source = case_dir / relative
            if source.exists():
                destination = artifact_archive / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
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
    if target == CaseStage.EVIDENCE_MAP:
        _invalidate_promoted_disclosure_questions(case_dir)
    _prepare_stage_artifact(case_dir, target, revision=revision)
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
        "12-application/application-metadata.json",
        "12-application/figures.json",
        "01-technical-disclosures.json",
        "01-technical-disclosures.md",
        "09-claim-support-map.json",
        "09-claim-support-map.md",
        "13-final-audit.json",
        "13-final-audit.md",
    ):
        source = case_dir / relative
        if not source.exists():
            continue
        destination = output_dir / Path(relative).name
        shutil.copy2(source, destination)
    drawings_description = case_dir / "12-application" / "drawings-description.md"
    if drawings_description.exists():
        shutil.copy2(drawings_description, output_dir / drawings_description.name)
    figures = case_dir / "12-application" / "figures"
    if figures.exists():
        shutil.copytree(figures, output_dir / "figures")
    _write_json(
        output_dir / "export-manifest.json",
        {
            "canonical_source": "patent-skill",
            "source_case": str(case_dir),
            "source_revision": status.get("revision", 0),
            "exported_at": datetime.now(UTC).isoformat(),
            "files": [
                {
                    "path": path.relative_to(output_dir).as_posix(),
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                }
                for path in sorted(output_dir.rglob("*"))
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
    errors.extend(validate_schema(status, "case-status.schema.json"))
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
        CaseStage.EVIDENCE_MAP: _validate_evidence_map,
        CaseStage.INVENTION_CANDIDATES: _validate_invention_candidates,
        CaseStage.FIRST_SEARCH: _validate_first_search,
        CaseStage.CANDIDATE_RANKING: _validate_ranking,
        CaseStage.FEATURE_MATRIX: _validate_feature_matrix,
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


def _prepare_stage_artifact(
    case_dir: Path, stage: CaseStage, *, revision: int | None = None
) -> None:
    if stage == CaseStage.EVIDENCE_MAP:
        _write_json(case_dir / "01-code-evidence-map.json", {"evidence": []})
        _render_evidence_map(case_dir, {"evidence": []})
        disclosures = {
            "case_revision": (
                _load_status(case_dir).get("revision", 0) if revision is None else revision
            ),
            "disclosures": [],
        }
        _write_json(case_dir / "01-technical-disclosures.json", disclosures)
        _render_technical_disclosures(case_dir, disclosures)
    elif stage == CaseStage.INVENTION_CANDIDATES:
        _write_json(case_dir / "02-invention-candidates.json", {"candidates": []})
        _render_invention_candidates(case_dir, {"candidates": []})
    elif stage == CaseStage.FEATURE_MATRIX:
        _write_json(case_dir / "04-feature-matrix.json", {"features": []})
        _render_feature_matrix(case_dir, {"features": []})
    elif stage == CaseStage.FIRST_SEARCH:
        _prepare_search_dir(case_dir / "03-prior-art-search")
    elif stage == CaseStage.FINAL_SEARCH:
        _prepare_final_search(case_dir)
    elif stage == CaseStage.APPLICATION_DRAFT:
        _prepare_application_draft(case_dir)
    elif stage == CaseStage.FINAL_AUDIT:
        _write_json(
            case_dir / "13-final-audit.json",
            {
                "audited_application": _application_hash_snapshot(case_dir),
                "novelty": {},
                "inventive_step": {},
                "eligibility": {},
                "clarity_and_support": {},
                "enablement": {},
                "unity": {},
                "amendment_basis": {},
                "sensitive_information": {},
                "unimplemented_disclosures": [],
            },
        )
        _render_final_audit(case_dir, {})
    elif stage == CaseStage.INDEPENDENT_AUDIT:
        directory = case_dir / "filing-package" / "huang-audit"
        directory.mkdir(parents=True, exist_ok=True)
        (case_dir / "filing-package" / "docx").mkdir(parents=True, exist_ok=True)
        audit = {
            "audit_id": "",
            "auditor": {"tool": "HuangXinzhe/cn-patent-drafting", "version": "unknown"},
            "source_application": _application_hash_snapshot(case_dir),
            "source_final_audit_sha256": _sha256_file(case_dir / "13-final-audit.json"),
            "findings": [],
            "overall_status": "PENDING",
        }
        _write_json(directory / "independent-audit.json", audit)
        _render_independent_audit(directory, audit)
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
                {"independent_claims": [], "dependent_claims": []},
            )
        elif stage == CaseStage.CLAIM_SUPPORT_MAP:
            _write_json(case_dir / "09-claim-support-map.json", {"limitations": []})
            _render_claim_support_map(case_dir, {"limitations": []})


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


def _prepare_final_search(case_dir: Path) -> None:
    directory = case_dir / "10-final-search"
    _prepare_search_dir(directory)
    status = _load_status(case_dir)
    _write_json(
        directory / "search-session.json",
        {
            "revision": status.get("revision", 0),
            "source": {
                "claims_v2_sha256": _sha256_file(case_dir / "08-claims-v2.md"),
                "claims_v2_structure_sha256": _sha256_file(
                    case_dir / "08-claims-v2-structure.json"
                ),
            },
            "started_at": datetime.now(UTC).isoformat(),
            "completed_at": None,
        },
    )


def _prepare_application_draft(case_dir: Path) -> None:
    application = case_dir / "12-application"
    application.mkdir(parents=True, exist_ok=True)
    claims_v2 = case_dir / "08-claims-v2.md"
    claims_text = claims_v2.read_text(encoding="utf-8") if claims_v2.exists() else ""
    claims_final = render_filing_claims(claims_text)
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
        "# 附图说明\n\n【待明确本案是否需要附图】\n",
        encoding="utf-8",
    )
    _write_json(
        application / "figures.json",
        {"figures_required": False, "figures": [], "abstract_figure_id": None},
    )
    _write_json(
        application / "application-metadata.json",
        {
            "source_claims_v2_sha256": _sha256_text(claims_text),
            "claims_final_sha256": _sha256_text(claims_final),
            "specification_final_sha256": "",
            "abstract_sha256": "",
            "drawings_description_sha256": "",
            "drawings": {
                "required": False,
                "reason": "【待明确文字是否足以清楚完整说明技术方案】",
                "abstract_figure_required": False,
                "abstract_figure_id": None,
            },
            "limitation_sync": [],
        },
    )


def _application_hash_snapshot(case_dir: Path) -> dict[str, Any]:
    application = case_dir / "12-application"
    status = _load_status(case_dir)
    return {
        "revision": status.get("revision", 0),
        "claims_final_sha256": _sha256_file(application / "claims-final.md"),
        "specification_final_sha256": _sha256_file(application / "specification-final.md"),
        "abstract_sha256": _sha256_file(application / "abstract.md"),
        "drawings_manifest_sha256": _sha256_file(application / "figures.json"),
    }


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


def _validate_effect_basis(
    statement: str, effect_basis: Any, label: str
) -> list[str]:
    errors: list[str] = []
    quantified = re.search(
        r"\d+(?:\.\d+)?\s*(?:%|％|倍|ms|毫秒|秒|分钟|MB|GB|GiB|MiB)",
        statement,
        flags=re.IGNORECASE,
    )
    if quantified and effect_basis != "measured":
        errors.append(f"{label} quantifies an effect without measured basis")
    return errors


def _technical_disclosure_state(
    case_dir: Path, evidence_map: dict[str, Any]
) -> tuple[list[str], dict[str, Any], set[str]]:
    try:
        disclosures = _load_json(
            case_dir / "01-technical-disclosures.json", "technical disclosures"
        )
        questions = _load_json(case_dir / "context-questions.json", "context questions")
        status = _load_status(case_dir)
    except ValueError as exc:
        return [str(exc)], {"case_revision": 0, "disclosures": []}, set()

    errors = validate_schema(disclosures, "technical-disclosures.schema.json")
    errors.extend(validate_schema(questions, "context-questions.schema.json"))
    if disclosures.get("case_revision", 0) > status.get("revision", 0):
        errors.append("Technical disclosures reference a future case revision")

    evidence_ids = {item.get("evidence_id") for item in evidence_map.get("evidence", [])}
    question_map = {item.get("id"): item for item in questions.get("questions", [])}
    disclosure_items = disclosures.get("disclosures", [])
    disclosure_ids = [item.get("disclosure_id", "") for item in disclosure_items]
    if len(disclosure_ids) != len(set(disclosure_ids)):
        errors.append("Technical disclosure IDs must be unique")
    known_td_ids = set(disclosure_ids)
    approved: set[str] = set()

    for question in questions.get("questions", []):
        completion = question.get("candidate_completion")
        if not completion:
            continue
        unknown_basis = set(completion.get("basis_refs", [])) - evidence_ids
        if unknown_basis:
            errors.append(
                f"Candidate completion {question.get('id')} references unknown engineering evidence"
            )
        resulting = set(question.get("resulting_disclosure_ids", []))
        completion_status = completion.get("status")
        if completion_status == "confirmed_and_promoted":
            if question.get("resolution_type") not in {
                "candidate_confirmed",
                "candidate_modified",
            }:
                errors.append(
                    f"Promoted candidate completion {question.get('id')} "
                    "lacks a confirming resolution"
                )
            if not resulting or resulting - known_td_ids:
                errors.append(
                    f"Promoted candidate completion {question.get('id')} lacks valid TD provenance"
                )
        elif resulting:
            errors.append(
                f"Unpromoted candidate completion {question.get('id')} cannot produce TD provenance"
            )

    for item in disclosure_items:
        disclosure_id = item.get("disclosure_id", "")
        question = question_map.get(item.get("question_id"))
        if not question or question.get("category") != "technical":
            errors.append(f"Technical disclosure {disclosure_id} lacks a technical source question")
        elif disclosure_id not in question.get("resulting_disclosure_ids", []):
            errors.append(
                f"Technical disclosure {disclosure_id} is not linked from its source question"
            )

        lifecycle = item.get("lifecycle_status")
        if lifecycle == "superseded":
            successor = item.get("superseded_by")
            if not successor or successor not in known_td_ids or successor == disclosure_id:
                errors.append(
                    f"Superseded technical disclosure {disclosure_id} lacks a valid successor"
                )
            continue
        if item.get("superseded_by") is not None:
            errors.append(f"Active technical disclosure {disclosure_id} cannot name a successor")

        enablement = item.get("enablement", {})
        if enablement.get("status") != "sufficient":
            errors.append(f"Technical disclosure {disclosure_id} has incomplete enablement")
        else:
            approved.add(disclosure_id)

        effect = item.get("technical_effect", {})
        errors.extend(
            _validate_effect_basis(
                str(effect.get("statement", "")),
                effect.get("effect_basis"),
                f"Technical disclosure {disclosure_id}",
            )
        )
        unknown_effect_refs = set(effect.get("evidence_refs", [])) - evidence_ids
        if unknown_effect_refs:
            errors.append(f"Technical disclosure {disclosure_id} has unknown effect evidence")

    return errors, disclosures, approved


def _invalidate_promoted_disclosure_questions(case_dir: Path) -> None:
    path = case_dir / "context-questions.json"
    questions = _load_json(path, "context questions")
    changed = False
    for item in questions.get("questions", []):
        completion = item.get("candidate_completion")
        if not completion or completion.get("status") != "confirmed_and_promoted":
            continue
        completion["status"] = "proposed"
        completion.pop("user_modified_statement", None)
        item.update(
            {
                "status": "open",
                "resolution": None,
                "source": None,
                "resulting_disclosure_ids": [],
            }
        )
        item.pop("resolution_type", None)
        item.pop("resolved_at", None)
        changed = True
    if changed:
        _write_json(path, questions)
        _render_context_questions(case_dir, questions)


def _validate_evidence_map(case_dir: Path, _: dict[str, Any]) -> list[str]:
    try:
        evidence_map = _load_json(case_dir / "01-code-evidence-map.json", "evidence map")
        snapshot = _load_json(
            case_dir / "00-project-snapshot" / "snapshot-manifest.json", "snapshot manifest"
        )
    except ValueError as exc:
        return [str(exc)]
    errors = validate_schema(evidence_map, "engineering-provenance.schema.json")
    manifest = {item["path"]: item["sha256"] for item in snapshot.get("files", [])}
    identifiers: list[str] = []
    for item in evidence_map.get("evidence", []):
        identifiers.append(item.get("evidence_id", ""))
        source = item.get("source", {})
        path = source.get("path")
        if path not in manifest:
            errors.append(f"Evidence {item.get('evidence_id')} references a file outside snapshot")
        elif source.get("sha256") != manifest[path]:
            errors.append(f"Evidence {item.get('evidence_id')} has a stale source hash")
        if (
            source.get("start_line")
            and source.get("end_line")
            and source["start_line"] > source["end_line"]
        ):
            errors.append(f"Evidence {item.get('evidence_id')} has an invalid line range")
        errors.extend(
            _validate_effect_basis(
                str(item.get("technical_effect", "")),
                item.get("effect_basis"),
                f"Evidence {item.get('evidence_id')}",
            )
        )
        if item.get("effect_basis") == "measured" and item.get("status") != "experiment-supported":
            errors.append(
                f"Evidence {item.get('evidence_id')} measured effect requires "
                "experiment-supported status"
            )
    if len(identifiers) != len(set(identifiers)):
        errors.append("Evidence IDs must be unique")
    disclosure_errors, disclosures, _ = _technical_disclosure_state(case_dir, evidence_map)
    errors.extend(disclosure_errors)
    if not errors:
        _render_evidence_map(case_dir, evidence_map)
        _render_technical_disclosures(case_dir, disclosures)
    return errors


def _validate_invention_candidates(case_dir: Path, _: dict[str, Any]) -> list[str]:
    try:
        candidates = _load_json(case_dir / "02-invention-candidates.json", "invention candidates")
        evidence = _load_json(case_dir / "01-code-evidence-map.json", "evidence map")
    except ValueError as exc:
        return [str(exc)]
    errors = validate_schema(candidates, "invention.schema.json")
    evidence_ids = {item.get("evidence_id") for item in evidence.get("evidence", [])}
    disclosure_errors, _, approved_td_ids = _technical_disclosure_state(case_dir, evidence)
    errors.extend(disclosure_errors)
    candidate_ids: list[str] = []
    for item in candidates.get("candidates", []):
        candidate_ids.append(item.get("candidate_id", ""))
        unknown = set(item.get("engineering_evidence_ids", [])) - evidence_ids
        if unknown:
            errors.append(
                f"Candidate {item.get('candidate_id')} references unknown evidence: "
                + ", ".join(sorted(unknown))
            )
        unknown_td = set(item.get("technical_disclosure_ids", [])) - approved_td_ids
        if unknown_td:
            errors.append(
                f"Candidate {item.get('candidate_id')} references unavailable "
                "technical disclosure: "
                + ", ".join(sorted(unknown_td))
            )
        errors.extend(
            _validate_effect_basis(
                "；".join(item.get("technical_effects", [])),
                item.get("effect_basis"),
                f"Candidate {item.get('candidate_id')}",
            )
        )
    if len(candidate_ids) != len(set(candidate_ids)):
        errors.append("Candidate IDs must be unique")
    if not errors:
        _render_invention_candidates(case_dir, candidates)
    return errors


def _validate_feature_matrix(case_dir: Path, _: dict[str, Any]) -> list[str]:
    try:
        matrix = _load_json(case_dir / "04-feature-matrix.json", "feature matrix")
        evidence = _load_json(case_dir / "01-code-evidence-map.json", "evidence map")
    except ValueError as exc:
        return [str(exc)]
    errors = validate_schema(matrix, "case-feature-matrix.schema.json")
    evidence_ids = {item.get("evidence_id") for item in evidence.get("evidence", [])}
    disclosure_errors, _, approved_td_ids = _technical_disclosure_state(case_dir, evidence)
    errors.extend(disclosure_errors)
    feature_ids: list[str] = []
    for item in matrix.get("features", []):
        feature_ids.append(item.get("feature_id", ""))
        unknown = set(item.get("engineering_evidence_ids", [])) - evidence_ids
        if unknown:
            errors.append(
                f"Feature {item.get('feature_id')} references unknown evidence: "
                + ", ".join(sorted(unknown))
            )
        unknown_td = set(item.get("technical_disclosure_ids", [])) - approved_td_ids
        if unknown_td:
            errors.append(
                f"Feature {item.get('feature_id')} references unavailable technical disclosure: "
                + ", ".join(sorted(unknown_td))
            )
        errors.extend(
            _validate_effect_basis(
                str(item.get("distinguishing_effect", "")),
                item.get("effect_basis"),
                f"Feature {item.get('feature_id')}",
            )
        )
    if len(feature_ids) != len(set(feature_ids)):
        errors.append("Feature IDs must be unique")
    if not errors:
        _render_feature_matrix(case_dir, matrix)
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


def _validate_first_search(case_dir: Path, _: dict[str, Any]) -> list[str]:
    try:
        candidates = _load_json(case_dir / "02-invention-candidates.json", "invention candidates")
    except ValueError as exc:
        return [str(exc)]
    required = {item.get("candidate_id", "") for item in candidates.get("candidates", [])}
    return _validate_search(case_dir / "03-prior-art-search", required)


def _read_search_records(
    path: Path, additional_fields: set[str] | None = None
) -> tuple[list[str], list[tuple[int, dict[str, Any]]]]:
    records_path = path / "search-records.jsonl"
    if not records_path.exists():
        return [f"Missing structured search log: {records_path.relative_to(path.parent)}"], []
    errors: list[str] = []
    records: list[tuple[int, dict[str, Any]]] = []
    required_fields = SEARCH_FIELDS | (additional_fields or set())
    record_ids: list[str] = []
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
        errors.extend(
            f"Search line {line_number}: {error}"
            for error in validate_schema(record, "case-search-record.schema.json")
        )
        record_ids.append(str(record.get("record_id", "")))
        if record.get("result_count", 0) > 0 and not record.get("reviewed_reference_ids"):
            errors.append(f"Search line {line_number} returned results but reviewed no references")
        records.append((line_number, record))
    if not records:
        errors.append("Structured search log must contain at least one record")
    if len(record_ids) != len(set(record_ids)):
        errors.append("Search record IDs must be unique")
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
    errors.extend(validate_no_internal_prose_inside_claim_body(text))
    if structure_path is not None:
        errors.extend(_validate_claim_structure(text, structure_path))
    return errors


def _validate_claim_structure(text: str, structure_path: Path) -> list[str]:
    try:
        structure = _load_json(structure_path, "Claims V2 structure")
    except ValueError as exc:
        return [str(exc)]
    errors = validate_schema(structure, "claims-v2-structure.schema.json")
    entries = structure.get("independent_claims")
    if not isinstance(entries, list) or not entries:
        return errors + ["Claims V2 structure must contain independent_claims"]

    blocks = parse_claim_blocks(text)
    independent_numbers = independent_claim_numbers(text)
    parsed: dict[str, list[str]] = {}
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

    dependencies = claim_dependencies(text)
    dependent_entries = structure.get("dependent_claims", [])
    parsed_dependent: dict[str, list[str]] = {}
    for number, refs in sorted(dependencies.items()):
        claim_id = f"D{number}"
        labels, label_errors = _parse_dependent_limitation_lines(number, blocks[number])
        parsed_dependent[claim_id] = labels
        errors.extend(label_errors)
        entry = next(
            (
                item
                for item in dependent_entries
                if isinstance(item, dict) and item.get("claim_id") == claim_id
            ),
            None,
        )
        if entry is None:
            errors.append(f"Claims V2 structure is missing dependent claim {claim_id}")
            continue
        if entry.get("claim_number") != number or entry.get("depends_on") != refs:
            errors.append(f"Dependent claim {claim_id} has inconsistent dependency metadata")
        if entry.get("added_limitation_ids") != labels:
            errors.append(
                f"{claim_id} parser limitation IDs must exactly match added_limitation_ids"
            )
    structured_dependent_ids = {
        item.get("claim_id") for item in dependent_entries if isinstance(item, dict)
    }
    if structured_dependent_ids != set(parsed_dependent):
        errors.append("Claims V2 structure must cover exactly all dependent claims")
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


def _parse_dependent_limitation_lines(
    claim_number: int, lines: list[str]
) -> tuple[list[str], list[str]]:
    claim_id = f"D{claim_number}"
    labels: list[str] = []
    errors: list[str] = []
    for line_index, line in enumerate(lines):
        line_labels = TRACE_LABEL_RE.findall(line)
        if line_index == 0:
            if line_labels:
                errors.append(
                    f"Dependent claim {claim_number} must place its preamble before limitations"
                )
            if len(lines) == 1 or not line.rstrip().endswith(("：", ":")):
                errors.append(f"Dependent claim {claim_number} preamble must end with a colon")
            continue
        if len(line_labels) != 1 or not TRACE_LINE_RE.match(line):
            errors.append(f"Dependent claim {claim_number} must label every added limitation line")
            continue
        label = line_labels[0]
        if not label.startswith(f"{claim_id}-L"):
            errors.append(f"Trace label {label} does not belong to dependent claim {claim_number}")
        labels.append(label)
    expected = [f"{claim_id}-L{index}" for index in range(1, len(labels) + 1)]
    if labels != expected:
        errors.append(f"Dependent claim {claim_number} trace labels must be consecutive")
    if not labels:
        errors.append(f"Dependent claim {claim_number} has no trace-labelled added limitations")
    return labels, errors


def _validate_support_map(case_dir: Path, _: dict[str, Any]) -> list[str]:
    try:
        support = _load_json(case_dir / "09-claim-support-map.json", "claim support map")
        structure = _load_json(case_dir / "08-claims-v2-structure.json", "Claims V2 structure")
        evidence = _load_json(case_dir / "01-code-evidence-map.json", "evidence map")
    except ValueError as exc:
        return [str(exc)]
    expected = {
        limitation_id
        for entry in structure.get("independent_claims", [])
        if isinstance(entry, dict)
        for limitation_id in entry.get("limitation_ids", [])
    }
    expected.update(
        limitation_id
        for entry in structure.get("dependent_claims", [])
        if isinstance(entry, dict)
        for limitation_id in entry.get("added_limitation_ids", [])
    )
    errors = validate_schema(support, "claim-support-map.schema.json")
    evidence_ids = {item.get("evidence_id") for item in evidence.get("evidence", [])}
    disclosure_errors, _, approved_td_ids = _technical_disclosure_state(case_dir, evidence)
    errors.extend(disclosure_errors)
    mapped: list[str] = []
    independent_engineering_anchors: dict[str, set[str]] = {
        str(entry.get("claim_id")): set()
        for entry in structure.get("independent_claims", [])
        if isinstance(entry, dict)
    }
    for item in support.get("limitations", []):
        limitation_id = item.get("limitation_id", "")
        mapped.append(limitation_id)
        if item.get("claim_id") != limitation_id.split("-L", 1)[0]:
            errors.append(f"Claim support {limitation_id} has inconsistent claim_id")
        if set(item.get("engineering_evidence_ids", [])) - evidence_ids:
            errors.append(f"Claim support {limitation_id} references unknown evidence")
        if set(item.get("technical_disclosure_ids", [])) - approved_td_ids:
            errors.append(
                f"Claim support {limitation_id} references unavailable technical disclosure"
            )
        if item.get("claim_id") in independent_engineering_anchors:
            independent_engineering_anchors[item["claim_id"]].update(
                item.get("engineering_evidence_ids", [])
            )
        errors.extend(
            _validate_effect_basis(
                str(item.get("technical_effect", "")),
                item.get("effect_basis"),
                f"Claim support {limitation_id}",
            )
        )
    if len(mapped) != len(set(mapped)):
        errors.append("Claim support limitation IDs must be unique")
    if set(mapped) != expected:
        errors.append(
            "Claim support map must cover exactly all independent and dependent limitations"
        )
    unanchored = sorted(
        claim_id for claim_id, anchors in independent_engineering_anchors.items() if not anchors
    )
    if unanchored:
        errors.append(
            "Independent claims must retain engineering-evidence anchors: "
            + ", ".join(unanchored)
        )
    if not errors:
        _render_claim_support_map(case_dir, support)
    return errors


def _validate_final_search(case_dir: Path, _: dict[str, Any]) -> list[str]:
    path = case_dir / "10-final-search"
    errors, records = _read_search_records(path, FINAL_SEARCH_FIELDS)
    try:
        structure = _load_json(case_dir / "08-claims-v2-structure.json", "Claims V2 structure")
        session = _load_json(path / "search-session.json", "final search session")
    except ValueError as exc:
        return errors + [str(exc)]
    errors.extend(validate_schema(session, "final-search-session.schema.json"))
    status = _load_status(case_dir)
    if session.get("revision") != status.get("revision", 0):
        errors.append("Final search session is stale against the current case revision")
    expected_source = {
        "claims_v2_sha256": _sha256_file(case_dir / "08-claims-v2.md"),
        "claims_v2_structure_sha256": _sha256_file(case_dir / "08-claims-v2-structure.json"),
    }
    if session.get("source") != expected_source:
        errors.append("Final search is stale against current Claims V2")
    if not session.get("completed_at"):
        errors.append("Final search session has not been marked completed")

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
    figures_path = application / "figures.json"
    metadata_path = application / "application-metadata.json"
    errors: list[str] = []
    for path in (
        claims_path,
        specification_path,
        abstract_path,
        metadata_path,
    ):
        if not path.exists():
            errors.append(f"Missing application draft artifact: {path.name}")
    if errors:
        return errors

    claims_v2 = (case_dir / "08-claims-v2.md").read_text(encoding="utf-8")
    claims_final = claims_path.read_text(encoding="utf-8")
    try:
        expected_claims = render_filing_claims(claims_v2)
    except ValueError as exc:
        errors.append(f"Claims V2 cannot be rendered for filing: {exc}")
        expected_claims = ""
    if claims_final != expected_claims:
        errors.append(
            "claims-final.md must exactly match the canonical filing rendering of Claims V2"
        )
    if TRACE_LABEL_RE.search(claims_final):
        errors.append("claims-final.md still contains internal trace labels")
    errors.extend(validate_claims_cn(claims_final))
    forbidden_markers = (
        "# Claims V2",
        "内部追踪",
        "待同步",
        "待确认",
        "[I1-",
        "[D1-",
    )
    for marker in forbidden_markers:
        if marker in claims_final:
            errors.append(f"claims-final.md contains forbidden filing marker: {marker}")

    specification = specification_path.read_text(encoding="utf-8")
    abstract = abstract_path.read_text(encoding="utf-8")
    drawings = drawings_path.read_text(encoding="utf-8") if drawings_path.exists() else ""
    for name, content in (
        ("specification-final.md", specification),
        ("abstract.md", abstract),
    ):
        if "【待" in content or "待同步" in content:
            errors.append(f"{name} still contains pending application-draft content")
    errors.extend(validate_abstract_cn(abstract))
    if not _meaningful_markdown(specification):
        errors.append("specification-final.md has no substantive content")

    try:
        metadata = _load_json(metadata_path, "application metadata")
        structure = _load_json(case_dir / "08-claims-v2-structure.json", "Claims V2 structure")
    except ValueError as exc:
        return errors + [str(exc)]
    errors.extend(validate_schema(metadata, "application-metadata.schema.json"))
    drawing_decision = metadata.get("drawings", {})
    if "【待" in str(drawing_decision.get("reason", "")):
        errors.append("Application drawings decision is still pending")
    if drawing_decision.get("abstract_figure_required") and not drawing_decision.get("required"):
        errors.append(
            "An abstract figure cannot be required when specification drawings are absent"
        )
    errors.extend(
        _validate_figures(
            case_dir,
            figures_path,
            drawing_decision,
            drawings,
            structure,
        )
    )
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
    expected_ids.update(
        limitation_id
        for entry in structure.get("dependent_claims", [])
        if isinstance(entry, dict)
        for limitation_id in entry.get("added_limitation_ids", [])
    )
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
    try:
        audit = _load_json(case_dir / "13-final-audit.json", "final audit")
        structure = _load_json(case_dir / "08-claims-v2-structure.json", "Claims V2 structure")
    except ValueError as exc:
        return [str(exc)]
    errors = validate_schema(audit, "final-audit.schema.json")
    support: dict[str, Any] = {"limitations": []}
    disclosures: dict[str, Any] = {"disclosures": []}
    approved_td_ids: set[str] = set()
    try:
        support = _load_json(case_dir / "09-claim-support-map.json", "claim support map")
        evidence = _load_json(case_dir / "01-code-evidence-map.json", "evidence map")
    except ValueError as exc:
        errors.append(str(exc))
    else:
        disclosure_errors, disclosures, approved_td_ids = _technical_disclosure_state(
            case_dir, evidence
        )
        errors.extend(disclosure_errors)
    try:
        application_snapshot = _application_hash_snapshot(case_dir)
    except (OSError, ValueError) as exc:
        errors.append(str(exc))
    else:
        if audit.get("audited_application") != application_snapshot:
            errors.append("Final audit is stale against the current application draft")
    claim_ids = {entry.get("claim_id") for entry in structure.get("independent_claims", [])}
    limitation_ids = {
        limitation
        for entry in structure.get("independent_claims", [])
        for limitation in entry.get("limitation_ids", [])
    }
    distinguishing_ids = {
        limitation
        for entry in structure.get("independent_claims", [])
        for limitation in entry.get("distinguishing_limitation_ids", [])
    }
    novelty_ids = set(audit.get("novelty", {}))
    if novelty_ids != claim_ids:
        errors.append("Final audit novelty must cover exactly all independent claims")
    inventive_ids = set(audit.get("inventive_step", {}).get("distinguishing_limitation_ids", []))
    if not inventive_ids <= limitation_ids:
        errors.append("Final audit inventive-step analysis references unknown limitations")
    if not distinguishing_ids <= inventive_ids:
        errors.append("Final audit inventive-step analysis omits distinguishing limitations")
    reference_ids = _search_reference_ids(case_dir / "10-final-search")
    cited = set(audit.get("inventive_step", {}).get("closest_prior_art", []))
    for item in audit.get("novelty", {}).values():
        cited.update(item.get("closest_reference_ids", []))
    if cited - reference_ids:
        errors.append("Final audit cites references absent from final-search records")

    used_td: dict[str, set[str]] = {}
    for item in support.get("limitations", []):
        for disclosure_id in item.get("technical_disclosure_ids", []):
            used_td.setdefault(disclosure_id, set()).add(item.get("limitation_id", ""))
    disclosure_map = {
        item.get("disclosure_id"): item for item in disclosures.get("disclosures", [])
    }
    expected_unimplemented = {
        disclosure_id
        for disclosure_id in used_td
        if disclosure_id in approved_td_ids
        and disclosure_map.get(disclosure_id, {}).get("implementation_status")
        in {"partially_implemented", "designed_not_implemented"}
    }
    reported = {
        item.get("disclosure_id"): item
        for item in audit.get("unimplemented_disclosures", [])
    }
    if set(reported) != expected_unimplemented:
        errors.append(
            "Final audit must disclose exactly all claim-used unimplemented technical disclosures"
        )
    for disclosure_id, item in reported.items():
        source = disclosure_map.get(disclosure_id, {})
        if set(item.get("used_in_limitations", [])) != used_td.get(disclosure_id, set()):
            errors.append(
                f"Final audit has stale limitation usage for technical disclosure {disclosure_id}"
            )
        if item.get("implementation_status") != source.get("implementation_status"):
            errors.append(
                "Final audit has stale implementation status for technical disclosure "
                f"{disclosure_id}"
            )
    if not errors:
        _render_final_audit(case_dir, audit)
    return errors


def _validate_content_ready(case_dir: Path, _: dict[str, Any]) -> list[str]:
    try:
        ledger = _load_json(case_dir / "context-questions.json", "context questions")
    except ValueError as exc:
        return [str(exc)]
    errors = validate_schema(ledger, "context-questions.schema.json")
    identifiers = [item.get("id") for item in ledger.get("questions", [])]
    if len(identifiers) != len(set(identifiers)):
        errors.append("Context question IDs must be unique")
    for item in ledger.get("questions", []):
        if item.get("status") == "resolved" and (
            not str(item.get("resolution") or "").strip()
            or not str(item.get("source") or "").strip()
            or not item.get("resolved_at")
        ):
            errors.append(f"Resolved context question {item.get('id')} lacks answer provenance")
    unresolved = [
        item.get("id", "unknown")
        for item in ledger.get("questions", [])
        if item.get("category") == "technical"
        and item.get("blocking") is True
        and (
            item.get("status") != "resolved"
            or item.get("resolution_type") == "unknown"
        )
    ]
    if unresolved:
        errors.append("Unresolved blocking technical questions: " + ", ".join(unresolved))
    return errors


def _validate_independent_audit(case_dir: Path, _: dict[str, Any]) -> list[str]:
    directory = case_dir / "filing-package" / "huang-audit"
    try:
        audit = _load_json(directory / "independent-audit.json", "independent audit")
        structure = _load_json(case_dir / "08-claims-v2-structure.json", "Claims V2 structure")
    except ValueError as exc:
        return [str(exc)]
    errors = validate_schema(audit, "independent-audit.schema.json")
    if audit.get("source_application") != _application_hash_snapshot(case_dir):
        errors.append("Independent audit is stale against the current application")
    if audit.get("source_final_audit_sha256") != _sha256_file(case_dir / "13-final-audit.json"):
        errors.append("Independent audit is stale against the current final audit")
    known_revisions = {
        item.get("revision_id") for item in _load_status(case_dir).get("revision_history", [])
    }
    claim_numbers = {
        item.get("claim_number")
        for key in ("independent_claims", "dependent_claims")
        for item in structure.get(key, [])
    }
    limitation_ids = {
        limitation
        for key in ("independent_claims", "dependent_claims")
        for item in structure.get(key, [])
        for limitation in item.get("limitation_ids", item.get("added_limitation_ids", []))
    }
    finding_ids: list[str] = []
    attorney_risk = False
    for finding in audit.get("findings", []):
        finding_id = finding.get("finding_id", "unknown")
        finding_ids.append(finding_id)
        disposition = finding.get("disposition")
        severity = finding.get("severity")
        if set(finding.get("affected_claims", [])) - claim_numbers:
            errors.append(f"{finding_id} references unknown claims")
        if set(finding.get("affected_limitation_ids", [])) - limitation_ids:
            errors.append(f"{finding_id} references unknown limitations")
        if disposition == "revision_required":
            errors.append(f"{finding_id} requires a canonical revision before DOCX rendering")
        if severity == "blocking" and disposition != "resolved_by_revision":
            errors.append(f"Blocking finding {finding_id} must be resolved by revision")
        if disposition in {"rejected_with_reason", "no_change_needed", "attorney_review_required"}:
            if not str(finding.get("resolution") or "").strip():
                errors.append(f"{finding_id} disposition requires a written resolution")
        if disposition == "resolved_by_revision":
            if finding.get("revision_id") not in known_revisions:
                errors.append(f"{finding_id} references an unknown canonical revision")
            if not str(finding.get("resolution") or "").strip():
                errors.append(f"{finding_id} resolved revision requires an explanation")
        if disposition == "attorney_review_required":
            attorney_risk = True
    if len(finding_ids) != len(set(finding_ids)):
        errors.append("Independent audit finding IDs must be unique")
    expected_status = "RESOLVED_WITH_ATTORNEY_REVIEW" if attorney_risk else "RESOLVED"
    if audit.get("overall_status") != expected_status:
        errors.append(f"Independent audit overall_status must be {expected_status}")
    if not errors:
        _render_independent_audit(directory, audit)
    return errors


def required_docx_subjects(case_dir: Path) -> tuple[str, ...]:
    metadata = _load_json(
        case_dir / "12-application" / "application-metadata.json", "application metadata"
    )
    drawings = metadata.get("drawings")
    if not isinstance(drawings, dict):
        raise ValueError("Application metadata lacks a drawings decision")
    subjects = list(BASE_REQUIRED_DOCX_SUBJECTS)
    if drawings.get("required"):
        subjects.append("说明书附图")
    if drawings.get("abstract_figure_required"):
        subjects.append("摘要附图")
    return tuple(subjects)


def _validate_figures(
    case_dir: Path,
    manifest_path: Path,
    decision: dict[str, Any],
    drawings_description: str,
    structure: dict[str, Any],
) -> list[str]:
    try:
        manifest = _load_json(manifest_path, "figure manifest")
        evidence_map = _load_json(case_dir / "01-code-evidence-map.json", "evidence map")
    except ValueError as exc:
        return [str(exc)]
    errors = validate_schema(manifest, "figure-manifest.schema.json")
    required = decision.get("required") is True
    if manifest.get("figures_required") is not required:
        errors.append("Figure manifest must match the application drawings decision")
    figures = manifest.get("figures", [])
    if not required:
        if figures or manifest.get("abstract_figure_id") is not None:
            errors.append("No-drawings application must have an empty figure manifest")
        if (
            decision.get("abstract_figure_required")
            or decision.get("abstract_figure_id") is not None
        ):
            errors.append("No-drawings application cannot designate an abstract figure")
        return errors
    if not drawings_description or not _meaningful_markdown(drawings_description):
        errors.append("Drawings-required application needs a substantive drawings description")
    if not figures:
        errors.append("Drawings-required application needs at least one canonical figure")

    evidence_ids = {item.get("evidence_id") for item in evidence_map.get("evidence", [])}
    disclosure_errors, _, approved_td_ids = _technical_disclosure_state(case_dir, evidence_map)
    errors.extend(disclosure_errors)
    limitation_ids = {
        limitation
        for key in ("independent_claims", "dependent_claims")
        for entry in structure.get(key, [])
        for limitation in entry.get("limitation_ids", entry.get("added_limitation_ids", []))
    }
    figure_ids: set[str] = set()
    for figure in figures:
        figure_id = figure.get("figure_id")
        if figure_id in figure_ids:
            errors.append(f"Duplicate figure ID: {figure_id}")
        figure_ids.add(figure_id)
        unknown_evidence = set(figure.get("engineering_evidence_ids", [])) - evidence_ids
        if unknown_evidence:
            errors.append(f"Figure {figure_id} references unknown engineering evidence")
        unknown_td = set(figure.get("technical_disclosure_ids", [])) - approved_td_ids
        if unknown_td:
            errors.append(f"Figure {figure_id} references unavailable technical disclosure")
        unknown_limitations = set(figure.get("claim_limitation_ids", [])) - limitation_ids
        if unknown_limitations:
            errors.append(f"Figure {figure_id} references unknown claim limitations")
        relative = Path(str(figure.get("file", "")))
        file_path = case_dir / "12-application" / relative
        if not file_path.exists() or not file_path.is_file():
            errors.append(f"Figure file is missing: {relative}")
        elif hashlib.sha256(file_path.read_bytes()).hexdigest() != figure.get("sha256"):
            errors.append(f"Figure file hash is stale: {figure_id}")
    abstract_id = manifest.get("abstract_figure_id")
    if decision.get("abstract_figure_required"):
        if not abstract_id or abstract_id not in figure_ids:
            errors.append("Required abstract figure must identify a canonical figure")
        if decision.get("abstract_figure_id") != abstract_id:
            errors.append("Application metadata and figure manifest disagree on abstract figure")
    elif abstract_id is not None or decision.get("abstract_figure_id") is not None:
        errors.append("Abstract figure is designated although it is not required")
    return errors


def _validate_docx_package(case_dir: Path, _: dict[str, Any]) -> list[str]:
    path = case_dir / "filing-package" / "docx"
    documents = list(path.glob("*.docx")) if path.exists() else []
    errors: list[str] = []
    used_documents: set[Path] = set()
    try:
        subjects = required_docx_subjects(case_dir)
    except ValueError as exc:
        return [str(exc)]
    for subject in sorted(subjects, key=len, reverse=True):
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
    scan = scan_archive(project)
    files = scan["files"]
    archive_sha = hashlib.sha256(project.read_bytes()).hexdigest()
    return {
        "snapshot_type": "uploaded_archive",
        "captured_at": datetime.now(UTC).isoformat(),
        "project_source": str(project),
        "snapshot_sha256": archive_sha,
        "archive_sha256": archive_sha,
        "manifest_sha256": _manifest_digest(files),
        "file_count": scan["file_count"],
        "languages": scan["languages"],
        "security_warnings": scan["security_warnings"],
        "excluded_files": scan["excluded_files"],
        "limits": scan["limits"],
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


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _meaningful_markdown(text: str) -> list[str]:
    return [
        line
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith(("#", ">"))
    ]


def _markdown_cell(value: Any) -> str:
    if isinstance(value, list):
        value = "；".join(str(item) for item in value)
    return str(value).replace("|", "\\|").replace("\n", " ")


def _render_evidence_map(case_dir: Path, data: dict[str, Any]) -> None:
    lines = [
        "# 技术证据地图",
        "",
        "> 本文件由 01-code-evidence-map.json 自动生成；请只编辑 JSON 事实源。",
        "",
        "| 证据编号 | 代码/文档证据 | 处理步骤 | 数据或状态变化 | 技术效果 | 效果依据 | 证据状态 |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in data.get("evidence", []):
        source = item.get("source", {})
        location = source.get("path", "")
        if source.get("symbol"):
            location += f"::{source['symbol']}"
        lines.append(
            "| "
            + " | ".join(
                _markdown_cell(value)
                for value in (
                    item.get("evidence_id", ""),
                    location,
                    item.get("processing_step", ""),
                    item.get("state_change", ""),
                    item.get("technical_effect", ""),
                    item.get("effect_basis", ""),
                    item.get("status", ""),
                )
            )
            + " |"
        )
    (case_dir / "01-code-evidence-map.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _render_technical_disclosures(case_dir: Path, data: dict[str, Any]) -> None:
    lines = [
        "# 已确认技术披露",
        "",
        "> 本文件由 01-technical-disclosures.json 自动生成；"
        "TD 是用户确认的技术披露，不是工程证据。",
        "",
        "| 披露编号 | 来源问题 | 技术陈述 | 实现状态 | 充分公开 | 技术效果 | 效果依据 | 生命周期 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for item in data.get("disclosures", []):
        effect = item.get("technical_effect", {})
        lines.append(
            "| "
            + " | ".join(
                _markdown_cell(value)
                for value in (
                    item.get("disclosure_id", ""),
                    item.get("question_id", ""),
                    item.get("statement", ""),
                    item.get("implementation_status", ""),
                    item.get("enablement", {}).get("status", ""),
                    effect.get("statement", ""),
                    effect.get("effect_basis", ""),
                    item.get("lifecycle_status", ""),
                )
            )
            + " |"
        )
    (case_dir / "01-technical-disclosures.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def _render_invention_candidates(case_dir: Path, data: dict[str, Any]) -> None:
    lines = [
        "# 候选发明",
        "",
        "> 本文件由 02-invention-candidates.json 自动生成；请只编辑 JSON 事实源。",
        "",
        "| 候选 | 名称 | 技术问题 | 核心机制 | 关键区别特征 | 技术效果 | "
        "效果依据 | 工程证据 | 技术披露 | 风险 |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for item in data.get("candidates", []):
        lines.append(
            "| "
            + " | ".join(
                _markdown_cell(value)
                for value in (
                    item.get("candidate_id", ""),
                    item.get("title", ""),
                    item.get("technical_problem", ""),
                    item.get("mechanism", ""),
                    item.get("distinguishing_features", []),
                    item.get("technical_effects", []),
                    item.get("effect_basis", ""),
                    item.get("engineering_evidence_ids", []),
                    item.get("technical_disclosure_ids", []),
                    item.get("risk", ""),
                )
            )
            + " |"
        )
    (case_dir / "02-invention-candidates.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _render_feature_matrix(case_dir: Path, data: dict[str, Any]) -> None:
    lines = [
        "# 区别特征矩阵",
        "",
        "> 本文件由 04-feature-matrix.json 自动生成；请只编辑 JSON 事实源。",
        "",
        "| 特征编号 | 技术特征 | 工程证据 | 技术披露 | 现有技术披露 | 区别与技术效果 | 效果依据 |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in data.get("features", []):
        references = "；".join(
            f"{key}: {value}" for key, value in sorted(item.get("references", {}).items())
        )
        lines.append(
            "| "
            + " | ".join(
                _markdown_cell(value)
                for value in (
                    item.get("feature_id", ""),
                    item.get("feature", ""),
                    item.get("engineering_evidence_ids", []),
                    item.get("technical_disclosure_ids", []),
                    references,
                    item.get("distinguishing_effect", ""),
                    item.get("effect_basis", ""),
                )
            )
            + " |"
        )
    (case_dir / "04-feature-matrix.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _render_claim_support_map(case_dir: Path, data: dict[str, Any]) -> None:
    lines = [
        "# 权利要求支持映射",
        "",
        "> 本文件由 09-claim-support-map.json 自动生成；请只编辑 JSON 事实源。",
        "",
        "| 限定 | 权利要求 | 工程证据 | 技术披露 | 说明书明确支持 | 技术效果 | 效果依据 | 状态 |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for item in data.get("limitations", []):
        lines.append(
            "| "
            + " | ".join(
                _markdown_cell(value)
                for value in (
                    item.get("limitation_id", ""),
                    item.get("claim_id", ""),
                    item.get("engineering_evidence_ids", []),
                    item.get("technical_disclosure_ids", []),
                    item.get("specification_sections", []),
                    item.get("technical_effect", ""),
                    item.get("effect_basis", ""),
                    item.get("status", ""),
                )
            )
            + " |"
        )
    (case_dir / "09-claim-support-map.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _render_context_questions(case_dir: Path, data: dict[str, Any]) -> None:
    lines = [
        "# 上下文确认记录",
        "",
        "> 本文件由 context-questions.json 自动生成；问题是否阻断由结构化字段计算。",
        "",
        "| 编号 | 类别 | 问题 | 阻断 | 影响 | 候选补全 | 处理结果 | TD | 状态 | 答案 | 来源 |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for item in data.get("questions", []):
        lines.append(
            "| "
            + " | ".join(
                _markdown_cell(value or "")
                for value in (
                    item.get("id"),
                    item.get("category"),
                    item.get("question"),
                    item.get("blocking"),
                    item.get("impact"),
                    item.get("candidate_completion", {}).get("statement", ""),
                    item.get("resolution_type", ""),
                    item.get("resulting_disclosure_ids", []),
                    item.get("status"),
                    item.get("resolution"),
                    item.get("source"),
                )
            )
            + " |"
        )
    (case_dir / "context-ledger.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _search_reference_ids(path: Path) -> set[str]:
    _, records = _read_search_records(path, FINAL_SEARCH_FIELDS)
    return {
        str(reference)
        for _, record in records
        for reference in record.get("reviewed_reference_ids", [])
    }


def _render_final_audit(case_dir: Path, data: dict[str, Any]) -> None:
    labels = {
        "eligibility": "专利客体",
        "clarity_and_support": "清楚性与支持性",
        "enablement": "充分公开",
        "unity": "单一性与拆案",
        "amendment_basis": "修改依据",
        "sensitive_information": "敏感信息",
    }
    lines = [
        "# 最终审计",
        "",
        "> 本文件由 13-final-audit.json 自动生成；审计结论、依据、风险和行动均以 JSON 为准。",
        "",
        "## 新颖性",
        "",
    ]
    for claim_id, item in sorted(data.get("novelty", {}).items()):
        lines.extend(
            [
                f"### {claim_id} — {item.get('status', '')}",
                "",
                f"- 最接近文献：{_markdown_cell(item.get('closest_reference_ids', []))}",
                f"- 单篇完整公开：{item.get('single_reference_full_disclosure', '')}",
                f"- 结论：{item.get('conclusion', '')}",
                f"- 依据：{_markdown_cell(item.get('evidence_refs', []))}",
                f"- 剩余风险：{item.get('residual_risk', '')}",
                f"- 建议处理：{item.get('recommended_action', '')}",
                "",
            ]
        )
    inventive = data.get("inventive_step", {})
    lines.extend(
        [
            "## 创造性",
            "",
            f"- 状态：{inventive.get('status', '')}",
            f"- 最接近现有技术：{_markdown_cell(inventive.get('closest_prior_art', []))}",
            f"- 区别限定：{_markdown_cell(inventive.get('distinguishing_limitation_ids', []))}",
            f"- 技术效果：{_markdown_cell(inventive.get('technical_effects', []))}",
            f"- 客观技术问题：{inventive.get('objective_technical_problem', '')}",
            f"- 组合动机：{inventive.get('combination_motivation', '')}",
            f"- 结论：{inventive.get('conclusion', '')}",
            f"- 剩余风险：{inventive.get('residual_risk', '')}",
            f"- 建议处理：{inventive.get('recommended_action', '')}",
            "",
        ]
    )
    for key, heading in labels.items():
        item = data.get(key, {})
        lines.extend(
            [
                f"## {heading}",
                "",
                f"- 状态：{item.get('status', '')}",
                f"- 结论：{item.get('conclusion', '')}",
                f"- 依据：{_markdown_cell(item.get('evidence_refs', []))}",
                f"- 剩余风险：{item.get('residual_risk', '')}",
                f"- 建议处理：{item.get('recommended_action', '')}",
                "",
            ]
        )
    lines.extend(["## 尚未在当前工程快照中完整实现的技术披露", ""])
    disclosures = data.get("unimplemented_disclosures", [])
    if not disclosures:
        lines.extend(["- 无。", ""])
    for item in disclosures:
        lines.extend(
            [
                f"### {item.get('disclosure_id', '')}",
                "",
                f"- 实现状态：{item.get('implementation_status', '')}",
                f"- 充分公开：{item.get('enablement_status', '')}",
                f"- 使用限定：{_markdown_cell(item.get('used_in_limitations', []))}",
                "",
            ]
        )
    (case_dir / "13-final-audit.md").write_text("\n".join(lines), encoding="utf-8")


def _render_independent_audit(directory: Path, data: dict[str, Any]) -> None:
    lines = [
        "# 独立审稿与协调记录",
        "",
        "> 本文件由 independent-audit.json 自动生成；不得在 Markdown 中关闭 finding。",
        "",
        f"- 审计编号：{data.get('audit_id', '')}",
        f"- 审稿工具：{data.get('auditor', {}).get('tool', '')}",
        f"- 总体状态：{data.get('overall_status', '')}",
        "",
    ]
    for finding in data.get("findings", []):
        lines.extend(
            [
                f"## {finding.get('finding_id', '')} — {finding.get('severity', '')}",
                "",
                f"- 类别：{finding.get('category', '')}",
                f"- 影响权利要求：{_markdown_cell(finding.get('affected_claims', []))}",
                f"- 影响限定：{_markdown_cell(finding.get('affected_limitation_ids', []))}",
                f"- 发现：{finding.get('finding', '')}",
                f"- 建议：{finding.get('recommendation', '')}",
                f"- 处置：{finding.get('disposition', '')}",
                f"- 协调说明：{finding.get('resolution') or ''}",
                f"- 修订：{finding.get('revision_id') or ''}",
                "",
            ]
        )
    (directory / "independent-audit.md").write_text("\n".join(lines), encoding="utf-8")


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
