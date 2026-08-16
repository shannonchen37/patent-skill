# Technical Summary

`deque` is abstracted as bounded historical resource-state storage. The moving average is a narrow prediction implementation. The score combines current resource availability, predicted contention, and task demand to select a target compute node.
