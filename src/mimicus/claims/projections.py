from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mimicus.canonical import canonical_json, sha256_obj


class EvidenceProjection(BaseModel):
    """Immutable provider-visible projection of one canonical evidence item.

    Projection identity is derived from the parent evidence identity, the exact
    declared/effective scope, and the exact material supplied to the provider.
    A projection never reuses the parent content identity after material is
    narrowed.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    projection_hash: str = Field(min_length=64, max_length=64)
    projection_snapshot_hash: str = Field(min_length=64, max_length=64)
    parent_evidence_hash: str = Field(min_length=64, max_length=64)
    parent_canonical_evidence_hash: str | None = None
    declared_scope: tuple[str, ...]
    origin: str
    source_class: str
    observed_at: Any | None = None
    as_of: Any | None = None
    independence_cluster: str
    content: str = ""
    extracted_facts: dict[str, Any] = Field(default_factory=dict)
    extraction_method: str
    authority_class: str
    units: str | None = None

    @model_validator(mode="after")
    def identity_recomputes(self) -> EvidenceProjection:
        if self.projection_snapshot_hash != sha256_obj(self.projected_material):
            raise ValueError("projection snapshot hash/material mismatch")
        if self.projection_hash != sha256_obj(self.identity_material):
            raise ValueError("projection hash/material mismatch")
        return self

    @property
    def projected_material(self) -> dict[str, Any]:
        return {
            "origin": self.origin,
            "source_class": self.source_class,
            "observed_at": self.observed_at,
            "as_of": self.as_of,
            "independence_cluster": self.independence_cluster,
            "content": self.content,
            "extracted_facts": self.extracted_facts,
            "extraction_method": self.extraction_method,
            "authority_class": self.authority_class,
            "units": self.units,
        }

    @property
    def identity_material(self) -> dict[str, Any]:
        return {
            "kind": "evidence_projection_v1",
            "parent_evidence_hash": self.parent_evidence_hash,
            "parent_canonical_evidence_hash": self.parent_canonical_evidence_hash,
            "declared_scope": self.declared_scope,
            "projection_snapshot_hash": self.projection_snapshot_hash,
            "projected_material": self.projected_material,
        }

    def provider_payload(self) -> dict[str, Any]:
        """Exact provider-visible payload with its own immutable identity."""
        return {
            "evidence_hash": self.projection_hash,
            "canonical_evidence_hash": self.projection_hash,
            "snapshot_hash": self.projection_snapshot_hash,
            "origin": self.origin,
            "source_class": self.source_class,
            "observed_at": self.observed_at,
            "as_of": self.as_of,
            "independence_cluster": self.independence_cluster,
            "content": self.content,
            "extracted_facts": self.extracted_facts,
            "extraction_method": self.extraction_method,
            "authority_class": self.authority_class,
            "units": self.units,
            "projection_parent_hash": self.parent_evidence_hash,
            "projection_scope": list(self.declared_scope),
        }

    def persisted_row(self) -> dict[str, Any]:
        return self.provider_payload() | {
            "evidence_kind": "projection",
            "projection_hash": self.projection_hash,
            "projection_snapshot_hash": self.projection_snapshot_hash,
        }


def derive_projection(parent: dict[str, Any], declared_scope: tuple[str, ...] | list[str]) -> EvidenceProjection:
    parent_hash = str(parent.get("evidence_hash", ""))
    if len(parent_hash) != 64:
        raise ValueError("projection parent must have a canonical evidence hash")
    scope = tuple(sorted({str(key) for key in declared_scope if str(key)}))
    raw_facts = parent.get("extracted_facts", {})
    facts = raw_facts if isinstance(raw_facts, dict) else {}
    projected_facts = {key: facts[key] for key in scope if key in facts}
    projected_material = {
        "origin": str(parent.get("origin", "")),
        "source_class": str(parent.get("source_class", "unknown")),
        "observed_at": parent.get("observed_at"),
        "as_of": parent.get("as_of"),
        "independence_cluster": str(parent.get("independence_cluster", "unknown")),
        "content": "",
        "extracted_facts": projected_facts,
        "extraction_method": str(parent.get("extraction_method", "unknown")),
        "authority_class": str(parent.get("authority_class", "unknown")),
        "units": parent.get("units"),
    }
    snapshot_hash = sha256_obj(projected_material)
    identity_material = {
        "kind": "evidence_projection_v1",
        "parent_evidence_hash": parent_hash,
        "parent_canonical_evidence_hash": parent.get("canonical_evidence_hash"),
        "declared_scope": scope,
        "projection_snapshot_hash": snapshot_hash,
        "projected_material": projected_material,
    }
    projection_hash = sha256_obj(identity_material)
    projection = EvidenceProjection(
        projection_hash=projection_hash,
        projection_snapshot_hash=snapshot_hash,
        parent_evidence_hash=parent_hash,
        parent_canonical_evidence_hash=(str(parent["canonical_evidence_hash"]) if parent.get("canonical_evidence_hash") is not None else None),
        declared_scope=scope,
        **projected_material,
    )
    # Explicitly force serialization now so malformed/unbounded material fails
    # before the provider boundary, not after execution.
    canonical_json(projection.provider_payload())
    return projection
