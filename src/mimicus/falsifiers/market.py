from __future__ import annotations

from dataclasses import dataclass

from mimicus.falsifiers.spec import FalsifierSpec


@dataclass(frozen=True)
class CandidateScore:
    spec_hash: str
    utility: float
    expected_information_gain: float
    applicability: float
    evidence_quality: float
    monetary_cost: float
    latency_cost: float
    risk_cost: float


class FalsifierMarket:
    def score(self, spec: FalsifierSpec, *, applicability: float = 1.0, evidence_quality: float = 1.0, risk_cost: float = 0.0) -> CandidateScore:
        latency_cost = spec.estimated_latency / 100_000.0
        denominator = max(1e-9, spec.estimated_cost + latency_cost + risk_cost)
        utility = spec.expected_information_gain * applicability * evidence_quality / denominator
        return CandidateScore(spec.hash, utility, spec.expected_information_gain, applicability, evidence_quality, spec.estimated_cost, latency_cost, risk_cost)

    def select(self, specs: list[FalsifierSpec], *, budget_usd: float, max_tests: int, information_floor: float = 0.0) -> tuple[list[FalsifierSpec], list[CandidateScore]]:
        scored = [(spec, self.score(spec)) for spec in specs]
        scored.sort(key=lambda pair: (-pair[1].utility, pair[0].hash))
        selected: list[FalsifierSpec] = []
        spent = 0.0
        for spec, score in scored:
            if len(selected) >= max_tests or score.expected_information_gain < information_floor:
                continue
            if spent + spec.estimated_cost > budget_usd + 1e-12:
                continue
            selected.append(spec)
            spent += spec.estimated_cost
        return selected, [score for _, score in scored]
