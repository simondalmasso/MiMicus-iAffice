from __future__ import annotations

from datetime import UTC, datetime, timedelta

from mimicus.germinal.center import evasion_farming_guard, germinal_demo
from mimicus.germinal.fossils import seed_fossils
from mimicus.memory.gates import cross_agent_gate, promotion_gate, retrieval_gate, write_gate
from mimicus.memory.models import MemoryItem
from mimicus.memory.provenance import independence_count
from mimicus.memory.retrieval import eligible_memories
from mimicus.types import MemoryStatus


def _item(**kwargs: object) -> MemoryItem:
    defaults = {
        "claim_hash": "a" * 64,
        "content": "claim",
        "owner_fingerprint": "owner",
        "domain": "d",
        "origin_clusters": ["origin"],
        "authority": 0.2,
    }
    defaults.update(kwargs)
    return MemoryItem(**defaults)


def test_memory_authority_laundering_and_promotion() -> None:
    parent = write_gate(_item(authority=0.2))
    child = write_gate(_item(authority=0.9, derived_from=[parent.memory_id]), [parent])
    assert child.authority == 0.2
    assert child.status == MemoryStatus.QUARANTINED
    same_origin = child.model_copy(update={"verified_clusters": ["same", "same"]})
    assert independence_count(same_origin) == 1
    assert promotion_gate(same_origin).status == MemoryStatus.QUARANTINED

    verified = write_gate(_item(authority=0.9, deterministic_verification=True))
    promoted = promotion_gate(verified)
    assert promoted.status == MemoryStatus.SHARED_VERIFIED
    assert cross_agent_gate(promoted, "peer")
    assert retrieval_gate(promoted, domain="d", now=datetime(2026, 8, 17, tzinfo=UTC))

    two_sources = child.model_copy(update={"verified_clusters": ["one", "two"]})
    assert promotion_gate(two_sources).status == MemoryStatus.SHARED_VERIFIED


def test_retrieval_expiry_and_owner_private() -> None:
    private = write_gate(_item(deterministic_verification=True))
    assert cross_agent_gate(private, "owner")
    assert not cross_agent_gate(private, "other")
    expired = private.model_copy(update={"expires_at": datetime.now(UTC) - timedelta(days=1)})
    assert not retrieval_gate(expired, domain="d")
    assert eligible_memories([private, expired], "d") == [private]


def test_fossil_corpus_and_germinal_decisions() -> None:
    fossils = seed_fossils()
    assert len(fossils) == 100
    for primitive in {f.primitive for f in fossils}:
        assert sum(f.primitive == primitive for f in fossils) >= 20
    demo = germinal_demo()
    assert demo["rejected_decision"] == "REJECT"
    assert demo["promoted_decision"] == "PROMOTE"
    assert demo["parent_preserved"] is True
    assert demo["relevant_fossils"] >= 20
    assert not evasion_farming_guard([], 1000)
    assert evasion_farming_guard(["truth"], 1)
