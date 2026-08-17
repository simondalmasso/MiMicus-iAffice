from __future__ import annotations

from dataclasses import dataclass, field

from mimicus.coalition.threat_profile import ThreatProfile


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


def correlation(a: AgentCandidate, b: AgentCandidate) -> float:
    features = [a.provider == b.provider, a.model == b.model, a.prompt_hash == b.prompt_hash, a.tool_hash == b.tool_hash]
    lineage = sum(features) / len(features)
    empirical = max(a.historical_cofailure.get(b.fingerprint, 0.0), b.historical_cofailure.get(a.fingerprint, 0.0))
    return min(1.0, 0.75 * lineage + 0.25 * empirical)


def select_coalition(profile: ThreatProfile, candidates: list[AgentCandidate], max_agents: int) -> tuple[list[AgentCandidate], dict[str, object]]:
    required = set(profile.required_capabilities)
    available = [c for c in candidates if not c.bankrupt]
    selected: list[AgentCandidate] = []
    uncovered = set(required)
    while uncovered and len(selected) < max_agents:
        best: AgentCandidate | None = None
        best_score = -1.0
        for candidate in available:
            if candidate in selected:
                continue
            coverage = len(uncovered & candidate.capabilities)
            if coverage == 0:
                continue
            corr_penalty = max((correlation(candidate, member) for member in selected), default=0.0)
            score = coverage * (0.55 * candidate.audition_score + 0.45 * candidate.calibration_score) * (1.0 - 0.8 * corr_penalty)
            if score > best_score:
                best_score, best = score, candidate
        if best is None:
            break
        selected.append(best)
        uncovered -= best.capabilities
    if not selected and available:
        selected.append(max(available, key=lambda c: c.audition_score + c.calibration_score))
    rationale = {
        "required_capabilities": sorted(required),
        "covered_capabilities": sorted(required - uncovered),
        "uncovered_capabilities": sorted(uncovered),
        "selected": [c.fingerprint for c in selected],
        "correlation_matrix": {
            f"{a.fingerprint}:{b.fingerprint}": correlation(a, b)
            for i, a in enumerate(selected)
            for b in selected[i + 1 :]
        },
    }
    return selected, rationale
