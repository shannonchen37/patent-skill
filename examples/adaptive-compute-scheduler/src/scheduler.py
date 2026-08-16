from __future__ import annotations

from collections import deque
from dataclasses import dataclass


@dataclass(frozen=True)
class ResourceState:
    compute: float
    memory: float


class LoadPredictor:
    """Predict near-future load from a bounded history window."""

    def __init__(self, window_size: int = 4) -> None:
        self.history: deque[ResourceState] = deque(maxlen=window_size)

    def update(self, state: ResourceState) -> None:
        self.history.append(state)

    def predict(self) -> ResourceState:
        if not self.history:
            return ResourceState(0.0, 0.0)
        count = len(self.history)
        return ResourceState(
            compute=sum(item.compute for item in self.history) / count,
            memory=sum(item.memory for item in self.history) / count,
        )


def match_score(current: ResourceState, predicted: ResourceState, demand: ResourceState) -> float:
    """Score remaining capacity while penalizing predicted contention."""
    current_fit = (1 - current.compute - demand.compute) + (1 - current.memory - demand.memory)
    predicted_penalty = predicted.compute + predicted.memory
    return current_fit - 0.5 * predicted_penalty


def select_node(
    states: dict[str, ResourceState], predictors: dict[str, LoadPredictor], demand: ResourceState
) -> str:
    """Select the node with the highest current-and-predicted resource match."""
    if not states:
        raise ValueError("at least one node is required")
    return max(states, key=lambda node: match_score(states[node], predictors[node].predict(), demand))
