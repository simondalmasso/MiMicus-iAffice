from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CommunicationEdge:
    source: str
    target: str
    value: float
    reason: str


def sparse_edges(agent_ids: list[str], disagreement: float, *, k: int = 2, round_index: int = 0) -> list[CommunicationEdge]:
    if disagreement <= 0.05 or round_index >= 3:
        return []
    edges: list[CommunicationEdge] = []
    for idx, source in enumerate(agent_ids):
        for offset in range(1, min(k, len(agent_ids) - 1) + 1):
            target = agent_ids[(idx + offset) % len(agent_ids)]
            if source < target:
                edges.append(CommunicationEdge(source, target, disagreement / offset, "residual disagreement × complementarity"))
    edges.sort(key=lambda edge: (-edge.value, edge.source, edge.target))
    return edges[: max(0, len(agent_ids) * k // 2)]
