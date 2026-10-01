from __future__ import annotations

from dataclasses import dataclass, field

from mimicus.coalition.threat_profile import ThreatProfile
from mimicus.orchestration.proximity import SemanticSignature, semantic_proximity


@dataclass(frozen=True)
class AgentCandidate:
    fingerprint: str
    name: str
    capabilities: frozenset[str]
    provider: str
    model: str
    prompt_hash: str
    tool_hash: str
    audition_score: float = 1.0
    calibration_score: float = 0.5
    bankrupt: bool = False
    historical_cofailure: dict[str, float] = field(default_factory=dict)
    historical_marginal_value: dict[str, float] = field(default_factory=dict)
    lineage_id: str | None = None
    probation: bool = False
    phenotype_version: str = "v1"
    policy_hash: str = ""
    provider_adapter_version: str = "unknown"
    runtime_model_version: str = "unknown"
    capability_audition_scores: dict[str, float] = field(default_factory=dict)
    capability_calibration_scores: dict[str, float] = field(default_factory=dict)
    capability_states: dict[str, str] = field(default_factory=dict)


def correlation(a: AgentCandidate, b: AgentCandidate) -> float:
    shared_policy = bool(a.policy_hash) and a.policy_hash == b.policy_hash
    shared = (
        0.35 * float(a.provider == b.provider)
        + 0.35 * float(a.model == b.model and a.runtime_model_version == b.runtime_model_version)
        + 0.15 * float(a.prompt_hash == b.prompt_hash)
        + 0.10 * float(a.tool_hash == b.tool_hash)
        + 0.05 * float(shared_policy)
    )
    empirical = max(a.historical_cofailure.get(b.fingerprint, 0.0), b.historical_cofailure.get(a.fingerprint, 0.0))
    return min(1.0, 0.80 * shared + 0.20 * empirical)


def _signature(candidate: AgentCandidate) -> SemanticSignature:
    return SemanticSignature(
        statement=f"{candidate.name} {' '.join(sorted(candidate.capabilities))}",
        domain="agent-candidate",
        claim_type="capability",
        evidence_clusters=(candidate.provider, candidate.model),
    )


def _capability_state(candidate: AgentCandidate, capability: str) -> str:
    if candidate.capability_states:
        return candidate.capability_states.get(capability, "ACTIVE")
    if candidate.bankrupt:
        return "BANKRUPT"
    if candidate.probation:
        return "PROBATION"
    return "ACTIVE"


def _capability_trust(candidate: AgentCandidate, capability: str) -> float:
    audition_score = candidate.capability_audition_scores.get(capability, candidate.audition_score)
    calibration_score = candidate.capability_calibration_scores.get(capability, candidate.calibration_score)
    return 0.55 * audition_score + 0.45 * calibration_score


def _usable_capabilities(candidate: AgentCandidate, required: set[str]) -> set[str]:
    return {cap for cap in required & set(candidate.capabilities) if _capability_state(candidate, cap) == "ACTIVE"}


def select_coalition(profile: ThreatProfile, candidates: list[AgentCandidate], max_agents: int) -> tuple[list[AgentCandidate], dict[str, object]]:
    required = set(profile.required_capabilities)
    available = [candidate for candidate in candidates if _usable_capabilities(candidate, required)]
    selected: list[AgentCandidate] = []
    uncovered = set(required)
    proximity_log: list[dict[str, object]] = []
    while uncovered and len(selected) < max_agents:
        best: AgentCandidate | None = None
        best_score = -1.0
        for candidate in available:
            if candidate in selected:
                continue
            useful_caps = _usable_capabilities(candidate, uncovered)
            if not useful_caps:
                continue
            corr_penalty = max((correlation(candidate, member) for member in selected), default=0.0)
            proximity_penalty = 0.0
            proximity_reason = "first useful candidate"
            if selected:
                comparisons = [semantic_proximity(_signature(candidate), _signature(member)) for member in selected]
                closest = max(comparisons, key=lambda row: row.score)
                proximity_penalty = 0.45 * closest.score if not closest.useful_contradiction else 0.0
                proximity_reason = closest.reason
            capability_trust = {cap: _capability_trust(candidate, cap) for cap in sorted(useful_caps)}
            authority = sum(capability_trust.values())
            marginal = sum(candidate.historical_marginal_value.get(cap, 0.0) for cap in useful_caps) / max(1, len(useful_caps))
            secondary_multiplier = 1.0 + 0.08 * max(-1.0, min(1.0, marginal))
            score = authority * (1.0 - 0.8 * corr_penalty) * max(0.05, 1.0 - proximity_penalty) * secondary_multiplier
            proximity_log.append(
                {
                    "candidate": candidate.fingerprint,
                    "capability_coverage": sorted(useful_caps),
                    "capability_trust": capability_trust,
                    "correlation_penalty": corr_penalty,
                    "proximity_penalty": proximity_penalty,
                    "verified_marginal_secondary": marginal,
                    "reason": proximity_reason,
                    "marginal_score": score,
                }
            )
            if score > best_score:
                best_score, best = score, candidate
        if best is None:
            break
        selected.append(best)
        uncovered -= _usable_capabilities(best, uncovered)
    rationale: dict[str, object] = {
        "required_capabilities": sorted(required),
        "covered_capabilities": sorted(required - uncovered),
        "uncovered_capabilities": sorted(uncovered),
        "selected": [candidate.fingerprint for candidate in selected],
        "correlation_matrix": {f"{a.fingerprint}:{b.fingerprint}": correlation(a, b) for i, a in enumerate(selected) for b in selected[i + 1 :]},
        "semantic_proximity": proximity_log,
        "capability_authority": {
            candidate.fingerprint: {
                cap: {
                    "state": _capability_state(candidate, cap),
                    "audition_score": candidate.capability_audition_scores.get(cap, candidate.audition_score),
                    "calibration_score": candidate.capability_calibration_scores.get(cap, candidate.calibration_score),
                    "direct_trust": _capability_trust(candidate, cap),
                    "verified_marginal_secondary": candidate.historical_marginal_value.get(cap, 0.0),
                }
                for cap in sorted(required & set(candidate.capabilities))
            }
            for candidate in candidates
        },
        "probation_excluded": [
            candidate.fingerprint
            for candidate in candidates
            if all(_capability_state(candidate, cap) == "PROBATION" for cap in required & set(candidate.capabilities)) and required & set(candidate.capabilities)
        ],
        "bankrupt_excluded": [
            candidate.fingerprint
            for candidate in candidates
            if all(_capability_state(candidate, cap) == "BANKRUPT" for cap in required & set(candidate.capabilities)) and required & set(candidate.capabilities)
        ],
    }
    return selected, rationale
