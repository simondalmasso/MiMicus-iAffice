from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
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


class NumericAssertion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["numeric"] = "numeric"
    asserted_value: float

    @property
    def hash(self) -> str:
        return sha256_obj(self)


class TemporalAssertion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["temporal"] = "temporal"
    as_of: datetime
    max_age_days: int | None = Field(default=None, ge=0, le=36500)

    @property
    def hash(self) -> str:
        return sha256_obj(self)


class SourceIndependenceAssertion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["source_independence"] = "source_independence"
    required_independent: int = Field(default=2, ge=2, le=16)

    @property
    def hash(self) -> str:
        return sha256_obj(self)


class EntailmentAssertion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["citation_entailment"] = "citation_entailment"
    claim_figure: str

    @property
    def hash(self) -> str:
        return sha256_obj(self)


class CounterexampleAssertion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["counterexample_absence"] = "counterexample_absence"
    absence_key: str = Field(min_length=1, max_length=256)

    @property
    def hash(self) -> str:
        return sha256_obj(self)


class OpaqueAssertion(BaseModel):
    """Typed non-deterministic proposition marker.

    Opaque assertions remain valid claims but deterministic falsifiers must
    return INCONCLUSIVE rather than infer truth from free text.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")
    kind: Literal["opaque"] = "opaque"
    semantic_key: str = Field(min_length=1, max_length=256)

    @property
    def hash(self) -> str:
        return sha256_obj(self)


ClaimAssertion = Annotated[
    NumericAssertion
    | TemporalAssertion
    | SourceIndependenceAssertion
    | EntailmentAssertion
    | CounterexampleAssertion
    | OpaqueAssertion,
    Field(discriminator="kind"),
]


class Claim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim_id: str = Field(default_factory=lambda: str(uuid4()))
    statement: str
    domain: str
    probability: float = Field(ge=0.0, le=1.0)
    claim_type: Literal["numeric", "factual", "causal", "temporal", "comparative", "other"] = "other"
    assertion: ClaimAssertion | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    units: str | None = None
    as_of: datetime | None = None
    status: ClaimStatus = ClaimStatus.PROPOSED

    @property
    def assertion_hash(self) -> str | None:
        return None if self.assertion is None else self.assertion.hash

    @property
    def identity_material(self) -> dict[str, object]:
        """Immutable sealed semantic/evidence/assertion anchor.

        Probability, epistemic status and revision metadata are deliberately
        excluded so a challenge cannot orphan falsifier/receipt lineage. The
        typed assertion is included because changing the predicate being tested
        is a different claim identity even when free text happens to match.
        """
        return {
            "claim_id": self.claim_id,
            "statement": self.statement,
            "domain": self.domain,
            "claim_type": self.claim_type,
            "assertion": None if self.assertion is None else self.assertion.model_dump(mode="json"),
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
        """Compatibility alias: all target lineage uses stable identity."""
        return self.identity_hash
