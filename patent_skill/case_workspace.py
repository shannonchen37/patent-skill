from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .scanner import scan_repository


CASE_FILES = {
    "context-ledger.md": """# 上下文确认记录

## 已确认事实

| 日期 | 事实 | 来源 | 影响文档 |
|---|---|---|---|

## 待确认问题

| 优先级 | 当前证据 | 不确定内容 | 为什么影响专利 | 状态 |
|---|---|---|---|---|

## 已排除或被否定的内容

| 内容 | 原因 | 证据/确认 |
|---|---|---|
""",
    "01-code-evidence-map.md": """# 技术证据地图

> 当前阶段只记录代码证据、处理步骤、数据或状态变化及技术效果，不写权利要求。

| 证据编号 | 代码/文档证据 | 处理步骤 | 数据或状态变化 | 技术效果 | 证据状态 |
|---|---|---|---|---|---|
""",
    "02-invention-candidates.md": """# 候选发明

> 从技术证据地图中提取 3–5 个完整候选。未经用户确认不得选择主发明。

| 候选 | 技术问题 | 核心技术机制 | 关键区别特征 | 技术效果 | 代码证据 | 主要风险 |
|---|---|---|---|---|---|---|
""",
    "04-feature-matrix.md": """# 区别特征矩阵

> 在第一次查新完成并由用户确认主发明后填写。

| 权利要求特征 | 代码支持 | D1 | D2 | D3 | 区别与技术效果 |
|---|---|---|---|---|---|
""",
    "05-claims-v1.md": """# Claims V1

> 仅在查新和区别特征确认后起草。每项限定必须回溯到技术证据地图。
""",
    "06-specification-v1.md": """# 说明书 V1

> 以 Claims V1 为保护策略骨架，补充替代方案、参数、数据结构、模块交互、异常路径和部署方式。
""",
    "07-claim-support-map.md": """# 权利要求支持映射

| Claims V2 限定 | Claims V1 来源 | 代码/设计证据 | 说明书段落 | 技术效果 | 确认状态 |
|---|---|---|---|---|---|
""",
    "08-claims-v2.md": """# Claims V2

> 在完整说明书基础上修订。每项限定须同时具有工程证据和说明书支持。
""",
    "10-final-audit.md": """# 最终审计

## Shannon 主流程复核

- 新颖性：待复核
- 创造性：待复核
- 专利客体：待复核
- 清楚性与支持性：待复核
- 充分公开：待复核
- 单一性/拆案：待复核
- 修改依据：待复核
- 敏感信息：待复核

## Huang 独立审稿结论

> 仅接收独立审稿意见；不得由外部 Skill 重选发明点或覆盖本案件事实。
""",
}

REQUIRED_CASE_PATHS = (
    "case-status.json",
    "context-ledger.md",
    "00-project-snapshot/snapshot-manifest.json",
    "01-code-evidence-map.md",
    "02-invention-candidates.md",
    "03-prior-art-search/shannon",
    "03-prior-art-search/yjmm10",
    "04-feature-matrix.md",
    "05-claims-v1.md",
    "06-specification-v1.md",
    "07-claim-support-map.md",
    "08-claims-v2.md",
    "09-final-search/shannon",
    "09-final-search/yjmm10",
    "10-final-audit.md",
    "filing-package/huang-audit",
    "filing-package/docx",
)

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


def init_case_workspace(case_dir: Path, project: Path, title: str = "") -> dict[str, Any]:
    case_dir = case_dir.resolve()
    project = project.resolve()
    if not project.is_dir():
        raise ValueError(f"Project directory not found: {project}")
    status_path = case_dir / "case-status.json"
    if status_path.exists():
        raise ValueError(f"Patent case already exists: {case_dir}")

    snapshot_dir = case_dir / "00-project-snapshot"
    for directory in (
        snapshot_dir,
        case_dir / "03-prior-art-search" / "shannon",
        case_dir / "03-prior-art-search" / "yjmm10",
        case_dir / "09-final-search" / "shannon",
        case_dir / "09-final-search" / "yjmm10",
        case_dir / "filing-package" / "huang-audit",
        case_dir / "filing-package" / "docx",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    scan = scan_repository(project)
    snapshot = {
        "captured_at": datetime.now(UTC).isoformat(),
        "project_root": str(project),
        "git": _git_snapshot(project),
        "file_count": scan["file_count"],
        "languages": scan["languages"],
        "security_warnings": scan["security_warnings"],
        "files": [_file_record(project, item) for item in scan["files"]],
    }
    _write_json(snapshot_dir / "snapshot-manifest.json", snapshot)
    (snapshot_dir / "disclosure-history.md").write_text(
        "# 公开历史\n\n- 项目开始时间：【待确认】\n- 核心机制首次实现时间：【待确认】\n"
        "- GitHub/产品/论文/演讲首次公开时间：【待确认】\n- 公开内容范围：【待确认】\n",
        encoding="utf-8",
    )
    (snapshot_dir / "contributors.md").write_text(
        "# 核心技术贡献人\n\n| 姓名 | 实质性技术贡献 | 证据 | 是否拟列发明人 |\n"
        "|---|---|---|---|\n",
        encoding="utf-8",
    )
    (snapshot_dir / "README.md").write_text(
        "# 专利证据版本\n\n本目录记录分析所依据的项目路径、Git 提交、工作树状态、"
        "文件摘要、安全警告、公开历史和技术贡献人。它不复制源代码，也不自动创建 Git tag。"
        "如工作树非干净状态，应先由用户确认冻结提交或 tag。\n",
        encoding="utf-8",
    )

    for relative, content in CASE_FILES.items():
        (case_dir / relative).write_text(content, encoding="utf-8")
    for relative in (
        "03-prior-art-search/shannon/README.md",
        "03-prior-art-search/yjmm10/README.md",
        "09-final-search/shannon/README.md",
        "09-final-search/yjmm10/README.md",
    ):
        (case_dir / relative).write_text(
            "# 检索输出\n\n保留查询式、数据库、日期、原始命中、筛选记录、核验 URL 和覆盖限制。\n",
            encoding="utf-8",
        )
    (case_dir / "filing-package" / "README.md").write_text(
        "# Filing package\n\n仅在 Claims V2、第二次检索和最终审计完成后生成。"
        "Huang cn-patent-drafting 只负责独立审稿与分件 DOCX 输出。\n",
        encoding="utf-8",
    )

    status = {
        "canonical_source": "patent-skill",
        "case_dir": str(case_dir),
        "project_root": str(project),
        "proposed_title": title,
        "current_stage": "PROJECT_SNAPSHOT",
        "current_gate": "SNAPSHOT_CONFIRMATION",
        "material_questions_open": True,
        "external_roles": {
            "yjmm10/patent-skills": "CNIPA_SEARCH_ONLY",
            "HuangXinzhe/cn-patent-drafting": "FINAL_AUDIT_AND_DOCX_ONLY",
        },
    }
    _write_json(status_path, status)
    return {"status": status, "snapshot": snapshot}


def validate_case_workspace(case_dir: Path) -> list[str]:
    case_dir = case_dir.resolve()
    errors: list[str] = []
    for relative in REQUIRED_CASE_PATHS:
        if not (case_dir / relative).exists():
            errors.append(f"Missing case artifact: {relative}")
    status_path = case_dir / "case-status.json"
    if not status_path.exists():
        return errors
    try:
        status = json.loads(status_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"Invalid case-status.json: {exc}")
        return errors
    if status.get("canonical_source") != "patent-skill":
        errors.append("canonical_source must be patent-skill")
    if status.get("current_stage") == "FILING_READY":
        errors.append("FILING_READY cannot be set by this tool")
    if status.get("current_stage") == "READY_FOR_ATTORNEY_REVIEW":
        if status.get("material_questions_open"):
            errors.append("Material questions remain open")
        docx_names = [path.name for path in (case_dir / "filing-package" / "docx").glob("*.docx")]
        for subject in REQUIRED_DOCX_SUBJECTS:
            if not any(subject in name for name in docx_names):
                errors.append(f"Missing attorney-review DOCX subject: {subject}")
    return errors


def _git_snapshot(project: Path) -> dict[str, Any]:
    def run(*args: str) -> str:
        completed = subprocess.run(
            ["git", "-C", str(project), *args],
            check=False,
            capture_output=True,
            text=True,
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
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {**item, "sha256": digest}


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
