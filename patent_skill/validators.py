from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import EngineeringProvenance, Evidence, ProvenanceStatus
from .workspace import validate_redaction


def build_engineering_provenance(features: list[dict[str, Any]]) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for item in features:
        evidence = [Evidence(**row) for row in item.get("evidence", [])]
        try:
            status = ProvenanceStatus(item["status"])
        except ValueError:
            output.append(
                {
                    **item,
                    "validation_errors": [
                        "Engineering provenance accepts only file-backed code, "
                        "document, or experiment support"
                    ],
                }
            )
            continue
        record = EngineeringProvenance(
            feature_id=item["feature_id"],
            invention_id=item["invention_id"],
            feature=item["feature"],
            status=status,
            evidence=evidence,
        )
        errors = record.validate()
        output.append({**item, "validation_errors": errors})
    return output


def validate_claim_support(records: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for record in records:
        if record.get("status") in {"missing", "weak"}:
            errors.append(
                f"{record.get('claim_id', '?')} / {record.get('feature_id', '?')} "
                f"has {record.get('status')} specification support"
            )
    return errors


def validate_amendment_basis(records: list[dict[str, Any]]) -> list[str]:
    return [
        f"No clear original basis: {record.get('potential_amendment', '?')}"
        for record in records
        if not record.get("specification_paragraph")
    ]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_disclosure_file(draft: Path, forbidden_file: Path) -> list[str]:
    forbidden = load_json(forbidden_file)
    return validate_redaction(draft.read_text(encoding="utf-8"), forbidden)
