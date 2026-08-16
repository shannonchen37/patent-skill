from pathlib import Path

from patent_skill.scanner import scan_repository
from patent_skill.security import detect_sensitive_files


def test_secret_is_reported_but_not_scanned(tmp_path: Path) -> None:
    (tmp_path / ".env").write_text("SECRET=do-not-print")
    manifest = scan_repository(tmp_path)
    assert manifest["files"] == []
    assert manifest["security_warnings"] == [".env"]
    assert detect_sensitive_files(tmp_path) == [".env"]
