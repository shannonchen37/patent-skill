from pathlib import Path

from patent_skill.scanner import scan_repository


def test_scan_repository_detects_language_and_ignores_build(tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.py").write_text("def run():\n    pass\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "bad.js").write_text("function leaked() {}")
    manifest = scan_repository(tmp_path)
    assert manifest["languages"] == {"Python": 1}
    assert [item["path"] for item in manifest["files"]] == ["src/main.py"]


def test_scan_skips_binary_and_large_file(tmp_path: Path) -> None:
    (tmp_path / "data.bin").write_bytes(b"\x00" * 20)
    (tmp_path / "huge.md").write_text("x" * 30)
    assert scan_repository(tmp_path, max_file_bytes=10)["file_count"] == 0
