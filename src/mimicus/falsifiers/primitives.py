from __future__ import annotations

import math
import re
from collections.abc import Callable
from datetime import datetime
from typing import Any

from mimicus.canonical import sha256_obj
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
        tolerance = float(spec.params.get("relative_tolerance", context.get("relative_tolerance", 0.05)))
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
        max_age = int(spec.params.get("max_age_days", context.get("max_age_days", 30)))
    except (TypeError, ValueError):
        return _result(spec, Verdict.INCONCLUSIVE, {}, "invalid freshness window")
    if max_age < 0:
        return _result(spec, Verdict.INCONCLUSIVE, {"max_age_days": max_age}, "invalid freshness window")
    age = (as_of - evidence_dt).total_seconds() / 86400.0
    verdict = Verdict.PASS if age <= max_age else Verdict.FAIL
    return _result(spec, verdict, {"age_days": age, "max_age_days": max_age})


def _jaccard(a: str, b: str) -> float:
    def tok(text):
        return set(re.findall(r"[a-z0-9]+", text.lower()))

    left, right = tok(a), tok(b)
    if not left and not right:
        return 1.0
    return len(left & right) / max(1, len(left | right))


def source_independence(spec: FalsifierSpec, context: dict[str, Any]) -> FalsifierExecution:
    clusters = context.get("clusters")
    if not isinstance(clusters, list) or len(clusters) < 2 or any(not str(c) for c in clusters):
        return _result(spec, Verdict.INCONCLUSIVE, {}, "insufficient provenance clusters")
    required = int(spec.params.get("min_independent", 2))
    unique = len(set(map(str, clusters)))
    texts = context.get("texts", [])
    max_similarity = 0.0
    if isinstance(texts, list):
        for i, left in enumerate(texts):
            for right in texts[i + 1 :]:
                if isinstance(left, str) and isinstance(right, str):
                    max_similarity = max(max_similarity, _jaccard(left, right))
    verdict = Verdict.PASS if unique >= required else Verdict.FAIL
    return _result(
        spec, verdict, {"observed_sources": len(clusters), "independent_clusters": unique, "required": required, "max_text_similarity": max_similarity, "provenance_primary": True}
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
