from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Attribution:
    member: str
    accuracy_delta: float
    cost_delta: float
    utility_delta: float


def removal_attribution(members: list[str], member_correctness: dict[str, float], member_cost: dict[str, float]) -> list[Attribution]:
    baseline_accuracy = sum(member_correctness.get(member, 0.0) for member in members) / max(1, len(members))
    baseline_cost = sum(member_cost.get(member, 0.0) for member in members)
    rows: list[Attribution] = []
    for member in members:
        remaining = [value for name, value in member_correctness.items() if name in members and name != member]
        without_accuracy = sum(remaining) / max(1, len(remaining))
        without_cost = baseline_cost - member_cost.get(member, 0.0)
        accuracy_delta = baseline_accuracy - without_accuracy
        cost_delta = baseline_cost - without_cost
        rows.append(Attribution(member, accuracy_delta, cost_delta, accuracy_delta - 0.01 * cost_delta))
    return rows
