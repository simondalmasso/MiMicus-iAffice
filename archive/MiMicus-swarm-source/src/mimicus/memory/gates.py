from __future__ import annotations

from datetime import UTC, datetime

from mimicus.memory.models import MemoryItem
from mimicus.memory.provenance import independence_count, inherited_authority
from mimicus.types import MemoryStatus


def write_gate(item: MemoryItem, parents: list[MemoryItem] | None = None) -> MemoryItem:
    authority = inherited_authority(parents or [], item.authority)
    status = MemoryStatus.PRIVATE_VERIFIED if item.deterministic_verification else MemoryStatus.QUARANTINED
    return item.model_copy(update={"authority": authority, "status": status})


def retrieval_gate(item: MemoryItem, *, domain: str, now: datetime | None = None) -> bool:
    current = now or datetime.now(UTC)
    if item.expires_at is not None and item.expires_at < current:
        return False
    return item.domain == domain and item.status in {MemoryStatus.PRIVATE_VERIFIED, MemoryStatus.SHARED_VERIFIED}


def promotion_gate(item: MemoryItem) -> MemoryItem:
    promotable = item.deterministic_verification or independence_count(item) >= 2
    if not promotable or item.status in {MemoryStatus.REJECTED, MemoryStatus.EXPIRED}:
        return item.model_copy(update={"status": MemoryStatus.QUARANTINED})
    return item.model_copy(update={"status": MemoryStatus.SHARED_VERIFIED})


def cross_agent_gate(item: MemoryItem, target_fingerprint: str) -> bool:
    if item.owner_fingerprint == target_fingerprint and item.status == MemoryStatus.PRIVATE_VERIFIED:
        return True
    return item.status == MemoryStatus.SHARED_VERIFIED
