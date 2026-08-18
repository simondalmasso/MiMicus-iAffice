from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from mimicus.canonical import canonical_json, sha256_obj
from mimicus.claims.models import Evidence
from mimicus.falsifiers.spec import FalsifierExecution

_EVIDENCE_KEYS = {
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
}


def _observed(fixture: dict[str, Any]) -> datetime:
    for key in ("as_of", "evidence_date", "observed_at"):
        value = fixture.get(key)
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
                return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)
            except ValueError:
                continue
    return datetime(1970, 1, 1, tzinfo=UTC)


def fixture_evidence(fixture: dict[str, Any], *, domain: str, scenario: str) -> list[Evidence]:
    material = {key: fixture[key] for key in sorted(_EVIDENCE_KEYS) if key in fixture}
    if not material:
        return []
    clusters = fixture.get("clusters")
    cluster = str(clusters[0]) if isinstance(clusters, list) and clusters else str(fixture.get("independence_cluster") or f"fixture:{scenario}")
    origin = str(fixture.get("source_id") or fixture.get("origin") or f"fixture:{scenario}")
    snapshot_hash = str(fixture.get("registry_snapshot_hash") or sha256_obj({"domain": domain, "scenario": scenario, "material": material}))
    if len(snapshot_hash) != 64:
        snapshot_hash = sha256_obj({"declared_snapshot": snapshot_hash, "material": material})
    return [
        Evidence(
            evidence_id=sha256_obj({"origin": origin, "snapshot": snapshot_hash})[:32],
            origin=origin,
            source_class="pinned_fixture_snapshot",
            trust_authority=1.0,
            observed_at=_observed(fixture),
            snapshot_hash=snapshot_hash,
            extraction_method="deterministic_structured_fixture",
            independence_cluster=cluster,
            content=canonical_json(material),
        )
    ]


def execution_evidence(execution: FalsifierExecution) -> Evidence:
    return Evidence(
        evidence_id=sha256_obj({"spec": execution.spec_hash, "snapshot": execution.execution_snapshot_hash})[:32],
        origin=f"falsifier:{execution.spec_hash}",
        source_class="deterministic_falsifier_execution",
        trust_authority=1.0,
        observed_at=datetime(1970, 1, 1, tzinfo=UTC),
        snapshot_hash=execution.execution_snapshot_hash,
        extraction_method="trusted_primitive_execution",
        independence_cluster=f"falsifier:{execution.spec_hash}",
        content=canonical_json({"verdict": execution.verdict.value, "evidence": execution.evidence, "reason": execution.reason}),
    )


def evidence_row(evidence: Evidence) -> dict[str, Any]:
    return evidence.model_dump(mode="json") | {"evidence_hash": evidence.hash}
