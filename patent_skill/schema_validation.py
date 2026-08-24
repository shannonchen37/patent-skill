from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

PACKAGE_SCHEMA_DIR = Path(__file__).resolve().parent / "schemas"
REPOSITORY_SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"


def validate_schema(instance: Any, schema_name: str) -> list[str]:
    package_path = PACKAGE_SCHEMA_DIR / schema_name
    schema_path = package_path if package_path.exists() else REPOSITORY_SCHEMA_DIR / schema_name
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(instance), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.absolute_path) or "$"
        errors.append(f"{schema_name} {location}: {error.message}")
    return errors
