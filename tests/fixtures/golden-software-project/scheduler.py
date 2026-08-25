from state import NodeState


def select_node(states: dict[str, NodeState]) -> str:
    """Feed current node state back into task allocation."""
    return min(states, key=lambda node_id: states[node_id].load)
