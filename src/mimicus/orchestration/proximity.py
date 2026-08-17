from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from mimicus.canonical import sha256_obj

_TOKEN_RE = re.compile(r"[a-z0-9]+")
_NEGATIONS = {"no", "not", "never", "none", "without", "false", "cannot", "can't"}


def normalized_tokens(text: str) -> frozenset[str]:
    return frozenset(_TOKEN_RE.findall(text.lower()))


def _jaccard(left: Iterable[str], right: Iterable[str]) -> float:
    a, b = set(left), set(right)
    if not a and not b:
        return 1.0
    return len(a & b) / max(1, len(a | b))


@dataclass(frozen=True)
class SemanticSignature:
    statement: str
    domain: str = "general"
    claim_type: str = "other"
    units: str | None = None
    as_of: str | None = None
    evidence_clusters: tuple[str, ...] = ()
    primitive: str | None = None
    trigger: str | None = None
    numeric_value: float | None = None

    @property
    def hash(self) -> str:
        return sha256_obj(self)


@dataclass(frozen=True)
class ProximityResult:
    score: float
    marginal_novelty: float
    useful_contradiction: bool
    token_similarity: float
    feature_overlap: float
    evidence_overlap: float
    primitive_overlap: float
    reason: str


def _polarity(text: str) -> int:
    tokens = normalized_tokens(text)
    return -1 if tokens & _NEGATIONS else 1


def semantic_proximity(left: SemanticSignature, right: SemanticSignature) -> ProximityResult:
    token_similarity = _jaccard(normalized_tokens(left.statement), normalized_tokens(right.statement))
    features = [
        left.domain == right.domain,
        left.claim_type == right.claim_type,
        left.units == right.units and left.units is not None,
        left.as_of == right.as_of and left.as_of is not None,
    ]
    feature_overlap = sum(bool(value) for value in features) / len(features)
    evidence_overlap = _jaccard(left.evidence_clusters, right.evidence_clusters) if (left.evidence_clusters or right.evidence_clusters) else 0.0
    primitive_overlap = 1.0 if left.primitive and left.primitive == right.primitive else 0.0
    useful_contradiction = False
    if token_similarity >= 0.35 and _polarity(left.statement) != _polarity(right.statement):
        useful_contradiction = True
    if left.numeric_value is not None and right.numeric_value is not None and left.numeric_value != right.numeric_value and token_similarity >= 0.25:
        useful_contradiction = True
    raw = 0.50 * token_similarity + 0.20 * feature_overlap + 0.20 * evidence_overlap + 0.10 * primitive_overlap
    score = min(1.0, max(0.0, raw))
    if useful_contradiction:
        marginal = max(0.65, 1.0 - score * 0.35)
        reason = "retained: lexical overlap carries contradictory falsifiable direction/value"
    else:
        marginal = max(0.0, 1.0 - score)
        reason = "demoted as redundant" if score >= 0.75 else "retained for marginal diversity"
    return ProximityResult(score, marginal, useful_contradiction, token_similarity, feature_overlap, evidence_overlap, primitive_overlap, reason)


def proposal_marginal_value(candidate: SemanticSignature, existing: Iterable[SemanticSignature]) -> tuple[float, list[ProximityResult]]:
    comparisons = [semantic_proximity(candidate, other) for other in existing]
    if not comparisons:
        return 1.0, []
    value = min(result.marginal_novelty for result in comparisons)
    if any(result.useful_contradiction for result in comparisons):
        value = max(value, 0.65)
    return value, comparisons
