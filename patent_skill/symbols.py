from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

from .scanner import LANGUAGES
from .security import should_ignore


PATTERNS = {
    "JavaScript": re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)|^class\s+(\w+)"),
    "TypeScript": re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+(\w+)|^class\s+(\w+)"),
    "Go": re.compile(r"^func\s+(?:\([^)]*\)\s*)?(\w+)"),
    "Java": re.compile(r"^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:class\s+)?(\w+)\s*\("),
    "Rust": re.compile(r"^\s*(?:pub\s+)?fn\s+(\w+)"),
    "C": re.compile(r"^\s*[\w*\s]+\s+(\w+)\s*\([^;]*\)\s*\{"),
    "C++": re.compile(r"^\s*[\w:*&<>\s]+\s+(\w+)\s*\([^;]*\)\s*\{"),
}


def extract_symbols(root: Path) -> list[dict[str, Any]]:
    symbols: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root)
        if not path.is_file() or should_ignore(rel):
            continue
        language = LANGUAGES.get(path.suffix.lower())
        if not language:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if language == "Python":
            symbols.extend(_python_symbols(rel.as_posix(), text))
        else:
            symbols.extend(_fallback_symbols(rel.as_posix(), language, text))
    return symbols


def _python_symbols(file: str, text: str) -> list[dict[str, Any]]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    result: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            result.append({
                "file": file, "language": "Python", "symbol_type": kind,
                "symbol": node.name, "parent": "", "start_line": node.lineno,
                "end_line": getattr(node, "end_lineno", node.lineno),
                "docstring": ast.get_docstring(node) or "",
            })
    return result


def _fallback_symbols(file: str, language: str, text: str) -> list[dict[str, Any]]:
    pattern = PATTERNS.get(language)
    if not pattern:
        return []
    result: list[dict[str, Any]] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        match = pattern.search(line)
        if match:
            name = next(group for group in match.groups() if group)
            result.append({
                "file": file, "language": language, "symbol_type": "symbol",
                "symbol": name, "parent": "", "start_line": line_no,
                "end_line": line_no, "docstring": "",
            })
    return result


def write_symbols(root: Path, output: Path) -> list[dict[str, Any]]:
    data = extract_symbols(root)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return data
