import json
from pathlib import Path

import pytest

from patent_skill.models import WorkspaceState
from patent_skill.workspace import can_transition, set_state, validate_redaction, validate_workspace


def test_corrected_state_order() -> None:
    assert can_transition(WorkspaceState.INVENTOR_REVIEW, WorkspaceState.CLAIM_SKELETON)
    assert can_transition(WorkspaceState.CLAIM_SKELETON, WorkspaceState.PRE_SEARCH)
    assert not can_transition(WorkspaceState.SEARCHED, WorkspaceState.CLAIM_SKELETON)


def test_filing_ready_is_forbidden(tmp_path: Path) -> None:
    status = tmp_path / "status.json"
    status.write_text('{"state":"DISCOVERY"}')
    with pytest.raises(ValueError, match="FILING_READY"):
        set_state(status, "FILING_READY")


def test_ready_for_review_requires_final_eligibility_and_unity(tmp_path: Path) -> None:
    (tmp_path / "status.json").write_text(json.dumps({"state": "READY_FOR_ATTORNEY_REVIEW"}))
    errors = validate_workspace(tmp_path)
    assert any("final-claim-eligibility-recheck.md" in error for error in errors)
    assert any("final-unity-recheck.md" in error for error in errors)


def test_internal_evidence_redaction() -> None:
    errors = validate_redaction("draft mentions src/internal/customer_router.py", ["src/internal/customer_router.py"])
    assert errors
