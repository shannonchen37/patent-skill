# Design

The scheduler maintains a bounded resource-state history per node. It predicts near-future compute and memory load, combines predicted contention with current capacity and task demand, and selects the highest-scoring node. The moving average and weight are narrow demo implementations, not the broad concept by themselves.
