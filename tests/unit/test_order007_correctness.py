from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from mimicus.claims.models import Claim
from mimicus.falsifiers.market import FalsifierMarket
from mimicus.falsifiers.spec import FalsifierSpec
from mimicus.orchestration.engine import MiMicusEngine, RunRequest
from mimicus.types import ClaimStatus


def _spec(spec_id: str, primitive: str, *, eig: float, tolerance: float | None = None) -> FalsifierSpec:
    params: dict[str, object] = {}
    if tolerance is not None:
        params["relative_tolerance"] = tolerance
    return FalsifierSpec(
        id=spec_id,
        version="7.0",
        domain="test",
        trigger="verify structured evidence against the sealed claim",
        primitive=primitive,  # type: ignore[arg-type]
        params=params,
        oracle_kind="deterministic",
        expected_information_gain=eig,
        estimated_cost=0.0,
        estimated_latency=1.0,
        provenance="ORDER-007-test",
    )


def test_claim_identity_survives_challenge_revision() -> None:
    claim = Claim(
        statement="Revenue equals 1200 units.",
        domain="finance",
        probability=0.72,
        claim_type="numeric",
        evidence_refs=["a" * 64],
        as_of=datetime(2026, 8, 18, tzinfo=UTC),
    )
    identity = claim.hash
    revision = claim.revision_hash
    challenged = claim.model_copy(update={"probability": 0.31, "status": ClaimStatus.INCONCLUSIVE})
    assert challenged.hash == identity
    assert challenged.identity_hash == identity
    assert challenged.revision_hash != revision


def test_claim_market_applies_novelty_and_probability_can_reorder() -> None:
    numeric = _spec("N1", "numeric_invariant", eig=0.9, tolerance=0.05)
    numeric_duplicate = _spec("N2", "numeric_invariant", eig=0.91, tolerance=0.051)
    freshness = _spec("T1", "freshness", eig=0.8)
    claims = [
        Claim(statement="numeric", domain="test", probability=0.51, claim_type="numeric"),
        Claim(statement="temporal", domain="test", probability=0.95, claim_type="temporal"),
    ]
    evidence = {"price": 10, "users": 10, "claimed": 100, "evidence_date": "2026-08-17", "as_of": "2026-08-18"}
    selected, candidates = FalsifierMarket().select_for_claims([numeric, numeric_duplicate, freshness], claims, evidence=evidence, budget_usd=1.0, max_tests=3)
    numeric_selected = {row.spec_hash for row in selected if row.spec_hash in {numeric.hash, numeric_duplicate.hash}}
    assert len(numeric_selected) == 1
    assert {row.spec_hash for row in candidates} >= {numeric.hash, numeric_duplicate.hash, freshness.hash}
    assert all("novelty=" in row.selection_reason for row in selected)

    flipped_claims = [
        claims[0].model_copy(update={"probability": 0.99}),
        claims[1].model_copy(update={"probability": 0.52}),
    ]
    selected_flipped, _ = FalsifierMarket().select_for_claims([numeric, freshness], flipped_claims, evidence=evidence, budget_usd=1.0, max_tests=2)
    assert selected and selected_flipped
    assert selected[0].target_claim_hash != selected_flipped[0].target_claim_hash


def test_normal_runtime_cannot_downgrade_to_legacy(tmp_path) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValidationError):
        RunRequest(task="x", source_mode="runtime", core_semantics=False)
    with pytest.raises(ValidationError):
        RunRequest(task="x", source_mode="runtime", fixture={"price": 1})

    engine = MiMicusEngine(f"sqlite:///{tmp_path / 'core-lock.db'}")
    result = engine.run(RunRequest(task="Assess the input.", source_mode="runtime"))
    assert result.threat_profile
    assert result.swarm_decision
    assert result.evidence_provenance["source_mode"] == "runtime"
