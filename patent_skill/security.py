from __future__ import annotations

import fnmatch
from pathlib import Path


BLOCKED_NAMES = {".env", "id_rsa", "id_ed25519", "credentials.json"}
BLOCKED_PATTERNS = ("*.pem", "*.key", "secrets.*", "*token*", "*password*")
IGNORED_DIRS = {
    ".git", ".idea", ".vscode", ".venv", "venv", "node_modules", "vendor",
    "dist", "build", "target", "__pycache__", "coverage", ".cache", "patent-workspace",
}


def is_sensitive(path: Path) -> bool:
    name = path.name.lower()
    return name in BLOCKED_NAMES or any(fnmatch.fnmatch(name, p) for p in BLOCKED_PATTERNS)


def should_ignore(path: Path) -> bool:
    return any(part in IGNORED_DIRS for part in path.parts) or is_sensitive(path)


def detect_sensitive_files(root: Path) -> list[str]:
    found: list[str] = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if any(part in IGNORED_DIRS for part in relative.parts[:-1]):
            continue
        if path.is_file() and is_sensitive(path):
            found.append(relative.as_posix())
    return sorted(found)
