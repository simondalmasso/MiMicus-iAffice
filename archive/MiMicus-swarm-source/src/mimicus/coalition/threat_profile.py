from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ThreatProfile(BaseModel):
    model_config = ConfigDict(frozen=True)
    domain: str
    threats: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    complexity: float = Field(ge=0.0, le=1.0)
    uncertainty: float = Field(default=0.5, ge=0.0, le=1.0)
    signal_provenance: tuple[dict[str, Any], ...] = ()


def profile_task(
    task: str,
    domain: str,
    scenario: str | None = None,
    *,
    evidence_facts: dict[str, Any] | None = None,
    verified_memory_coverage: tuple[str, ...] = (),
    prior_verified_failure_modes: tuple[str, ...] = (),
    available_capabilities: tuple[str, ...] = (),
    budget_usd: float | None = None,
    max_concurrency: int | None = None,
) -> ThreatProfile:
    text = f"{task} {scenario or ''}".lower()
    facts = evidence_facts or {}
    threats: list[str] = []
    capabilities: list[str] = []
    signals: list[dict[str, Any]] = []

    def add(threat: str, capability: str, source: str, strength: float) -> None:
        if threat not in threats:
            threats.append(threat)
        if capability not in capabilities:
            capabilities.append(capability)
        signals.append({"source": source, "threat": threat, "capability": capability, "strength": strength})

    lexical = (
        (("tam", "numeric", "price", "revenue", "12x", "12×"), "numeric_inconsistency", "numeric"),
        (("fresh", "date", "current", "stale"), "temporal_staleness", "freshness"),
        (("source", "citation", "echo", "origin"), "source_correlation", "source"),
        (("entail", "figure", "quote"), "citation_mismatch", "entailment"),
        (("absence", "counterexample", "none exist"), "absence_claim", "counterexample"),
    )
    for tokens, threat, capability in lexical:
        if any(token in text for token in tokens):
            add(threat, capability, "task_text_weak", 0.35)
    if any(token in text for token in ("source", "citation", "echo", "origin")):
        add("source_correlation", "independence", "task_text_weak", 0.35)

    keys = set(facts)
    if {"price", "users", "claimed"}.issubset(keys):
        add("numeric_inconsistency", "numeric", "evidence_schema", 1.0)
    if "claim_figure" in keys:
        add("numeric_inconsistency", "numeric", "evidence_schema", 0.85)
    if {"evidence_date", "as_of"}.issubset(keys):
        add("temporal_staleness", "freshness", "evidence_schema", 1.0)
    if "clusters" in keys:
        add("source_correlation", "source", "evidence_schema", 0.9)
        add("source_correlation", "independence", "evidence_schema", 1.0)
    if {"claim_figure", "evidence_spans"}.issubset(keys):
        add("citation_mismatch", "entailment", "evidence_schema", 1.0)
        add("source_correlation", "source", "evidence_schema", 0.7)
    if {"absence_key", "registry"}.issubset(keys):
        add("absence_claim", "counterexample", "evidence_schema", 1.0)

    for capability in prior_verified_failure_modes:
        mapping = {
            "numeric": "numeric_inconsistency",
            "freshness": "temporal_staleness",
            "source": "source_correlation",
            "independence": "source_correlation",
            "entailment": "citation_mismatch",
            "counterexample": "absence_claim",
        }
        if capability in mapping:
            add(mapping[capability], capability, "prior_verified_failure", 0.75)

    available = set(available_capabilities)
    if available:
        capabilities = [cap for cap in capabilities if cap in available]
    if not capabilities:
        capabilities.append("synthesize")
        threats.append("general_epistemic_error")
        signals.append({"source": "fallback", "threat": "general_epistemic_error", "capability": "synthesize", "strength": 0.5})

    if verified_memory_coverage:
        signals.append({"source": "verified_memory", "capabilities": sorted(verified_memory_coverage), "strength": 0.25})
    if budget_usd is not None:
        signals.append({"source": "budget", "budget_usd": budget_usd, "strength": 0.2})
    if max_concurrency is not None:
        signals.append({"source": "concurrency", "max_concurrency": max_concurrency, "strength": 0.2})

    unique_caps = tuple(dict.fromkeys(capabilities))
    structural = sum(1 for row in signals if row.get("source") == "evidence_schema")
    complexity = min(1.0, 0.18 + 0.14 * len(unique_caps) + 0.03 * structural)
    direct_structural = max((float(row.get("strength", 0.0)) for row in signals if row.get("source") == "evidence_schema"), default=0.0)
    uncertainty = min(0.95, max(0.15, 0.62 - 0.22 * direct_structural + 0.04 * max(0, len(unique_caps) - 1)))
    return ThreatProfile(
        domain=domain,
        threats=tuple(threats),
        required_capabilities=unique_caps,
        complexity=complexity,
        uncertainty=uncertainty,
        signal_provenance=tuple(signals),
    )
