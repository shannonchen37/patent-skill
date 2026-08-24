from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class ProvenanceStatus(StrEnum):
    CODE = "code-supported"
    DOCUMENT = "document-supported"
    EXPERIMENT = "experiment-supported"
    DEVELOPER_CONFIRMED = "developer-confirmed"
    PROPOSED = "proposed-but-enabled"
    INSUFFICIENT = "insufficiently-supported"
    CONTRADICTED = "contradicted"


class WorkspaceState(StrEnum):
    DISCOVERY = "DISCOVERY"
    INVENTOR_REVIEW = "INVENTOR_REVIEW"
    CLAIM_SKELETON = "CLAIM_SKELETON"
    PRE_SEARCH = "PRE_SEARCH"
    SEARCHED = "SEARCHED"
    CLAIM_STRATEGY = "CLAIM_STRATEGY"
    CLAIMS_V1 = "CLAIMS_V1"
    DRAFT = "DRAFT"
    CLAIMS_V2 = "CLAIMS_V2"
    PRE_FILING_REVIEW = "PRE_FILING_REVIEW"
    READY_FOR_ATTORNEY_REVIEW = "READY_FOR_ATTORNEY_REVIEW"


STATE_ORDER = list(WorkspaceState)


@dataclass(slots=True)
class Evidence:
    type: str
    path: str
    explanation: str
    symbol: str = ""
    start_line: int = 0
    end_line: int = 0
    classification: str = "internal-only"


@dataclass(slots=True)
class EngineeringProvenance:
    feature_id: str
    invention_id: str
    feature: str
    status: ProvenanceStatus
    evidence: list[Evidence] = field(default_factory=list)
    inventor_confirmation: bool = False
    enablement_review_required: bool = False

    def validate(self) -> list[str]:
        errors: list[str] = []
        if self.status is ProvenanceStatus.DEVELOPER_CONFIRMED and not self.inventor_confirmation:
            errors.append("developer-confirmed requires inventor_confirmation=true")
        if self.status is ProvenanceStatus.PROPOSED and not self.enablement_review_required:
            errors.append("proposed-but-enabled requires enablement_review_required=true")
        return errors


@dataclass(slots=True)
class ClaimSnapshot:
    claim_set_id: str
    version: int
    claims: dict[str, str]
    based_on_search_snapshot_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    content_hash: str = ""

    def __post_init__(self) -> None:
        if not self.content_hash:
            payload = json.dumps(self.claims, ensure_ascii=False, sort_keys=True)
            self.content_hash = hashlib.sha256(payload.encode()).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SearchSnapshot:
    search_snapshot_id: str
    databases: list[str]
    queries: list[str]
    reference_ids: list[str]
    searched_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    query_log_hash: str = ""
    reference_set_hash: str = ""

    def __post_init__(self) -> None:
        if not self.query_log_hash:
            self.query_log_hash = _hash(self.queries)
        if not self.reference_set_hash:
            self.reference_set_hash = _hash(sorted(self.reference_ids))


def _hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode()
    ).hexdigest()
