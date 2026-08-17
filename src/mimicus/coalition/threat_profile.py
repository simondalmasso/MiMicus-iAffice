from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ThreatProfile(BaseModel):
    model_config = ConfigDict(frozen=True)
    domain: str
    threats: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    complexity: float = Field(ge=0.0, le=1.0)


def profile_task(task: str, domain: str, scenario: str | None = None) -> ThreatProfile:
    text = f"{task} {scenario or ''}".lower()
    threats: list[str] = []
    capabilities: list[str] = []
    if any(token in text for token in ("tam", "numeric", "price", "revenue", "12x", "12×")):
        threats.append("numeric_inconsistency")
        capabilities.append("numeric")
    if any(token in text for token in ("fresh", "date", "current", "stale")):
        threats.append("temporal_staleness")
        capabilities.append("freshness")
    if any(token in text for token in ("source", "citation", "echo", "origin")):
        threats.append("source_correlation")
        capabilities.extend(["source", "independence"])
    if any(token in text for token in ("entail", "figure", "quote")):
        threats.append("citation_mismatch")
        capabilities.append("entailment")
    if any(token in text for token in ("absence", "counterexample", "none exist")):
        threats.append("absence_claim")
        capabilities.append("counterexample")
    if not capabilities:
        capabilities.append("synthesize")
        threats.append("general_epistemic_error")
    unique_caps = tuple(dict.fromkeys(capabilities))
    complexity = min(1.0, 0.2 + 0.18 * len(unique_caps))
    return ThreatProfile(domain=domain, threats=tuple(threats), required_capabilities=unique_caps, complexity=complexity)
