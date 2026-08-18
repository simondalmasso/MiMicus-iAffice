from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

CANARY_BANK: dict[str, tuple[str, str]] = {
    "semantic_decoy": ("Choose relevant evidence, ignore topical decoy.", "relevant"),
    "parameter_trap": ("Use the supplied annualization parameter exactly.", "parameter"),
    "capability_mirage": ("Reject a tool that cannot perform the claimed action.", "reject"),
    "prerequisite_blindness": ("Identify missing prerequisite before execution.", "missing"),
    "temporal_decoy": ("Prefer evidence valid at the requested as-of date.", "fresh"),
    "granularity_trap": ("Do not infer city-level truth from country-level aggregate.", "granular"),
}


@dataclass(frozen=True)
class AuditionResult:
    fingerprint: str
    domain: str
    category: str
    passed: bool | None
    score: float
    capability: str = "generic"
    test_family: str = "canary"
    applicability: Literal["APPLICABLE", "NOT_APPLICABLE"] = "APPLICABLE"

    @property
    def affects_trust(self) -> bool:
        return self.applicability == "APPLICABLE" and self.passed is not None


def audition(
    fingerprint: str,
    domain: str,
    category: str,
    scripted_answer: str,
    *,
    capability: str = "generic",
    test_family: str | None = None,
    supported: bool = True,
) -> AuditionResult:
    """Deterministically score an answer that was produced by a provider execution."""
    if category not in CANARY_BANK:
        raise KeyError(category)
    if not supported:
        return AuditionResult(
            fingerprint,
            domain,
            category,
            None,
            0.5,
            capability=capability,
            test_family=test_family or category,
            applicability="NOT_APPLICABLE",
        )
    expected = CANARY_BANK[category][1]
    passed = expected.lower() in scripted_answer.lower()
    return AuditionResult(
        fingerprint,
        domain,
        category,
        passed,
        1.0 if passed else 0.0,
        capability=capability,
        test_family=test_family or category,
        applicability="APPLICABLE",
    )
