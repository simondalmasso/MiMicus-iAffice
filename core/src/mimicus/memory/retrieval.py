from __future__ import annotations

from mimicus.memory.gates import retrieval_gate
from mimicus.memory.models import MemoryItem


def eligible_memories(items: list[MemoryItem], domain: str) -> list[MemoryItem]:
    eligible = [item for item in items if retrieval_gate(item, domain=domain)]
    return sorted(eligible, key=lambda item: (-item.authority, item.memory_id))


def retrieve(items: list[MemoryItem], domain: str) -> list[MemoryItem]:
    return eligible_memories(items, domain)
