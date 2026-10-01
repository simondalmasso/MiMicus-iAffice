from __future__ import annotations


def topology_for_size(size: int, complexity: float) -> str:
    if size <= 1:
        return "solo"
    if size == 2:
        return "paired"
    if complexity >= 0.7:
        return "sparse-star"
    return "sparse-chain"
