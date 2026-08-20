from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from mimicus.canonical import canonical_json, sha256_obj

MAX_EVIDENCE_ITEMS = 16
MAX_EVIDENCE_CONTENT_CHARS = 12_000
MAX_EVIDENCE_BUNDLE_CHARS = 60_000

_FIXTURE_FACT_KEYS = {
    "price",
    "users",
    "price_period",
    "claimed",
    "clusters",
    "texts",
    "evidence_date",
    "as_of",
    "claim_figure",
    "evidence_spans",
    "absence_key",
    "registry",
    "registry_snapshot_hash",
    "public_facts",
    "observations",
    "source_snapshots",
    "benchmark_marker",
}


class EvidenceInput(BaseModel):
    """Bounded caller-supplied evidence. Hashes/provenance authority are derived, never caller-selected."""

    model_config = ConfigDict(extra="forbid")

    origin: str = Field(min_length=1, max_length=512)
    source_class: Literal["caller_supplied"] = "caller_supplied"
    observed_at: datetime | None = None
    as_of: datetime | None = None
    independence_cluster: str = Field(min_length=1, max_length=256)
    content: str = Field(default="", max_length=MAX_EVIDENCE_CONTENT_CHARS)
    extracted_facts: dict[str, Any] = Field(default_factory=dict)
    extraction_method: Literal["caller_supplied"] = "caller_supplied"
    authority_class: Literal["caller_supplied"] = "caller_supplied"
    units: str | None = Field(default=None, max_length=64)

    @model_validator(mode="after")
    def bounded_facts(self) -> EvidenceInput:
        encoded = canonical_json(self.extracted_facts)
        if len(encoded) > MAX_EVIDENCE_CONTENT_CHARS:
            raise ValueError("evidence extracted_facts exceeds bounded size")
        return self


class CanonicalEvidenceItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    evidence_hash: str = Field(min_length=64, max_length=64)
    canonical_evidence_hash: str = Field(min_length=64, max_length=64)
    snapshot_hash: str = Field(min_length=64, max_length=64)
    origin: str
    source_class: str
    observed_at: datetime | None = None
    as_of: datetime | None = None
    independence_cluster: str
    content: str = ""
    extracted_facts: dict[str, Any] = Field(default_factory=dict)
    extraction_method: str
    authority_class: str
    units: str | None = None

    def provider_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class EvidenceBundle(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_mode: Literal["runtime", "fixture", "benchmark"]
    items: tuple[CanonicalEvidenceItem, ...] = ()

    @model_validator(mode="after")
    def bounded_bundle(self) -> EvidenceBundle:
        if len(self.items) > MAX_EVIDENCE_ITEMS:
            raise ValueError(f"evidence bundle exceeds {MAX_EVIDENCE_ITEMS} items")
        if len(canonical_json([item.model_dump(mode="json") for item in self.items])) > MAX_EVIDENCE_BUNDLE_CHARS:
            raise ValueError("evidence bundle exceeds bounded serialized size")
        return self

    @property
    def hashes(self) -> tuple[str, ...]:
        return tuple(item.evidence_hash for item in self.items)

    def provider_payload(self) -> tuple[dict[str, Any], ...]:
        return tuple(item.provider_payload() for item in self.items)

    def persisted_rows(self) -> list[dict[str, Any]]:
        return [item.model_dump(mode="json") for item in self.items]

    def falsifier_context(self) -> dict[str, Any]:
        """Merge only explicit structured facts. Conflicting facts are removed fail-closed."""
        merged: dict[str, Any] = {}
        conflicts: set[str] = set()
        for item in self.items:
            for key, value in item.extracted_facts.items():
                if key in conflicts:
                    continue
                if key in merged and canonical_json(merged[key]) != canonical_json(value):
                    merged.pop(key, None)
                    conflicts.add(key)
                else:
                    merged[key] = value
        if conflicts:
            merged["evidence_conflicts"] = sorted(conflicts)
        return merged


def _canonical_item(
    *,
    run_id: str,
    origin: str,
    source_class: str,
    observed_at: datetime | None,
    as_of: datetime | None,
    independence_cluster: str,
    content: str,
    extracted_facts: dict[str, Any],
    extraction_method: str,
    authority_class: str,
    units: str | None,
) -> CanonicalEvidenceItem:
    material = {
        "origin": origin,
        "source_class": source_class,
        "observed_at": observed_at.isoformat() if observed_at else None,
        "as_of": as_of.isoformat() if as_of else None,
        "independence_cluster": independence_cluster,
        "content": content,
        "extracted_facts": extracted_facts,
        "extraction_method": extraction_method,
        "authority_class": authority_class,
        "units": units,
    }
    snapshot_hash = sha256_obj(material)
    canonical_evidence_hash = sha256_obj({"snapshot_hash": snapshot_hash, "material": material})
    evidence_hash = sha256_obj({"run_id": run_id, "canonical_evidence_hash": canonical_evidence_hash})
    return CanonicalEvidenceItem(
        evidence_hash=evidence_hash,
        canonical_evidence_hash=canonical_evidence_hash,
        snapshot_hash=snapshot_hash,
        origin=origin,
        source_class=source_class,
        observed_at=observed_at,
        as_of=as_of,
        independence_cluster=independence_cluster,
        content=content,
        extracted_facts=extracted_facts,
        extraction_method=extraction_method,
        authority_class=authority_class,
        units=units,
    )


def runtime_evidence_bundle(run_id: str, inputs: list[EvidenceInput]) -> EvidenceBundle:
    if len(inputs) > MAX_EVIDENCE_ITEMS:
        raise ValueError(f"evidence bundle exceeds {MAX_EVIDENCE_ITEMS} items")
    rows = tuple(
        _canonical_item(
            run_id=run_id,
            origin=item.origin,
            source_class="caller_supplied",
            observed_at=item.observed_at,
            as_of=item.as_of,
            independence_cluster=item.independence_cluster,
            content=item.content,
            extracted_facts=dict(item.extracted_facts),
            extraction_method="caller_supplied",
            authority_class="caller_supplied",
            units=item.units,
        )
        for item in inputs
    )
    return EvidenceBundle(source_mode="runtime", items=rows)


def build_evidence_bundle(inputs: list[EvidenceInput], *, run_id: str | None = None) -> EvidenceBundle:
    """Build deterministic runtime evidence when a run identifier is not yet available."""
    effective_run_id = run_id or sha256_obj(
        {"standalone_evidence_inputs": [item.model_dump(mode="json") for item in inputs]}
    )
    return runtime_evidence_bundle(effective_run_id, inputs)


def explicit_fixture_bundle(
    run_id: str,
    fixture: dict[str, Any],
    *,
    domain: str,
    scenario: str,
    benchmark: bool = False,
) -> EvidenceBundle:
    material = {key: fixture[key] for key in sorted(_FIXTURE_FACT_KEYS) if key in fixture}
    if not material:
        return EvidenceBundle(source_mode="benchmark" if benchmark else "fixture", items=())
    observed_at: datetime | None = None
    for key in ("evidence_date", "observed_at"):
        value = fixture.get(key)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                observed_at = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
                break
            except ValueError:
                pass
    as_of: datetime | None = None
    raw_as_of = fixture.get("as_of")
    if isinstance(raw_as_of, str):
        try:
            parsed_as_of = datetime.fromisoformat(raw_as_of.replace("Z", "+00:00"))
            as_of = parsed_as_of if parsed_as_of.tzinfo else parsed_as_of.replace(tzinfo=UTC)
        except ValueError:
            pass
    clusters = fixture.get("clusters")
    cluster = str(clusters[0]) if isinstance(clusters, list) and clusters else str(fixture.get("independence_cluster") or f"fixture:{scenario}")
    source_class = "benchmark_fixture" if benchmark else "test_fixture"
    row = _canonical_item(
        run_id=run_id,
        origin=str(fixture.get("source_id") or fixture.get("origin") or f"{source_class}:{domain}:{scenario}"),
        source_class=source_class,
        observed_at=observed_at,
        as_of=as_of,
        independence_cluster=cluster,
        content=canonical_json(material),
        extracted_facts=material,
        extraction_method="explicit_structured_fixture",
        authority_class="benchmark_fixture" if benchmark else "test_fixture",
        units=str(fixture["units"]) if fixture.get("units") is not None else None,
    )
    return EvidenceBundle(source_mode="benchmark" if benchmark else "fixture", items=(row,))
