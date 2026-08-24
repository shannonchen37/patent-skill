import json
import subprocess
import zipfile
from pathlib import Path

import pytest

from patent_skill.case_workspace import (
    REQUIRED_DOCX_SUBJECTS,
    _validate_claims_stage,
    _validate_docx_file,
    _validate_final_search,
    _validate_support_map,
    advance_stage,
    init_case_workspace,
    validate_case_workspace,
)


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _search_record(candidate: str = "P001") -> str:
    return (
        json.dumps(
            {
                "database": "CNIPA",
                "search_date": "2026-08-24",
                "query": "状态反馈 调度",
                "candidate_id": candidate,
                "result_count": 3,
                "reviewed_reference_ids": ["CN123"],
                "verified_urls": ["https://example.test/CN123"],
                "coverage_limitations": "公开网页覆盖有限",
            },
            ensure_ascii=False,
        )
        + "\n"
    )


def _final_search_record(
    claim_id: str = "I1",
    limitation_ids: tuple[str, ...] = ("I1-L1",),
    scope: str = "claim_combination",
) -> str:
    record = json.loads(_search_record().strip())
    record.update(
        {
            "claim_id": claim_id,
            "limitation_ids": list(limitation_ids),
            "search_scope": scope,
        }
    )
    return json.dumps(record, ensure_ascii=False) + "\n"


def _write_valid_docx(path: Path, body: str = "有效专利文档正文") -> None:
    content_types = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
        "</Types>"
    )
    document = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{body}</w:t></w:r></w:p></w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("word/document.xml", document)
        archive.writestr("docProps/validation-padding.bin", bytes(range(256)) * 8)


def test_init_case_creates_only_snapshot_and_uses_clean_git_commit(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _write(project / "core.py", "def mechanism():\n    return 1\n")
    subprocess.run(["git", "init", str(project)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(project), "add", "core.py"], check=True)
    subprocess.run(
        [
            "git",
            "-C",
            str(project),
            "-c",
            "user.name=Test",
            "-c",
            "user.email=test@example.com",
            "commit",
            "-m",
            "evidence",
        ],
        check=True,
        capture_output=True,
    )

    case = tmp_path / "patent-case"
    result = init_case_workspace(case, project, "一种测试方法")

    assert result["snapshot"]["snapshot_type"] == "git_commit"
    assert len(result["snapshot"]["snapshot_sha256"]) == 64
    assert result["snapshot"]["git"]["worktree_clean"] is True
    assert not (case / "01-code-evidence-map.md").exists()
    assert validate_case_workspace(case) == []


def test_directory_and_uploaded_archive_snapshots_have_file_hashes(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    _write(project / "core.py", "value = 1\n")
    directory_result = init_case_workspace(tmp_path / "directory-case", project)
    assert directory_result["snapshot"]["snapshot_type"] == "directory_manifest"
    assert len(directory_result["snapshot"]["files"][0]["sha256"]) == 64

    archive = tmp_path / "project.zip"
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("src/core.py", "value = 1\n")
    archive_result = init_case_workspace(tmp_path / "archive-case", archive)
    assert archive_result["snapshot"]["snapshot_type"] == "uploaded_archive"
    assert (
        archive_result["snapshot"]["archive_sha256"]
        == archive_result["snapshot"]["snapshot_sha256"]
    )
    assert archive_result["snapshot"]["files"][0]["path"] == "src/core.py"


def test_stage_transition_is_sequential_and_candidate_confirmation_is_conditional(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    case = tmp_path / "case"
    init_case_workspace(case, project)

    with pytest.raises(ValueError, match="Illegal stage transition"):
        advance_stage(case, "CLAIMS_V1")
    advance_stage(case, "EVIDENCE_MAP")
    _write(
        case / "01-code-evidence-map.md",
        "| 编号 | 证据 | 步骤 | 状态变化 | 效果 | 状态 |\n"
        "|---|---|---|---|---|---|\n"
        "| E1 | core.py:1 | 处理 | A→B | 降低时延 | confirmed |\n",
    )
    advance_stage(case, "INVENTION_CANDIDATES")
    _write(
        case / "02-invention-candidates.md",
        "| 候选 | 问题 | 机制 | 特征 | 效果 | 证据 | 风险 |\n|---|---|---|---|---|---|---|\n"
        "| P1 | a | m | f | e | E1 | r |\n"
        "| P2 | b | m | f | e | E1 | r |\n"
        "| P3 | c | m | f | e | E1 | r |\n",
    )
    advance_stage(case, "FIRST_SEARCH")
    _write(
        case / "03-prior-art-search" / "search-records.jsonl",
        "".join(_search_record(candidate) for candidate in ("P1", "P2", "P3")),
    )
    advance_stage(case, "CANDIDATE_RANKING")
    ranking_path = case / "02-candidate-ranking.json"
    ranking = json.loads(ranking_path.read_text(encoding="utf-8"))
    ranking.update(
        {
            "ranked_candidates": [
                {"candidate_id": "P1", "score": 8},
                {"candidate_id": "P2", "score": 7.9},
            ],
            "selected_candidate_id": "P1",
            "strategic_ambiguity": True,
            "human_confirmation_required": True,
            "selection_reason": "分值接近",
        }
    )
    ranking_path.write_text(json.dumps(ranking, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(ValueError, match="human_confirmation"):
        advance_stage(case, "FEATURE_MATRIX")
    advance_stage(case, "FEATURE_MATRIX", confirmation="用户确认选择 P1")
    assert json.loads(ranking_path.read_text(encoding="utf-8"))["human_confirmation"]


def test_support_map_order_content_ready_and_docx_are_separate_gates(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    case = tmp_path / "case"
    init_case_workspace(case, project)
    advance_stage(case, "EVIDENCE_MAP")
    _write(case / "01-code-evidence-map.md", "| a | b |\n|---|---|\n| E1 | code |\n")
    advance_stage(case, "INVENTION_CANDIDATES")
    _write(
        case / "02-invention-candidates.md",
        "| a | b |\n|---|---|\n| P1 | x |\n| P2 | y |\n| P3 | z |\n",
    )
    advance_stage(case, "FIRST_SEARCH")
    _write(
        case / "03-prior-art-search" / "search-records.jsonl",
        "".join(_search_record(candidate) for candidate in ("P1", "P2", "P3")),
    )
    advance_stage(case, "CANDIDATE_RANKING")
    _write(
        case / "02-candidate-ranking.json",
        json.dumps(
            {
                "ranked_candidates": ["P1", "P2", "P3"],
                "selected_candidate_id": "P1",
                "strategic_ambiguity": False,
                "human_confirmation_required": False,
                "human_confirmation": "",
                "selection_reason": "明显最优",
            }
        ),
    )
    advance_stage(case, "FEATURE_MATRIX")
    _write(case / "04-feature-matrix.md", "| a | b |\n|---|---|\n| F1 | E1 |\n")
    advance_stage(case, "CLAIMS_V1")
    _write(case / "05-claims-v1.md", "# Claims V1\n\n1. 一种处理方法，包括步骤A。\n")
    advance_stage(case, "SPECIFICATION_V1")
    _write(case / "06-specification-v1.md", "# 说明书 V1\n\n实施例执行步骤A并得到技术效果。\n")
    advance_stage(case, "SUPPORT_CANDIDATES")
    assert (case / "07-support-candidates.md").exists()
    assert not (case / "09-claim-support-map.md").exists()
    _write(case / "07-support-candidates.md", "| a | b |\n|---|---|\n| 步骤A | E1 |\n")
    advance_stage(case, "CLAIMS_V2")
    _write(
        case / "08-claims-v2.md",
        "# Claims V2\n\n1. 一种处理方法，其特征在于，包括：\n[I1-L1] 执行步骤A。\n",
    )
    _write(
        case / "08-claims-v2-structure.json",
        json.dumps(
            {
                "independent_claims": [
                    {
                        "claim_id": "I1",
                        "claim_number": 1,
                        "limitation_ids": ["I1-L1"],
                        "distinguishing_limitation_ids": ["I1-L1"],
                    }
                ]
            }
        ),
    )
    advance_stage(case, "CLAIM_SUPPORT_MAP")
    _write(
        case / "09-claim-support-map.md",
        "| 限定 | 工程 | 说明书 | 效果 | 状态 |\n"
        "|---|---|---|---|---|\n"
        "| I1-L1 步骤A | E1 | 段落1 | 降低时延 | supported |\n",
    )
    advance_stage(case, "FINAL_SEARCH")
    _write(case / "10-final-search" / "search-records.jsonl", _search_record())
    with pytest.raises(ValueError, match="Final search"):
        advance_stage(case, "FINAL_AUDIT")
    _write(case / "10-final-search" / "search-records.jsonl", _final_search_record())
    advance_stage(case, "FINAL_AUDIT")
    sections = (
        "新颖性",
        "创造性",
        "专利客体",
        "清楚性与支持性",
        "充分公开",
        "单一性与拆案",
        "修改依据",
        "敏感信息",
    )
    _write(
        case / "11-final-audit.md",
        "# 最终审计\n\n"
        + "\n\n".join(f"## {section}\n\n已完成检查。" for section in sections)
        + "\n",
    )

    with pytest.raises(ValueError, match="Technical content questions"):
        advance_stage(case, "CONTENT_READY_FOR_ATTORNEY_REVIEW")
    advance_stage(case, "CONTENT_READY_FOR_ATTORNEY_REVIEW", close_technical_questions=True)
    status = json.loads((case / "case-status.json").read_text(encoding="utf-8"))
    assert status["filing_context_questions_open"] is True
    assert not (case / "filing-package").exists()

    advance_stage(case, "INDEPENDENT_AUDIT")
    _write(
        case / "filing-package" / "huang-audit" / "independent-audit.md",
        "# 独立审稿\n\n审计完成。\n",
    )
    with pytest.raises(ValueError, match="DOCX render gate"):
        advance_stage(case, "DOCX_PACKAGE_RENDERED")
    for subject in REQUIRED_DOCX_SUBJECTS:
        _write_valid_docx(case / "filing-package" / "docx" / f"{subject}.docx", subject)
    advance_stage(case, "DOCX_PACKAGE_RENDERED")
    assert validate_case_workspace(case) == []


def test_manual_stage_jump_and_filing_ready_are_rejected(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    case = tmp_path / "case"
    init_case_workspace(case, project)
    status_path = case / "case-status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["current_stage"] = "CLAIMS_V2"
    status_path.write_text(json.dumps(status), encoding="utf-8")
    assert any("stage_history" in error for error in validate_case_workspace(case))

    status["current_stage"] = "FILING_READY"
    status_path.write_text(json.dumps(status), encoding="utf-8")
    assert "FILING_READY cannot be set by this tool" in validate_case_workspace(case)


def test_claims_v1_gate_runs_chinese_claim_validator(tmp_path: Path) -> None:
    path = tmp_path / "claims.md"
    _write(
        path,
        "# Claims V1\n\n"
        "1. 一种方法，其特征在于，包括A。\n"
        "3. 根据权利要求4所述的方法，其特征在于，包括B。\n",
    )
    errors = _validate_claims_stage(path)
    assert any("consecutive" in error for error in errors)
    assert any("earlier" in error for error in errors)


def test_claim_structure_rejects_unlabelled_limitation_and_mismatch(tmp_path: Path) -> None:
    claims = tmp_path / "claims-v2.md"
    structure = tmp_path / "claims-v2-structure.json"
    _write(
        claims,
        "1. 一种方法，其特征在于，包括：\n"
        "[I1-L1] 获取数据；\n"
        "对所述数据进行状态预测；\n"
        "[I1-L3] 根据状态预测结果调整资源。\n",
    )
    _write(
        structure,
        json.dumps(
            {
                "independent_claims": [
                    {
                        "claim_id": "I1",
                        "claim_number": 1,
                        "limitation_ids": ["I1-L1", "I1-L2", "I1-L3"],
                        "distinguishing_limitation_ids": ["I1-L2", "I1-L3"],
                    }
                ]
            }
        ),
    )
    errors = _validate_claims_stage(claims, structure)
    assert any("unlabelled substantive limitation" in error for error in errors)
    assert any("unique and consecutive" in error for error in errors)
    assert any("exactly match" in error for error in errors)


def test_docx_gate_rejects_fake_and_empty_ooxml(tmp_path: Path) -> None:
    fake = tmp_path / "fake.docx"
    fake.write_bytes(b"docx")
    assert any("not a valid OOXML ZIP" in error for error in _validate_docx_file(fake))

    empty = tmp_path / "empty.docx"
    _write_valid_docx(empty, "")
    assert any("body is empty" in error for error in _validate_docx_file(empty))

    valid = tmp_path / "valid.docx"
    _write_valid_docx(valid)
    assert _validate_docx_file(valid) == []


def test_support_map_requires_exactly_one_row_per_structured_limitation(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "08-claims-v2-structure.json",
        json.dumps(
            {
                "independent_claims": [
                    {
                        "claim_id": "I1",
                        "claim_number": 1,
                        "limitation_ids": ["I1-L1", "I1-L2"],
                        "distinguishing_limitation_ids": ["I1-L2"],
                    }
                ]
            }
        ),
    )
    _write(
        tmp_path / "09-claim-support-map.md",
        "| 限定 | 工程 | 说明书 | 效果 | 状态 |\n"
        "|---|---|---|---|---|\n"
        "| I1-L1 | E1 | 段落1 | 效果1 | supported |\n"
        "| I1-L1 | E1 | 段落1 | 效果1 | supported |\n",
    )
    errors = _validate_support_map(tmp_path, {})
    assert any("mapped more than once" in error for error in errors)
    assert any("missing independent-claim limitations: I1-L2" in error for error in errors)


def test_final_search_requires_claim_combinations_and_distinguishing_coverage(
    tmp_path: Path,
) -> None:
    _write(
        tmp_path / "08-claims-v2-structure.json",
        json.dumps(
            {
                "independent_claims": [
                    {
                        "claim_id": "I1",
                        "claim_number": 1,
                        "limitation_ids": ["I1-L1", "I1-L2"],
                        "distinguishing_limitation_ids": ["I1-L2"],
                    }
                ]
            }
        ),
    )
    search_dir = tmp_path / "10-final-search"
    search_dir.mkdir()
    _write(
        search_dir / "search-records.jsonl",
        _final_search_record("I1", ("I1-L1",), "distinguishing_limitation"),
    )
    errors = _validate_final_search(tmp_path, {})
    assert any("full combination query" in error for error in errors)
    assert any("distinguishing limitations: I1-L2" in error for error in errors)
