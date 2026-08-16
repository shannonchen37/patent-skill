from patent_skill.analysis import ReferenceDisclosure, final_claim_recheck, novelty_assessment


def test_novelty_does_not_mosaic_references() -> None:
    result = novelty_assessment(
        {"F1", "F2", "F3"},
        [ReferenceDisclosure("D1", {"F1", "F2"}), ReferenceDisclosure("D2", {"F3"})],
    )
    assert result["preliminary_novelty_preserved"] is True
    assert result["potentially_novelty_destroying_references"] == []


def test_final_claim_recheck_catches_removed_feature() -> None:
    result = final_claim_recheck(
        {"F1", "F2", "F3"}, {"F1", "F2"}, [ReferenceDisclosure("D1", {"F1", "F2"})]
    )
    assert "NOVELTY / INVENTIVE-STEP REASSESSMENT REQUIRED" in result["flags"]
    assert "POTENTIAL NOVELTY ISSUE INTRODUCED OR REMAINS" in result["flags"]
