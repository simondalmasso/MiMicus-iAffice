from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from mimicus.canonical import sha256_obj
from mimicus.types import ClaimStatus


class ChallengeRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    challenger_fingerprint: str
    target_fingerprint: str
    target_claim_hash: str
    target_statement_summary: str
    evidence_refs: list[str] = Field(default_factory=list)
    falsifier_observations: list[dict[str, object]] = Field(default_factory=list)
    challenge_reason: str
    round: int = Field(ge=1, le=3)

    @property
    def hash(self) -> str:
        return sha256_obj(self)


class ChallengeResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    disposition: Literal["accepted", "rejected", "partial", "unchanged"]
    revised_probability: float = Field(ge=0.0, le=1.0)
    revised_status: ClaimStatus
    new_evidence_refs: list[str] = Field(default_factory=list)
    rationale_summary: str
    provider_call_id: str | None = None

    @property
    def hash(self) -> str:
        return sha256_obj(self)


@dataclass(frozen=True)
class CommunicationCandidate:
    challenger: str
    target: str
    residual_disagreement: float
    verified_reliability: float
    task_relevance: float
    capability_complementarity: float
    correlation: float
    semantic_proximity: float
    expected_information_gain: float
    estimated_cost: float = 0.0
    estimated_latency_ms: float = 0.0

    @property
    def score(self) -> float:
        benefit = (
            0.28 * self.residual_disagreement
            + 0.16 * self.verified_reliability
            + 0.14 * self.task_relevance
            + 0.14 * self.capability_complementarity
            + 0.28 * self.expected_information_gain
        )
        redundancy = 0.20 * self.correlation + 0.15 * self.semantic_proximity
        resource_penalty = min(0.20, self.estimated_cost * 10.0 + self.estimated_latency_ms / 100_000.0)
        return benefit - redundancy - resource_penalty


def select_sparse_edges(candidates: list[CommunicationCandidate], *, k: int = 2, min_score: float = 0.05) -> list[CommunicationCandidate]:
    if not 1 <= k <= 2:
        raise ValueError("sparse communication k must be 1..2")
    selected: list[CommunicationCandidate] = []
    out_degree: dict[str, int] = {}
    for candidate in sorted(candidates, key=lambda row: (-row.score, row.challenger, row.target)):
        if candidate.score < min_score:
            continue
        if out_degree.get(candidate.challenger, 0) >= k:
            continue
        if any(row.challenger == candidate.challenger and row.target == candidate.target for row in selected):
            continue
        selected.append(candidate)
        out_degree[candidate.challenger] = out_degree.get(candidate.challenger, 0) + 1
    return selected
