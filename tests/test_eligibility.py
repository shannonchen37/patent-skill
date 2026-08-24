from patent_skill.eligibility import (
    draft_prerequisites,
    utility_model_eligibility,
    validate_inventors,
)


def test_ai_cannot_be_inventor() -> None:
    assert validate_inventors(["ChatGPT"])
    assert validate_inventors(["张三"]) == []


def test_pure_software_rejected_for_utility_model() -> None:
    result = utility_model_eligibility(
        has_physical_product=False, has_shape_or_structure=False, pure_software=True
    )
    assert result["eligible"] is False


def test_normal_draft_requires_search_but_presearch_can_continue() -> None:
    assert draft_prerequisites(
        search_snapshot_id=None,
        feature_novelty_done=False,
        feature_inventive_step_done=False,
        pre_search=False,
    )
    assert (
        draft_prerequisites(
            search_snapshot_id=None,
            feature_novelty_done=False,
            feature_inventive_step_done=False,
            pre_search=True,
        )
        == []
    )
