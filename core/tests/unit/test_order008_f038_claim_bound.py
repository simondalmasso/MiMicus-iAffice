from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from mimicus.canonical import sha256_obj
from mimicus.claims.models import (
    Claim,
    CounterexampleAssertion,
    EntailmentAssertion,
    NumericAssertion,
    SourceIndependenceAssertion,
    TemporalAssertion,
)
from mimicus.falsifiers.builtins import builtin_specs
from mimicus.falsifiers.primitives import execute_claim_bound
from mimicus.types import Verdict


def _claim(statement: str, assertion: Any, projection_hash: str) -> Claim:
    return Claim(
        statement=statement,
        domain="audit",
        probability=0.8,
        claim_type="other",
        assertion=assertion,
        evidence_refs=[projection_hash],
    )


def _assert_divergent_binding(
    *,
    spec_key: str,
    context: dict[str, Any],
    passing_assertion: Any,
    failing_assertion: Any,
) -> None:
    projection_hash = sha256_obj({"order008": spec_key, "evidence": context})
    passing_claim = _claim(f"{spec_key} passing target", passing_assertion, projection_hash)
    failing_claim = _claim(f"{spec_key} failing target", failing_assertion, projection_hash)

    passed = execute_claim_bound(
        builtin_specs("audit")[spec_key],
        passing_claim,
        context,
        evidence_projection_hashes=(projection_hash,),
        selection_reason=f"ORDER-008 {spec_key} claim-bound kill",
    )
    failed = execute_claim_bound(
        builtin_specs("audit")[spec_key],
        failing_claim,
        context,
        evidence_projection_hashes=(projection_hash,),
        selection_reason=f"ORDER-008 {spec_key} claim-bound kill",
    )

    assert passed.verdict == Verdict.PASS
    assert failed.verdict == Verdict.FAIL
    assert passed.target_claim_hashes == (passing_claim.identity_hash,)
    assert failed.target_claim_hashes == (failing_claim.identity_hash,)
    assert passed.target_claim_hashes != failed.target_claim_hashes
    assert passed.tested_assertion_hash == passing_claim.assertion_hash
    assert failed.tested_assertion_hash == failing_claim.assertion_hash
    assert passed.tested_assertion_hash != failed.tested_assertion_hash
    assert passed.execution_snapshot_hash != failed.execution_snapshot_hash
    assert passed.evidence_projection_hashes == failed.evidence_projection_hashes == (projection_hash,)
    assert passed.evidence["target_claim_identity_hash"] == passing_claim.identity_hash
    assert failed.evidence["target_claim_identity_hash"] == failing_claim.identity_hash


def test_f038_f2_freshness_is_bound_to_target_temporal_assertion() -> None:
    _assert_divergent_binding(
        spec_key="F2",
        context={"evidence_date": "2026-08-10T00:00:00+00:00"},
        passing_assertion=TemporalAssertion(as_of=datetime(2026, 8, 17, tzinfo=UTC), max_age_days=30),
        failing_assertion=TemporalAssertion(as_of=datetime(2026, 10, 1, tzinfo=UTC), max_age_days=30),
    )


def test_f038_f3_independence_is_bound_to_target_requirement() -> None:
    _assert_divergent_binding(
        spec_key="F3",
        context={"clusters": ["a", "b", "c"], "texts": ["alpha", "beta", "gamma"]},
        passing_assertion=SourceIndependenceAssertion(required_independent=2),
        failing_assertion=SourceIndependenceAssertion(required_independent=4),
    )


def test_f038_f4_entailment_is_bound_to_target_figure() -> None:
    _assert_divergent_binding(
        spec_key="F4",
        context={"evidence_spans": [{"span_id": "s1", "supported_figures": ["42"], "material_support": True}]},
        passing_assertion=EntailmentAssertion(claim_figure="42"),
        failing_assertion=EntailmentAssertion(claim_figure="99"),
    )


def test_f038_f5_counterexample_is_bound_to_target_absence_key() -> None:
    _assert_divergent_binding(
        spec_key="F5",
        context={"registry": {"blocked": "counterexample"}, "registry_snapshot_hash": "a" * 64},
        passing_assertion=CounterexampleAssertion(absence_key="free"),
        failing_assertion=CounterexampleAssertion(absence_key="blocked"),
    )


@pytest.mark.parametrize(
    ("spec_key", "context"),
    [
        ("F2", {"evidence_date": "2026-08-10T00:00:00+00:00"}),
        ("F3", {"clusters": ["a", "b"], "texts": ["alpha", "beta"]}),
        ("F4", {"evidence_spans": [{"span_id": "s", "supported_figures": ["42"], "material_support": True}]}),
        ("F5", {"registry": {}, "registry_snapshot_hash": "b" * 64}),
    ],
)
def test_f038_f2_f5_missing_or_wrong_typed_assertion_fails_closed(spec_key: str, context: dict[str, Any]) -> None:
    projection_hash = sha256_obj({"order008": "fail-closed", "spec": spec_key})
    spec = builtin_specs("audit")[spec_key]
    for assertion in (None, NumericAssertion(asserted_value=1.0)):
        claim = _claim(f"{spec_key} incompatible target", assertion, projection_hash)
        execution = execute_claim_bound(
            spec,
            claim,
            context,
            evidence_projection_hashes=(projection_hash,),
            selection_reason="ORDER-008 typed assertion fail-closed kill",
        )
        assert execution.verdict == Verdict.INCONCLUSIVE
        assert execution.target_claim_hashes == (claim.identity_hash,)
        assert execution.tested_assertion_hash == claim.assertion_hash
        assert execution.execution_snapshot_hash
