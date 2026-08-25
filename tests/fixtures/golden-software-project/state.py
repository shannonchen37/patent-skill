from dataclasses import dataclass


@dataclass(frozen=True)
class NodeState:
    queued_tasks: int
    active_tasks: int

    @property
    def load(self) -> int:
        return self.queued_tasks + self.active_tasks
