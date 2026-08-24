from patent_skill.validators import (
    build_engineering_provenance,
    validate_amendment_basis,
    validate_claim_support,
)


def test_engineering_evidence_is_not_specification_support() -> None:
    assert validate_claim_support([{"claim_id": "C1", "feature_id": "F4", "status": "missing"}])


def test_amendment_requires_original_basis() -> None:
    assert validate_amendment_basis(
        [{"potential_amendment": "add F4", "specification_paragraph": None}]
    )


def test_builder_preserves_proposed_enablement_gate() -> None:
    result = build_engineering_provenance(
        [
            {
                "feature_id": "F5",
                "invention_id": "P001",
                "feature": "future option",
                "status": "proposed-but-enabled",
                "evidence": [],
                "inventor_confirmation": True,
                "enablement_review_required": True,
            }
        ]
    )
    assert result[0]["validation_errors"] == []
