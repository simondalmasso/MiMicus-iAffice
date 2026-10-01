from __future__ import annotations

from datetime import UTC, datetime

import pytest

from mimicus.canonical import canonical_json, sha256_obj, sha256_text
from mimicus.claims.graph import ClaimGraph
from mimicus.claims.models import Claim, Evidence


def test_canonical_is_order_independent() -> None:
    assert canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'
    assert sha256_obj({"a": 1, "b": 2}) == sha256_obj({"b": 2, "a": 1})
    assert len(sha256_text("x")) == 64


def test_claim_evidence_hashes_and_graph() -> None:
    evidence = Evidence(
        origin="fixture://one",
        source_class="fixture",
        trust_authority=0.9,
        observed_at=datetime(2026, 8, 17, tzinfo=UTC),
        snapshot_hash="a" * 64,
        extraction_method="deterministic",
        independence_cluster="origin-a",
        content="42",
    )
    claim1 = Claim(statement="42", domain="test", probability=0.8, evidence_refs=[evidence.evidence_id])
    claim2 = Claim(statement="43", domain="test", probability=0.2)
    assert len(evidence.hash) == len(claim1.hash) == 64
    graph = ClaimGraph()
    graph.add(claim1)
    graph.add(claim2)
    graph.relate(claim1.claim_id, claim2.claim_id, "contradicts")
    assert (claim1.claim_id, claim2.claim_id, "contradicts") in graph.edges
    with pytest.raises(KeyError):
        graph.relate("missing", claim2.claim_id, "x")
