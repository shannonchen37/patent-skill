from __future__ import annotations

AI_ENTITIES = {"chatgpt", "openai", "gpt", "llm", "ai", "人工智能", "agent"}


def validate_inventors(inventors: list[str]) -> list[str]:
    errors: list[str] = []
    for inventor in inventors:
        normalized = inventor.strip().lower()
        if not normalized:
            errors.append("Inventor name must not be empty")
        elif normalized in AI_ENTITIES or any(token in normalized for token in ("chatgpt", "gpt-")):
            errors.append(f"AI/system entity cannot be accepted as an inventor entry: {inventor}")
    return errors


def utility_model_eligibility(
    *, has_physical_product: bool, has_shape_or_structure: bool, pure_software: bool
) -> dict[str, object]:
    eligible = has_physical_product and has_shape_or_structure and not pure_software
    reason = (
        "Qualifying physical product shape or structure identified."
        if eligible
        else "No qualifying physical product shape or structure identified."
    )
    return {"eligible": eligible, "reason": reason}


def draft_prerequisites(
    *,
    search_snapshot_id: str | None,
    feature_novelty_done: bool,
    feature_inventive_step_done: bool,
    pre_search: bool,
) -> list[str]:
    if pre_search:
        return []
    missing: list[str] = []
    if not search_snapshot_id:
        missing.append("documented search snapshot")
    if not feature_novelty_done:
        missing.append("feature-combination novelty assessment")
    if not feature_inventive_step_done:
        missing.append("feature-combination inventive-step assessment")
    return missing
