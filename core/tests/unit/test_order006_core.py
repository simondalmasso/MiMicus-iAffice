from __future__ import annotations

import asyncio
from datetime import UTC, datetime

from mimicus.agents.auditions import CANARY_BANK, audition
from mimicus.claims.models import Claim
from mimicus.coalition.threat_profile import profile_task
from mimicus.falsifiers.builtins import builtin_specs
from mimicus.falsifiers.market import FalsifierMarket
from mimicus.falsifiers.spec import FalsifierExecution
from mimicus.orchestration.synthesis import synthesize_swarm
from mimicus.providers.base import AuditionRequest
from mimicus.providers.scripted import ScriptedProvider
from mimicus.types import Verdict


def test_real_provider_microaudition_is_scored_not_canned() -> None:
    request = AuditionRequest(
        fingerprint="a" * 64,
        domain="finance",
        phenotype="numeric-1",
        capability="numeric",
        test_family="numeric_canary",
        category="parameter_trap",
        prompt=CANARY_BANK["parameter_trap"][0],
        sealed_context_id="sealed",
    )
    good = ScriptedProvider()
    good_response = asyncio.run(good.audition_async(request))
    good_score = audition(
        request.fingerprint,
        request.domain,
        request.category,
        good_response.answer,
        capability=request.capability,
        test_family=request.test_family,
        supported=good_response.supported,
    )
    bad = ScriptedProvider(audition_competence={"numeric-1": frozenset()})
    bad_response = asyncio.run(bad.audition_async(request))
    bad_score = audition(
        request.fingerprint,
        request.domain,
        request.category,
        bad_response.answer,
        capability=request.capability,
        test_family=request.test_family,
        supported=bad_response.supported,
    )
    assert good.audition_calls == 1 and bad.audition_calls == 1
    assert good_score.passed is True
    assert bad_score.passed is False
    assert bad_response.answer != CANARY_BANK["parameter_trap"][1]


def test_claim_aware_market_routes_different_claim_types_to_different_tests() -> None:
    specs = builtin_specs("research")
    numeric = Claim(statement="numeric candidate", domain="research", probability=0.52, claim_type="numeric")
    temporal = Claim(statement="temporal candidate", domain="research", probability=0.86, claim_type="temporal")
    evidence = {
        "price": 10,
        "users": 10,
        "claimed": 1200,
        "evidence_date": "2026-08-17T00:00:00+00:00",
        "as_of": "2026-08-18T00:00:00+00:00",
    }
    selected, all_bids = FalsifierMarket().select_for_claims(
        [specs["F1"], specs["F2"]],
        [numeric, temporal],
        evidence=evidence,
        budget_usd=1.0,
        max_tests=4,
    )
    by_claim = {claim.hash: {row.spec_hash for row in selected if row.target_claim_hash == claim.hash} for claim in (numeric, temporal)}
    assert specs["F1"].hash in by_claim[numeric.hash]
    assert specs["F2"].hash not in by_claim[numeric.hash]
    assert specs["F2"].hash in by_claim[temporal.hash]
    assert all(row.selection_reason.startswith("claim-aware") for row in all_bids)


def test_swarm_synthesis_materially_uses_claims_and_falsifiers() -> None:
    a = Claim(statement="candidate A", domain="test", probability=0.82, claim_type="factual")
    b = Claim(statement="candidate B", domain="test", probability=0.55, claim_type="factual")
    pass_execution = FalsifierExecution(
        spec_hash="a" * 64,
        verdict=Verdict.PASS,
        execution_snapshot_hash="b" * 64,
        target_claim_hashes=(a.hash,),
        selection_reason="test",
    )
    supported = synthesize_swarm([("fp-a", a, 0.8), ("fp-b", b, 0.4)], [pass_execution], [], budget={}, coverage_complete=True)
    fail_execution = pass_execution.model_copy(update={"verdict": Verdict.FAIL, "execution_snapshot_hash": "c" * 64})
    falsified = synthesize_swarm([("fp-a", a, 0.8), ("fp-b", b, 0.4)], [fail_execution], [], budget={}, coverage_complete=True)
    assert supported.candidate_answer == "candidate A"
    assert supported.epistemic_status in {"SUPPORTED", "INCONCLUSIVE"}
    assert falsified.epistemic_status == "FALSIFIED"
    changed_claim = b.model_copy(update={"probability": 0.99})
    changed = synthesize_swarm([("fp-a", a, 0.2), ("fp-b", changed_claim, 0.95)], [], [], budget={}, coverage_complete=False)
    assert changed.candidate_answer == "candidate B"


def test_structural_threat_profile_is_wording_invariant() -> None:
    facts = {"price": 10, "users": 100, "claimed": 1000, "price_period": "monthly"}
    kwargs = {
        "evidence_facts": facts,
        "available_capabilities": ("numeric", "freshness", "source", "independence", "entailment", "counterexample", "synthesize"),
        "budget_usd": 0.0,
        "max_concurrency": 4,
    }
    left = profile_task("Assess this bundle.", "finance", **kwargs)
    right = profile_task("Please evaluate the supplied material.", "finance", **kwargs)
    assert left.required_capabilities == right.required_capabilities == ("numeric",)
    assert left.threats == right.threats == ("numeric_inconsistency",)
    assert any(row["source"] == "evidence_schema" for row in left.signal_provenance)
    assert left.uncertainty == right.uncertainty


def test_verification_submission_timestamp_is_not_authority_multiplier() -> None:
    from mimicus.verification.models import VerificationSubmission

    base = dict(
        run_id="run-1",
        claim_hash="a" * 64,
        verified_status="SUPPORTED",
        authority_class="deterministic_oracle",
        verifier_id="oracle:one",
        source_independence_cluster="registry:one",
    )
    first = VerificationSubmission(observed_at=datetime(2026, 8, 18, 10, tzinfo=UTC), **base)
    repeat = VerificationSubmission(observed_at=datetime(2026, 8, 18, 11, tzinfo=UTC), evidence_hashes=("b" * 64,), **base)
    assert first.origin_key_hash == repeat.origin_key_hash
