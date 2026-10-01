from __future__ import annotations

import math
import re
from collections.abc import Callable
from datetime import datetime
from typing import Any, cast

from mimicus.canonical import sha256_obj
from mimicus.claims.models import (
    Claim,
    CounterexampleAssertion,
    EntailmentAssertion,
    NumericAssertion,
    SourceIndependenceAssertion,
    TemporalAssertion,
)
from mimicus.falsifiers.spec import FalsifierExecution, FalsifierSpec
from mimicus.types import Verdict


def _result(spec: FalsifierSpec, verdict: Verdict, evidence: dict[str, object], reason: str | None = None) -> FalsifierExecution:
    snapshot = {"spec_hash": spec.hash, "evidence": evidence, "verdict": verdict.value, "reason": reason}
    return FalsifierExecution(
        spec_hash=spec.hash,
        verdict=verdict,
        evidence=evidence,
        execution_snapshot_hash=sha256_obj(snapshot),
        cost=spec.estimated_cost,
        latency_ms=spec.estimated_latency,
        reason=reason,
    )


def numeric_invariant(spec: FalsifierSpec, context: dict[str, Any]) -> FalsifierExecution:
    required = ("price", "users", "claimed")
    if any(context.get(key) is None for key in required):
        return _result(spec, Verdict.INCONCLUSIVE, {}, "missing numeric evidence")
    try:
        price = float(context["price"])
        users = float(context["users"])
        claimed = float(context["claimed"])
        period = str(context.get("price_period", "annual")).lower()
        tolerance = float(cast(Any, spec.params.get("relative_tolerance", context.get("relative_tolerance", 0.05))))
    except (TypeError, ValueError):
        return _result(spec, Verdict.INCONCLUSIVE, {}, "ambiguous numeric parse")
    if not 0.0 <= tolerance <= 0.25:
        return _result(spec, Verdict.INCONCLUSIVE, {"tolerance": tolerance}, "tolerance outside safe bound")
    factors = {"annual": 1.0, "year": 1.0, "monthly": 12.0, "month": 12.0, "weekly": 52.0, "week": 52.0, "daily": 365.0, "day": 365.0}
    if period not in factors or any(not math.isfinite(v) for v in (price, users, claimed)):
        return _result(spec, Verdict.INCONCLUSIVE, {"period": period}, "unsupported period or non-finite value")
    expected = price * factors[period] * users
    rel_error = (0.0 if claimed == 0 else math.inf) if expected == 0 else abs(claimed - expected) / abs(expected)
    verdict = Verdict.PASS if rel_error <= tolerance else Verdict.FAIL
    return _result(spec, verdict, {"expected": expected, "claimed": claimed, "relative_error": rel_error, "tolerance": tolerance, "normalized_period": "annual"})


def _parse_dt(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def freshness(spec: FalsifierSpec, context: dict[str, Any]) -> FalsifierExecution:
    evidence_dt = _parse_dt(context.get("evidence_date"))
    as_of = _parse_dt(context.get("as_of"))
    if evidence_dt is None or as_of is None:
        return _result(spec, Verdict.INCONCLUSIVE, {}, "missing or malformed publication/as-of date")
    if evidence_dt.tzinfo != as_of.tzinfo:
        return _result(spec, Verdict.INCONCLUSIVE, {}, "timezone comparability ambiguous")
    if evidence_dt > as_of:
        return _result(spec, Verdict.FAIL, {"evidence_date": evidence_dt.isoformat(), "as_of": as_of.isoformat()}, "evidence is from the future relative to claim snapshot")
    try:
        max_age = int(cast(Any, spec.params.get("max_age_days", context.get("max_age_days", 30))))
    except (TypeError, ValueError):
        return _result(spec, Verdict.INCONCLUSIVE, {}, "invalid freshness window")
    if max_age < 0:
        return _result(spec, Verdict.INCONCLUSIVE, {"max_age_days": max_age}, "invalid freshness window")
    age = (as_of - evidence_dt).total_seconds() / 86400.0
    verdict = Verdict.PASS if age <= max_age else Verdict.FAIL
    return _result(spec, verdict, {"age_days": age, "max_age_days": max_age})


def _jaccard(a: str, b: str) -> float:
    def tok(text: str) -> set[str]:
        return set(re.findall(r"[a-z0-9]+", text.lower()))

    left, right = tok(a), tok(b)
    if not left and not right:
        return 1.0
    return len(left & right) / max(1, len(left | right))


def source_independence(spec: FalsifierSpec, context: dict[str, Any]) -> FalsifierExecution:
    clusters = context.get("clusters")
    if not isinstance(clusters, list) or len(clusters) < 2 or any(not str(c) for c in clusters):
        return _result(spec, Verdict.INCONCLUSIVE, {}, "insufficient provenance clusters")
    required = int(cast(Any, context.get("required_independent", spec.params.get("min_independent", 2))))
    unique = len(set(map(str, clusters)))
    texts = context.get("texts", [])
    max_similarity = 0.0
    if isinstance(texts, list):
        for i, left in enumerate(texts):
            for right in texts[i + 1 :]:
                if isinstance(left, str) and isinstance(right, str):
                    max_similarity = max(max_similarity, _jaccard(left, right))
    similarity_limit = float(cast(Any, spec.params.get("max_syndication_similarity", 0.88)))
    obvious_syndication = len(texts) >= 2 and max_similarity >= similarity_limit
    independent = unique >= required and not obvious_syndication
    verdict = Verdict.PASS if independent else Verdict.FAIL
    reason = "obvious syndicated/near-duplicate support is not independent" if obvious_syndication else None
    return _result(
        spec,
        verdict,
        {
            "observed_sources": len(clusters),
            "independent_clusters": unique,
            "required": required,
            "max_text_similarity": max_similarity,
            "syndication_similarity_limit": similarity_limit,
            "obvious_syndication": obvious_syndication,
            "provenance_primary": True,
        },
        reason,
    )


def citation_entailment(spec: FalsifierSpec, context: dict[str, Any]) -> FalsifierExecution:
    figure = context.get("claim_figure")
    spans = context.get("evidence_spans")
    if figure is None or not isinstance(spans, list) or not spans:
        return _result(spec, Verdict.INCONCLUSIVE, {}, "missing pinned claim figure or evidence spans")
    normalized = str(figure)
    bound = False
    matched_span: str | None = None
    for span in spans:
        if not isinstance(span, dict):
            continue
        supported = [str(v) for v in span.get("supported_figures", [])]
        if normalized in supported and bool(span.get("material_support", False)):
            bound = True
            matched_span = str(span.get("span_id", "unknown"))
            break
    verdict = Verdict.PASS if bound else Verdict.FAIL
    return _result(spec, verdict, {"claim_figure": normalized, "bound": bound, "matched_span": matched_span})


def counterexample_search(spec: FalsifierSpec, context: dict[str, Any]) -> FalsifierExecution:
    key = context.get("absence_key")
    registry = context.get("registry")
    snapshot_hash = context.get("registry_snapshot_hash")
    if not isinstance(key, str) or not isinstance(registry, dict) or not isinstance(snapshot_hash, str) or len(snapshot_hash) != 64:
        return _result(spec, Verdict.INCONCLUSIVE, {}, "registry snapshot is not pinned")
    value = registry.get(key)
    if value is None:
        return _result(spec, Verdict.PASS, {"absence_key": key, "counterexample": None, "registry_snapshot_hash": snapshot_hash})
    return _result(spec, Verdict.FAIL, {"absence_key": key, "counterexample": value, "registry_snapshot_hash": snapshot_hash}, "counterexample found")


PRIMITIVES: dict[str, Callable[[FalsifierSpec, dict[str, Any]], FalsifierExecution]] = {
    "numeric_invariant": numeric_invariant,
    "freshness": freshness,
    "source_independence": source_independence,
    "citation_entailment": citation_entailment,
    "counterexample_search": counterexample_search,
}


def execute_primitive(spec: FalsifierSpec, context: dict[str, Any]) -> FalsifierExecution:
    primitive = PRIMITIVES.get(spec.primitive)
    if primitive is None:
        raise ValueError(f"unknown trusted primitive: {spec.primitive}")
    return primitive(spec, context)


def _claim_context(spec: FalsifierSpec, claim: Claim, evidence_context: dict[str, Any]) -> tuple[dict[str, Any], str | None]:
    context = dict(evidence_context)
    assertion = claim.assertion
    if spec.primitive == "numeric_invariant":
        if not isinstance(assertion, NumericAssertion):
            return context, "target claim has no numeric typed assertion"
        context["claimed"] = assertion.asserted_value
    elif spec.primitive == "freshness":
        if not isinstance(assertion, TemporalAssertion):
            return context, "target claim has no temporal typed assertion"
        context["as_of"] = assertion.as_of
        if assertion.max_age_days is not None:
            context["max_age_days"] = assertion.max_age_days
    elif spec.primitive == "source_independence":
        if not isinstance(assertion, SourceIndependenceAssertion):
            return context, "target claim has no source-independence typed assertion"
        context["required_independent"] = assertion.required_independent
    elif spec.primitive == "citation_entailment":
        if not isinstance(assertion, EntailmentAssertion):
            return context, "target claim has no citation-entailment typed assertion"
        context["claim_figure"] = assertion.claim_figure
    elif spec.primitive == "counterexample_search":
        if not isinstance(assertion, CounterexampleAssertion):
            return context, "target claim has no counterexample typed assertion"
        context["absence_key"] = assertion.absence_key
    return context, None


def execute_claim_bound(
    spec: FalsifierSpec,
    claim: Claim,
    evidence_context: dict[str, Any],
    *,
    evidence_projection_hashes: tuple[str, ...] = (),
    selection_reason: str | None = None,
) -> FalsifierExecution:
    """Execute one deterministic primitive against one exact target predicate.

    The primitive receives only the target claim assertion plus the exact
    evidence projection context. The resulting snapshot cryptographically binds
    claim identity/revision, assertion, evidence projections, spec and verdict.
    No verdict is sprayed across unrelated claims.
    """
    context, incompatibility = _claim_context(spec, claim, evidence_context)
    raw = execute_primitive(spec, context) if incompatibility is None else _result(spec, Verdict.INCONCLUSIVE, {}, incompatibility)
    assertion_hash = claim.assertion_hash
    equivalence_material = {
        "primitive": spec.primitive,
        "assertion_hash": assertion_hash,
        "context_hash": sha256_obj(context),
        "evidence_projection_hashes": tuple(sorted(set(evidence_projection_hashes))),
    }
    equivalence_hash = sha256_obj(equivalence_material)
    bound_evidence: dict[str, object] = {
        "primitive_evidence": raw.evidence,
        "tested_evidence_context": dict(context),
        "target_claim_identity_hash": claim.identity_hash,
        "target_claim_revision_hash": claim.revision_hash,
        "tested_assertion_hash": assertion_hash,
        "evidence_projection_hashes": tuple(sorted(set(evidence_projection_hashes))),
        "evidence_context_hash": sha256_obj(context),
        "deterministic_equivalence_hash": equivalence_hash,
    }
    snapshot_material = {
        "spec_hash": spec.hash,
        "target_claim_identity_hash": claim.identity_hash,
        "target_claim_revision_hash": claim.revision_hash,
        "tested_assertion_hash": assertion_hash,
        "evidence_projection_hashes": tuple(sorted(set(evidence_projection_hashes))),
        "evidence_context_hash": sha256_obj(context),
        "verdict": raw.verdict.value,
        "reason": raw.reason,
        "primitive_evidence": raw.evidence,
    }
    return FalsifierExecution(
        spec_hash=spec.hash,
        verdict=raw.verdict,
        evidence=bound_evidence,
        execution_snapshot_hash=sha256_obj(snapshot_material),
        cost=raw.cost,
        latency_ms=raw.latency_ms,
        reason=raw.reason,
        target_claim_hashes=(claim.identity_hash,),
        selection_reason=selection_reason,
        tested_assertion_hash=assertion_hash,
        tested_revision_hash=claim.revision_hash,
        evidence_projection_hashes=tuple(sorted(set(evidence_projection_hashes))),
        deterministic_equivalence_hash=equivalence_hash,
    )
