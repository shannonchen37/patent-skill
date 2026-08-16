from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import STATE_ORDER, WorkspaceState


FORBIDDEN_STATE = "FILING_READY"
REQUIRED_REVIEW_ARTIFACTS = (
    "drafting/{id}/claims-v2.md",
    "drafting/{id}/specification.md",
    "drafting/{id}/abstract.md",
    "validation/{id}/final-claim-search-recheck.md",
    "validation/{id}/final-claim-eligibility-recheck.md",
    "validation/{id}/final-unity-recheck.md",
    "validation/{id}/disclosure-redaction-review.md",
)


def can_transition(current: WorkspaceState, target: WorkspaceState) -> bool:
    return STATE_ORDER.index(target) == STATE_ORDER.index(current) + 1


def set_state(status_file: Path, target: str) -> dict[str, Any]:
    if target == FORBIDDEN_STATE:
        raise ValueError("FILING_READY cannot be granted automatically")
    status = json.loads(status_file.read_text(encoding="utf-8")) if status_file.exists() else {
        "state": WorkspaceState.DISCOVERY.value,
    }
    current = WorkspaceState(status["state"])
    destination = WorkspaceState(target)
    if current != destination and not can_transition(current, destination):
        raise ValueError(f"Invalid transition: {current.value} -> {destination.value}")
    status["state"] = destination.value
    status_file.parent.mkdir(parents=True, exist_ok=True)
    status_file.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    return status


def validate_workspace(root: Path, invention_id: str = "P001") -> list[str]:
    errors: list[str] = []
    status_file = root / "status.json"
    if not status_file.exists():
        errors.append("Missing status.json")
        return errors
    status = json.loads(status_file.read_text(encoding="utf-8"))
    if status.get("state") == FORBIDDEN_STATE:
        errors.append("FILING_READY cannot be set by this tool")
    if status.get("state") == WorkspaceState.READY_FOR_ATTORNEY_REVIEW.value:
        for pattern in REQUIRED_REVIEW_ARTIFACTS:
            path = root / pattern.format(id=invention_id)
            if not path.exists():
                errors.append(f"Missing review artifact: {path.relative_to(root)}")
    return errors


def validate_redaction(text: str, forbidden: list[str]) -> list[str]:
    return [f"Internal value leaked into public draft: {value}" for value in forbidden if value in text]
