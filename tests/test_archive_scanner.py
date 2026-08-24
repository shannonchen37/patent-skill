import zipfile
from pathlib import Path

import pytest

from patent_skill.scanner import scan_archive


def _archive(path: Path, files: dict[str, str]) -> Path:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for name, content in files.items():
            output.writestr(name, content)
    return path


def test_archive_excludes_dotenv_and_records_sensitive_warning(tmp_path: Path) -> None:
    result = scan_archive(_archive(tmp_path / "project.zip", {".env": "TOKEN=secret"}))
    assert result["files"] == []
    assert result["security_warnings"] == [".env"]
    assert result["excluded_files"] == [{"path": ".env", "reason": "sensitive"}]


def test_archive_ignores_node_modules(tmp_path: Path) -> None:
    result = scan_archive(
        _archive(tmp_path / "project.zip", {"node_modules/pkg/index.js": "module.exports = 1"})
    )
    assert result["files"] == []
    assert result["excluded_files"][0]["reason"] == "ignored"


def test_archive_rejects_path_traversal(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unsafe archive path"):
        scan_archive(_archive(tmp_path / "project.zip", {"../escape.py": "pass"}))


def test_archive_rejects_oversized_member(tmp_path: Path) -> None:
    archive = _archive(tmp_path / "project.zip", {"big.py": "x" * 101})
    with pytest.raises(ValueError, match="evidence size limit"):
        scan_archive(archive, max_evidence_file_bytes=100, max_compression_ratio=1000)


def test_archive_rejects_excessive_compression_ratio(tmp_path: Path) -> None:
    archive = _archive(tmp_path / "project.zip", {"bomb.txt": "0" * 10_000})
    with pytest.raises(ValueError, match="compression ratio"):
        scan_archive(archive, max_compression_ratio=2)


def test_archive_detects_languages(tmp_path: Path) -> None:
    archive = _archive(tmp_path / "project.zip", {"src/core.py": "pass", "web/app.ts": ""})
    result = scan_archive(archive)
    assert result["languages"] == {"Python": 1, "TypeScript": 1}
    assert {entry["path"] for entry in result["files"]} == {"src/core.py", "web/app.ts"}
