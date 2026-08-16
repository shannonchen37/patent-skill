from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from .security import detect_sensitive_files, should_ignore


LANGUAGES = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript", ".ts": "TypeScript",
    ".tsx": "TypeScript", ".go": "Go", ".java": "Java", ".c": "C", ".h": "C/C++",
    ".cc": "C++", ".cpp": "C++", ".hpp": "C++", ".rs": "Rust",
}
TEXT_SUFFIXES = set(LANGUAGES) | {".md", ".txt", ".json", ".yaml", ".yml", ".toml"}


def scan_repository(root: Path, max_file_bytes: int = 1_000_000) -> dict[str, Any]:
    root = root.resolve()
    files: list[dict[str, Any]] = []
    languages: Counter[str] = Counter()
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if not path.is_file() or should_ignore(rel):
            continue
        size = path.stat().st_size
        if size > max_file_bytes or path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        language = LANGUAGES.get(path.suffix.lower())
        if language:
            languages[language] += 1
        files.append({"path": rel.as_posix(), "size": size, "language": language})
    return {
        "root": str(root), "files": files, "file_count": len(files),
        "languages": dict(sorted(languages.items())),
        "security_warnings": detect_sensitive_files(root),
    }


def write_manifest(root: Path, output: Path) -> dict[str, Any]:
    manifest = scan_repository(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest
