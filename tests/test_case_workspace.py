import json
import subprocess
from pathlib import Path

import pytest

from patent_skill.case_workspace import init_case_workspace, validate_case_workspace


def test_init_case_creates_canonical_structure_and_snapshot(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "core.py").write_text("def mechanism():\n    return 1\n", encoding="utf-8")
    subprocess.run(["git", "init", str(project)], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(project), "add", "core.py"], check=True)
    subprocess.run(
        [
            "git", "-C", str(project), "-c", "user.name=Test", "-c",
            "user.email=test@example.com", "commit", "-m", "evidence",
        ],
        check=True,
        capture_output=True,
    )

    case = tmp_path / "patent-case"
    result = init_case_workspace(case, project, "一种测试方法")

    assert (case / "00-project-snapshot" / "snapshot-manifest.json").exists()
    assert (case / "07-claim-support-map.md").exists()
    assert (case / "03-prior-art-search" / "yjmm10").is_dir()
    assert (case / "filing-package" / "huang-audit").is_dir()
    status = json.loads((case / "case-status.json").read_text(encoding="utf-8"))
    assert status["canonical_source"] == "patent-skill"
    assert status["current_gate"] == "SNAPSHOT_CONFIRMATION"
    assert result["snapshot"]["git"]["worktree_clean"] is True
    file_record = result["snapshot"]["files"][0]
    assert len(file_record["sha256"]) == 64
    assert validate_case_workspace(case) == []


def test_init_case_refuses_to_overwrite_existing_case(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    case = tmp_path / "patent-case"
    init_case_workspace(case, project)
    with pytest.raises(ValueError, match="already exists"):
        init_case_workspace(case, project)


def test_ready_for_attorney_review_requires_material_closure_and_docx(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    case = tmp_path / "patent-case"
    init_case_workspace(case, project)
    status_path = case / "case-status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    status["current_stage"] = "READY_FOR_ATTORNEY_REVIEW"
    status_path.write_text(json.dumps(status), encoding="utf-8")

    errors = validate_case_workspace(case)
    assert "Material questions remain open" in errors
    assert any("权利要求书" in error for error in errors)
