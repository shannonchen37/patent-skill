from src.scheduler import LoadPredictor, ResourceState, select_node


def test_selects_node_with_better_predicted_state() -> None:
    state = ResourceState(0.3, 0.3)
    predictors = {"rising": LoadPredictor(), "stable": LoadPredictor()}
    predictors["rising"].update(ResourceState(0.9, 0.9))
    predictors["stable"].update(ResourceState(0.2, 0.2))
    assert select_node({"rising": state, "stable": state}, predictors, ResourceState(0.1, 0.1)) == "stable"
