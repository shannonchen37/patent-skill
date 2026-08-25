from __future__ import annotations

import re

CLAIM_RE = re.compile(r"^\s*(\d+)[\.、]\s*(.+)$")
REFERENCE_RE = re.compile(r"根据权利要求\s*([\d、,，至到或和\-\s]+)\s*所述的?([^，,；;。]+)")
INTERNAL_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
TRACE_LABEL_RE = re.compile(r"\[((?:I|D)\d+-L\d+)\]")


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


def claim_dependencies(text: str) -> dict[int, list[int]]:
    dependencies: dict[int, list[int]] = {}
    for number, claim in parse_claims(INTERNAL_COMMENT_RE.sub("", text)).items():
        match = REFERENCE_RE.search(claim)
        if match:
            dependencies[number] = _reference_numbers(match.group(1))
    return dependencies


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


def validate_no_internal_prose_inside_claim_body(text: str) -> list[str]:
    seen_claim = False
    for line in text.splitlines():
        if CLAIM_RE.match(line):
            seen_claim = True
        elif seen_claim and line.lstrip().startswith(("#", ">", "<!--")):
            return ["Internal Markdown metadata appears after formal claims begin"]
    return []


def render_filing_claims(text: str) -> str:
    blocks = parse_claim_blocks(text)
    if not blocks:
        raise ValueError("No numbered claims found")
    errors = validate_no_internal_prose_inside_claim_body(text)
    if errors:
        raise ValueError("; ".join(errors))

    lines = ["# 权利要求书", ""]
    for number in sorted(blocks):
        parts = []
        for part in blocks[number]:
            clean = TRACE_LABEL_RE.sub("", part).strip()
            if clean.startswith(("#", ">", "<!--")):
                continue
            if clean:
                parts.append(clean)
        if not parts:
            raise ValueError(f"Claim {number} is empty after filing cleanup")
        lines.append(f"{number}. {parts[0]}")
        lines.extend(parts[1:])
        lines.append("")
    result = "\n".join(lines).rstrip() + "\n"
    errors = validate_claims_cn(result)
    if errors:
        raise ValueError("; ".join(errors))
    return result


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
