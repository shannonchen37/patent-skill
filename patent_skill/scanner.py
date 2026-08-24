from __future__ import annotations

import hashlib
import json
import stat
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

from .security import detect_sensitive_files, is_sensitive, should_ignore

LANGUAGES = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".java": "Java",
    ".c": "C",
    ".h": "C/C++",
    ".cc": "C++",
    ".cpp": "C++",
    ".hpp": "C++",
    ".rs": "Rust",
}
TEXT_SUFFIXES = set(LANGUAGES) | {".md", ".txt", ".json", ".yaml", ".yml", ".toml"}
DEFAULT_SCAN_LIMITS = {
    "max_member_count": 20_000,
    "max_total_uncompressed_bytes": 500 * 1024 * 1024,
    "max_evidence_file_bytes": 1_000_000,
    "max_compression_ratio": 100,
}


def scan_repository(root: Path, max_file_bytes: int = 1_000_000) -> dict[str, Any]:
    root = root.resolve()
    files: list[dict[str, Any]] = []
    excluded_files: list[dict[str, str]] = []
    languages: Counter[str] = Counter()
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if not path.is_file():
            continue
        if should_ignore(rel):
            excluded_files.append({"path": rel.as_posix(), "reason": "ignored_or_sensitive"})
            continue
        size = path.stat().st_size
        if size > max_file_bytes:
            excluded_files.append({"path": rel.as_posix(), "reason": "oversized"})
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES:
            excluded_files.append({"path": rel.as_posix(), "reason": "unsupported_suffix"})
            continue
        language = LANGUAGES.get(path.suffix.lower())
        if language:
            languages[language] += 1
        files.append({"path": rel.as_posix(), "size": size, "language": language})
    return {
        "root": str(root),
        "files": files,
        "excluded_files": excluded_files,
        "file_count": len(files),
        "languages": dict(sorted(languages.items())),
        "security_warnings": detect_sensitive_files(root),
        "limits": {**DEFAULT_SCAN_LIMITS, "max_evidence_file_bytes": max_file_bytes},
    }


def scan_archive(
    archive_path: Path,
    *,
    max_member_count: int = DEFAULT_SCAN_LIMITS["max_member_count"],
    max_total_uncompressed_bytes: int = DEFAULT_SCAN_LIMITS["max_total_uncompressed_bytes"],
    max_evidence_file_bytes: int = DEFAULT_SCAN_LIMITS["max_evidence_file_bytes"],
    max_compression_ratio: int = DEFAULT_SCAN_LIMITS["max_compression_ratio"],
) -> dict[str, Any]:
    archive_path = archive_path.resolve()
    files: list[dict[str, Any]] = []
    excluded_files: list[dict[str, str]] = []
    security_warnings: list[str] = []
    languages: Counter[str] = Counter()
    limits = {
        "max_member_count": max_member_count,
        "max_total_uncompressed_bytes": max_total_uncompressed_bytes,
        "max_evidence_file_bytes": max_evidence_file_bytes,
        "max_compression_ratio": max_compression_ratio,
    }
    with zipfile.ZipFile(archive_path) as archive:
        members = archive.infolist()
        if len(members) > max_member_count:
            raise ValueError("Archive exceeds the maximum member count")
        total_uncompressed = sum(info.file_size for info in members if not info.is_dir())
        if total_uncompressed > max_total_uncompressed_bytes:
            raise ValueError("Archive exceeds the maximum total uncompressed size")
        for info in sorted(members, key=lambda item: item.filename):
            if info.is_dir():
                continue
            relative = _safe_archive_path(info.filename)
            if info.flag_bits & 0x1:
                raise ValueError(f"Encrypted archive member is not allowed: {relative}")
            mode = info.external_attr >> 16
            if mode and stat.S_ISLNK(mode):
                raise ValueError(f"Archive symlink is not allowed: {relative}")
            if info.file_size > max_evidence_file_bytes:
                raise ValueError(f"Archive member exceeds evidence size limit: {relative}")
            if (
                info.file_size
                and info.file_size / max(info.compress_size, 1) > max_compression_ratio
            ):
                raise ValueError(f"Archive member has excessive compression ratio: {relative}")
            if is_sensitive(relative):
                warning = relative.as_posix()
                security_warnings.append(warning)
                excluded_files.append({"path": warning, "reason": "sensitive"})
                continue
            if should_ignore(relative):
                excluded_files.append({"path": relative.as_posix(), "reason": "ignored"})
                continue
            suffix = relative.suffix.lower()
            if suffix not in TEXT_SUFFIXES:
                excluded_files.append({"path": relative.as_posix(), "reason": "unsupported_suffix"})
                continue
            digest = _hash_archive_member(archive, info, max_evidence_file_bytes)
            language = LANGUAGES.get(suffix)
            if language:
                languages[language] += 1
            files.append(
                {
                    "path": relative.as_posix(),
                    "size": info.file_size,
                    "language": language,
                    "sha256": digest,
                }
            )
    return {
        "root": str(archive_path),
        "files": files,
        "excluded_files": excluded_files,
        "file_count": len(files),
        "languages": dict(sorted(languages.items())),
        "security_warnings": sorted(set(security_warnings)),
        "limits": limits,
    }


def _safe_archive_path(raw_name: str) -> PurePosixPath:
    normalized = raw_name.replace("\\", "/")
    path = PurePosixPath(normalized)
    if path.is_absolute() or ".." in path.parts or not path.parts:
        raise ValueError(f"Unsafe archive path: {raw_name}")
    if path.parts[0].endswith(":"):
        raise ValueError(f"Unsafe archive path: {raw_name}")
    return path


def _hash_archive_member(archive: zipfile.ZipFile, info: zipfile.ZipInfo, max_bytes: int) -> str:
    digest = hashlib.sha256()
    total = 0
    with archive.open(info) as source:
        while chunk := source.read(64 * 1024):
            total += len(chunk)
            if total > max_bytes:
                raise ValueError(f"Archive member expanded beyond limit: {info.filename}")
            digest.update(chunk)
    return digest.hexdigest()


def write_manifest(root: Path, output: Path) -> dict[str, Any]:
    manifest = scan_repository(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest
