from __future__ import annotations

from mimicus.memory.models import MemoryItem


def inherited_authority(parents: list[MemoryItem], proposed_authority: float) -> float:
    if not parents:
        return min(1.0, max(0.0, proposed_authority))
    return min(proposed_authority, *(parent.authority for parent in parents))


def independence_count(item: MemoryItem) -> int:
    return len(set(item.verified_clusters))
