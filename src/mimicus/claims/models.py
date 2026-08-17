from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from mimicus.canonical import sha256_obj
from mimicus.types import ClaimStatus


class Evidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_id: str = Field(default_factory=lambda: str(uuid4()))
    origin: str
    source_class: str
    trust_authority: float = Field(ge=0.0, le=1.0)
    observed_at: datetime
    snapshot_hash: str = Field(min_length=64, max_length=64)
    extraction_method: str
    independence_cluster: str
    content: str = ""

    @property
    def hash(self) -> str:
        return sha256_obj(self)


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(default_factory=lambda: str(uuid4()))
    statement: str
    domain: str
    probability: float = Field(ge=0.0, le=1.0)
    claim_type: Literal["numeric", "factual", "causal", "temporal", "comparative", "other"] = "other"
    evidence_refs: list[str] = Field(default_factory=list)
    units: str | None = None
    as_of: datetime | None = None
    status: ClaimStatus = ClaimStatus.PROPOSED

    @property
    def hash(self) -> str:
        return sha256_obj(self)
