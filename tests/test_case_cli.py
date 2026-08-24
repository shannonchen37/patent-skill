from pathlib import Path

import pytest

from patent_skill.cli import build_parser, main


def test_cli_exposes_one_canonical_case_namespace() -> None:
    args = build_parser().parse_args(["case", "advance", "case-dir", "EVIDENCE_MAP"])
    assert args.group == "case"
    assert args.case_command == "advance"
    assert not hasattr(args, "close_technical_questions")


def test_old_flat_case_commands_are_not_exposed() -> None:
    with pytest.raises(SystemExit, match="2"):
        build_parser().parse_args(["advance-stage", "case-dir", "EVIDENCE_MAP"])


def test_case_init_status_and_validate_cli(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    project = tmp_path / "project"
    project.mkdir()
    (project / "core.py").write_text("value = 1\n", encoding="utf-8")
    case = tmp_path / "case"
    assert main(["case", "init", str(case), "--project", str(project)]) == 0
    assert main(["case", "status", str(case)]) == 0
    assert main(["case", "validate", str(case)]) == 0
    output = capsys.readouterr().out
    assert "PROJECT_SNAPSHOT" in output
    assert "PASS canonical case validation" in output
