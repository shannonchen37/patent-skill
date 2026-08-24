from __future__ import annotations

import re

CLAIM_RE = re.compile(r"^\s*(\d+)[\.、]\s*(.+)$")
REFERENCE_RE = re.compile(r"根据权利要求\s*([\d、,，至到或和\-\s]+)\s*所述的?([^，,；;。]+)")
INTERNAL_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def parse_claim_blocks(text: str) -> dict[int, list[str]]:
    claims: dict[int, list[str]] = {}
    current: int | None = None
    for line in text.splitlines():
        match = CLAIM_RE.match(line)
        if match:
            current = int(match.group(1))
            claims[current] = [match.group(2).strip()]
        elif current is not None and line.strip():
            claims[current].append(line.strip())
    return claims


def parse_claims(text: str) -> dict[int, str]:
    return {number: "".join(parts) for number, parts in parse_claim_blocks(text).items()}


def independent_claim_numbers(text: str) -> set[int]:
    return {
        number
        for number, claim in parse_claims(INTERNAL_COMMENT_RE.sub("", text)).items()
        if not REFERENCE_RE.search(claim)
    }


def validate_claims_cn(text: str) -> list[str]:
    text = INTERNAL_COMMENT_RE.sub("", text)
    claims = parse_claims(text)
    errors: list[str] = []
    if not claims:
        return ["No numbered claims found"]
    if sorted(claims) != list(range(1, max(claims) + 1)):
        errors.append("Claims must use consecutive Arabic numbering")
    multiple_dependent: set[int] = set()
    for number, claim in claims.items():
        match = REFERENCE_RE.search(claim)
        if match:
            refs = _reference_numbers(match.group(1))
            if any(ref >= number for ref in refs):
                errors.append(f"Claim {number} must reference only earlier claims")
            is_multiple = len(refs) > 1
            if is_multiple:
                multiple_dependent.add(number)
                if "或" not in match.group(1) and "任一" not in match.group(1):
                    errors.append(f"Claim {number} multiple dependency must be alternative")
                if any(ref in multiple_dependent for ref in refs):
                    errors.append(f"Claim {number} must not depend on a multiple dependent claim")
        if not claim.rstrip().endswith("。"):
            errors.append(f"Claim {number} should end with a full stop")
    return errors


def _reference_numbers(raw: str) -> list[int]:
    numbers = [int(value) for value in re.findall(r"\d+", raw)]
    if ("至" in raw or "到" in raw or "-" in raw) and len(numbers) == 2:
        return list(range(numbers[0], numbers[1] + 1))
    return numbers


def validate_abstract_cn(text: str) -> list[str]:
    errors: list[str] = []
    compact = "".join(line.strip() for line in text.splitlines() if not line.startswith("#"))
    if len(compact) > 300:
        errors.append(f"Abstract exceeds 300 Chinese characters/punctuation: {len(compact)}")
    promotion = ("领先", "最佳", "革命性", "世界第一", "卓越")
    if any(word in compact for word in promotion):
        errors.append("Abstract contains possible promotional language")
    if not compact:
        errors.append("Abstract is empty")
    return errors


def validate_background_assertions(records: list[dict[str, str]]) -> list[str]:
    return [
        f"Background assertion {index} is model-inferred and cannot enter the final draft"
        for index, record in enumerate(records, 1)
        if record.get("status") == "model-inferred"
    ]
