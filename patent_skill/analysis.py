from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ReferenceDisclosure:
    reference_id: str
    disclosed_features: set[str]


def novelty_assessment(
    feature_ids: set[str], references: list[ReferenceDisclosure]
) -> dict[str, object]:
    """Assess disclosure reference by reference; never mosaic references for novelty."""
    rows: list[dict[str, object]] = []
    destroying: list[str] = []
    for reference in references:
        missing = sorted(feature_ids - reference.disclosed_features)
        all_disclosed = not missing
        if all_disclosed:
            destroying.append(reference.reference_id)
        rows.append({
            "reference_id": reference.reference_id,
            "all_features_disclosed": all_disclosed,
            "missing_features": missing,
        })
    return {
        "feature_ids": sorted(feature_ids),
        "references": rows,
        "potentially_novelty_destroying_references": destroying,
        "preliminary_novelty_preserved": not destroying,
        "notice": "Multiple references were not combined for novelty.",
    }


def final_claim_recheck(
    old_features: set[str], new_features: set[str], references: list[ReferenceDisclosure]
) -> dict[str, object]:
    assessment = novelty_assessment(new_features, references)
    removed = sorted(old_features - new_features)
    added = sorted(new_features - old_features)
    flags: list[str] = []
    if removed:
        flags.append("NOVELTY / INVENTIVE-STEP REASSESSMENT REQUIRED")
    if added:
        flags.append("SEARCH UPDATE REQUIRED")
    if assessment["potentially_novelty_destroying_references"]:
        flags.append("POTENTIAL NOVELTY ISSUE INTRODUCED OR REMAINS")
    if not flags:
        flags.append("CURRENT CLAIM SET CONSISTENT WITH LATEST SEARCH ASSESSMENT")
    return {"removed_features": removed, "added_features": added, "flags": flags,
            "novelty": assessment}
