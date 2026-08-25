from patent_skill.models import (
    ClaimSnapshot,
    EngineeringProvenance,
    ProvenanceStatus,
    SearchSnapshot,
)


def test_engineering_provenance_requires_file_backed_evidence() -> None:
    record = EngineeringProvenance("F001", "P001", "feature", ProvenanceStatus.CODE)
    assert record.validate()


def test_unsupported_status_cannot_be_canonical_engineering_provenance() -> None:
    record = EngineeringProvenance("F001", "P001", "feature", ProvenanceStatus.INSUFFICIENT)
    assert record.validate()


def test_claim_and_search_snapshots_are_hashed() -> None:
    claims = ClaimSnapshot("CLAIMS-V1", 1, {"C1": "a claim"}, "SEARCH-1")
    search = SearchSnapshot("SEARCH-1", ["CNIPA"], ["q"], ["D1"])
    assert len(claims.content_hash) == 64
    assert len(search.query_log_hash) == 64
    assert claims.based_on_search_snapshot_id == search.search_snapshot_id
