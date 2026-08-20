from __future__ import annotations

from datetime import UTC, datetime

import pytest

from mimicus.canonical import sha256_obj
from mimicus.claims.evidence_bundle import EvidenceInput, build_evidence_bundle
from mimicus.claims.projections import EvidenceProjection, derive_projection
from mimicus.orchestration.engine import MiMicusEngine, RunRequest
from mimicus.providers.base import ProviderRequest, ProviderResponse
from mimicus.providers.scripted import ScriptedProvider
from mimicus.verification.models import VerificationSubmission


class MaliciousRefProvider(ScriptedProvider):
    async def generate_request_async(self, request: ProviderRequest) -> ProviderResponse:
        base = await super().generate_request_async(request)
        refs = [str(row["evidence_hash"]) for row in request.evidence if isinstance(row, dict) and isinstance(row.get("evidence_hash"), str)]
        claim = base.claim.model_copy(update={"evidence_refs": [*refs, "f" * 64]})
        return ProviderResponse(
            claim=claim,
            cost=base.cost,
            latency_ms=base.latency_ms,
            trace_id=base.trace_id,
            usage=base.usage,
        )


def _evidence() -> EvidenceInput:
    registry: dict[str, object] = {}
    return EvidenceInput(
        origin="order008://f041",
        independence_cluster="f041-a",
        content="parent content must not leak into narrowed projections",
        extracted_facts={
            "price": 100,
            "users": 12,
            "claimed": 1200,
            "price_period": "annual",
            "evidence_date": "2026-08-19T00:00:00+00:00",
            "as_of": "2026-08-20T00:00:00+00:00",
            "clusters": ["f041-a", "f041-b"],
            "texts": ["alpha", "beta"],
            "claim_figure": "1200",
            "evidence_spans": [{"span_id": "s1", "supported_figures": ["1200"], "material_support": True}],
            "absence_key": "missing",
            "registry": registry,
            "registry_snapshot_hash": sha256_obj(registry),
        },
    )


def test_projection_identity_binds_scope_and_exact_material() -> None:
    bundle = build_evidence_bundle([_evidence()])
    parent = bundle.provider_payload()[0]
    numeric = derive_projection(parent, ("price", "users", "claimed", "price_period"))
    numeric_again = derive_projection(parent, ("claimed", "users", "price_period", "price"))
    source = derive_projection(parent, ("clusters", "texts"))
    assert numeric.projection_hash == numeric_again.projection_hash
    assert numeric.projection_snapshot_hash == sha256_obj(numeric.projected_material)
    assert numeric.projection_hash == sha256_obj(numeric.identity_material)
    assert numeric.projection_hash != source.projection_hash
    assert numeric.parent_evidence_hash == source.parent_evidence_hash == parent["evidence_hash"]
    tampered = numeric.model_dump(mode="python")
    tampered["extracted_facts"] = dict(tampered["extracted_facts"]) | {"price": 999}
    with pytest.raises(ValueError, match="projection snapshot hash/material mismatch"):
        EvidenceProjection.model_validate(tampered)


def test_runtime_projection_refs_proofs_and_restart_are_exact(tmp_path) -> None:
    database = f"sqlite:///{tmp_path / 'f041.db'}"
    provider = MaliciousRefProvider()
    engine = MiMicusEngine(database, provider=provider)
    run = engine.run(
        RunRequest(
            task="Resolve every required audit predicate.",
            domain="research",
            source_mode="runtime",
            evidence=[_evidence()],
            depth="deep",
            max_agents=4,
            max_concurrency=4,
            learn=True,
        )
    )
    assert run.morphology == "hierarchical_fanout_fanin"
    projection_hashes = set(run.evidence_provenance["evidence_projection_hashes"])
    parent_hashes = set(run.evidence_provenance["provider_input_parent_evidence_hashes"])
    assert len(projection_hashes) >= 6
    assert projection_hashes.isdisjoint(parent_hashes)
    assert all("f" * 64 not in row["evidence_refs"] for row in run.final_claims)

    audited = [row for row in run.evidence_provenance["provider_usages"] if row.get("usage", {}).get("projection_hashes_supplied")]
    assert audited
    for row in audited:
        usage = row["usage"]
        supplied = set(usage["evidence_hashes_supplied"])
        assert supplied == set(usage["projection_hashes_supplied"])
        assert set(usage["validated_evidence_refs"]) <= supplied
        assert "f" * 64 in usage["provider_claimed_evidence_refs"]
        assert "f" * 64 in usage["rejected_evidence_refs"]

    restarted = MiMicusEngine(database, provider=MaliciousRefProvider())
    persisted = restarted.repository.get_evidence(run.run_id)
    persisted_projections = {str(row["evidence_hash"]): row for row in persisted if row.get("evidence_kind") == "projection"}
    assert projection_hashes <= set(persisted_projections)
    for projection_hash in projection_hashes:
        projection = EvidenceProjection.model_validate(persisted_projections[projection_hash])
        assert projection.projection_hash == projection_hash
        assert projection.projection_snapshot_hash == sha256_obj(projection.projected_material)

    claim = run.final_claims[0]
    snapshot = next(str(row["execution_snapshot_hash"]) for row in run.falsifiers if str(claim["claim_hash"]) in set(row["target_claim_hashes"]))
    token = "order008-f041-verifier-token-v1"
    restarted.register_verifier_authority(
        verifier_id="oracle:order008-f041",
        authority_class="deterministic_oracle",
        source_independence_cluster="f041-verifier",
        auth_token=token,
    )
    parent_proof = restarted.submit_verification(
        VerificationSubmission(
            run_id=run.run_id,
            claim_hash=str(claim["claim_hash"]),
            verified_status="SUPPORTED",
            authority_class="deterministic_oracle",
            evidence_hashes=(next(iter(parent_hashes)),),
            snapshot_hashes=(snapshot,),
            verifier_id="oracle:order008-f041",
            auth_token=token,
            observed_at=datetime(2026, 8, 20, 11, 30, tzinfo=UTC),
            source_independence_cluster="f041-verifier",
        )
    )
    assert parent_proof["accepted"] is False
    assert parent_proof["receipt"]["rejection_reason"] == "evidence_hash_not_bound_to_run"

    exact_proof = restarted.submit_verification(
        VerificationSubmission(
            run_id=run.run_id,
            claim_hash=str(claim["claim_hash"]),
            verified_status="SUPPORTED",
            authority_class="deterministic_oracle",
            evidence_hashes=(str(claim["evidence_refs"][0]),),
            snapshot_hashes=(snapshot,),
            verifier_id="oracle:order008-f041",
            auth_token=token,
            observed_at=datetime(2026, 8, 20, 11, 31, tzinfo=UTC),
            source_independence_cluster="f041-verifier",
        )
    )
    assert exact_proof["accepted"] is True
