from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from mimicus.canonical import sha256_obj
from mimicus.types import Verdict

PrimitiveName = Literal[
    "numeric_invariant",
    "freshness",
    "source_independence",
    "citation_entailment",
    "counterexample_search",
]


class FalsifierSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    version: str
    domain: str
    trigger: str
    primitive: PrimitiveName
    params: dict[str, object] = Field(default_factory=dict)
    oracle_kind: Literal["deterministic", "registry", "supplemental_llm"] = "deterministic"
    expected_information_gain: float = Field(ge=0.0)
    estimated_cost: float = Field(ge=0.0)
    estimated_latency: float = Field(ge=0.0)
    provenance: str
    valid_from: datetime | None = None
    expires_at: datetime | None = None
    parent_hash: str | None = None

    @field_validator("params")
    @classmethod
    def reject_executable_payloads(cls, value: dict[str, object]) -> dict[str, object]:
        forbidden = {"script", "source", "python", "javascript", "sql", "code"}
        if forbidden.intersection(key.lower() for key in value):
            raise ValueError("executable source fields are forbidden in FalsifierSpec")
        return value

    @property
    def hash(self) -> str:
        return sha256_obj(self)


class FalsifierExecution(BaseModel):
    model_config = ConfigDict(frozen=True)

    spec_hash: str
    verdict: Verdict
    evidence: dict[str, object] = Field(default_factory=dict)
    execution_snapshot_hash: str
    cost: float = 0.0
    latency_ms: float = 0.0
    reason: str | None = None
    target_claim_hashes: tuple[str, ...] = ()
    selection_reason: str | None = None
