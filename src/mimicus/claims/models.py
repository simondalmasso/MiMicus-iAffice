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
    def identity_material(self) -> dict[str, object]:
        """Immutable sealed semantic/evidence anchor.

        Probability, epistemic status and revision metadata are deliberately
        excluded so a challenge cannot orphan falsifier/receipt lineage.
        """
        return {
            "claim_id": self.claim_id,
            "statement": self.statement,
            "domain": self.domain,
            "claim_type": self.claim_type,
            "evidence_refs": tuple(sorted(set(self.evidence_refs))),
            "units": self.units,
            "as_of": self.as_of,
        }

    @property
    def identity_hash(self) -> str:
        return sha256_obj(self.identity_material)

    @property
    def revision_hash(self) -> str:
        return sha256_obj(
            {
                "claim_identity_hash": self.identity_hash,
                "probability": self.probability,
                "status": self.status.value,
            }
        )

    @property
    def hash(self) -> str:
        """Compatibility alias: all target lineage now uses stable identity."""
        return self.identity_hash
