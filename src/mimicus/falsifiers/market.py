from __future__ import annotations

from dataclasses import asdict, dataclass

from mimicus.canonical import sha256_obj
from mimicus.falsifiers.spec import FalsifierSpec


def _tokens(value: str) -> set[str]:
    return {token for token in "".join(ch.lower() if ch.isalnum() else " " for ch in value).split() if token}


def _param_band(value: object) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, (int, float)):
        number = float(value)
        if number == 0:
            return "0"
        magnitude = 1.0
        while abs(number) >= 10 * magnitude:
            magnitude *= 10
        while abs(number) < magnitude and magnitude > 1e-9:
            magnitude /= 10
        return f"{round(number / magnitude, 1)}e{magnitude:g}"
    return str(value)[:80].lower()


@dataclass(frozen=True)
class FalsifierSignature:
    primitive: str
    trigger_tokens: tuple[str, ...]
    evidence_targets: tuple[str, ...]
    oracle_kind: str
    parameter_bands: tuple[tuple[str, str], ...]

    @property
    def hash(self) -> str:
        return sha256_obj(asdict(self))


def falsifier_signature(spec: FalsifierSpec) -> FalsifierSignature:
    target_keys = ("source", "origin", "cluster", "registry", "span", "figure", "date", "unit")
    targets = tuple(sorted(token for token in _tokens(spec.trigger) if any(key in token for key in target_keys)))
    bands = tuple(sorted((str(key), _param_band(value)) for key, value in spec.params.items()))
    return FalsifierSignature(spec.primitive, tuple(sorted(_tokens(spec.trigger))), targets, spec.oracle_kind, bands)


def falsifier_proximity(left: FalsifierSpec, right: FalsifierSpec) -> float:
    a, b = falsifier_signature(left), falsifier_signature(right)
    primitive = 1.0 if a.primitive == b.primitive else 0.0
    ta, tb = set(a.trigger_tokens), set(b.trigger_tokens)
    trigger = len(ta & tb) / max(1, len(ta | tb))
    pa, pb = set(a.parameter_bands), set(b.parameter_bands)
    params = len(pa & pb) / max(1, len(pa | pb)) if pa or pb else 1.0
    oracle = 1.0 if a.oracle_kind == b.oracle_kind else 0.0
    ea, eb = set(a.evidence_targets), set(b.evidence_targets)
    evidence = len(ea & eb) / max(1, len(ea | eb)) if ea or eb else 0.0
    return min(1.0, 0.45 * primitive + 0.20 * trigger + 0.20 * params + 0.10 * oracle + 0.05 * evidence)


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
    base_utility: float = 0.0
    redundancy_penalty: float = 0.0
    novelty_bonus: float = 0.0
    closest_proximity: float = 0.0
    retention_reason: str = "base_utility"
    signature_hash: str = ""


class FalsifierMarket:
    def score(self, spec: FalsifierSpec, *, applicability: float = 1.0, evidence_quality: float = 1.0, risk_cost: float = 0.0) -> CandidateScore:
        latency_cost = spec.estimated_latency / 100_000.0
        denominator = max(1e-9, spec.estimated_cost + latency_cost + risk_cost)
        utility = spec.expected_information_gain * applicability * evidence_quality / denominator
        return CandidateScore(
            spec.hash,
            utility,
            spec.expected_information_gain,
            applicability,
            evidence_quality,
            spec.estimated_cost,
            latency_cost,
            risk_cost,
            base_utility=utility,
            signature_hash=falsifier_signature(spec).hash,
        )

    def select(self, specs: list[FalsifierSpec], *, budget_usd: float, max_tests: int, information_floor: float = 0.0) -> tuple[list[FalsifierSpec], list[CandidateScore]]:
        base = [(spec, self.score(spec)) for spec in specs]
        base.sort(key=lambda pair: (-pair[1].base_utility, pair[0].hash))
        selected: list[FalsifierSpec] = []
        spent = 0.0
        final_scores: list[CandidateScore] = []
        for spec, score in base:
            closest = max((falsifier_proximity(spec, chosen) for chosen in selected), default=0.0)
            near_duplicate = bool(selected) and closest >= 0.80 and any(chosen.primitive == spec.primitive for chosen in selected)
            redundancy_penalty = score.base_utility * (0.95 if near_duplicate else 0.35 * closest)
            novelty_bonus = score.base_utility * (0.10 * max(0.0, 1.0 - closest)) if selected and not near_duplicate else 0.0
            final_utility = max(0.0, score.base_utility - redundancy_penalty + novelty_bonus)
            reason = "near_duplicate_substitute" if near_duplicate else ("complementary_or_novel" if selected else "first_high_utility")
            scored = CandidateScore(
                spec_hash=score.spec_hash,
                utility=final_utility,
                expected_information_gain=score.expected_information_gain,
                applicability=score.applicability,
                evidence_quality=score.evidence_quality,
                monetary_cost=score.monetary_cost,
                latency_cost=score.latency_cost,
                risk_cost=score.risk_cost,
                base_utility=score.base_utility,
                redundancy_penalty=redundancy_penalty,
                novelty_bonus=novelty_bonus,
                closest_proximity=closest,
                retention_reason=reason,
                signature_hash=score.signature_hash,
            )
            final_scores.append(scored)
            if len(selected) >= max_tests or score.expected_information_gain < information_floor or near_duplicate:
                continue
            if spent + spec.estimated_cost > budget_usd + 1e-12:
                continue
            selected.append(spec)
            spent += spec.estimated_cost
        return selected, final_scores
