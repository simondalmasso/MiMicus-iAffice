from __future__ import annotations

from datetime import UTC, datetime

from mimicus.claims.evidence_bundle import EvidenceInput
from mimicus.claims.models import Claim, NumericAssertion
from mimicus.orchestration.engine import MiMicusEngine, RunRequest
from mimicus.providers.base import ProviderRequest, ProviderResponse
from mimicus.providers.scripted import ScriptedProvider
from mimicus.verification.models import VerificationSubmission


class NearMissProvider(ScriptedProvider):
    async def generate_request_async(self, request: ProviderRequest) -> ProviderResponse:
        self.generate_calls += 1
        refs = [str(row["evidence_hash"]) for row in request.evidence if isinstance(row, dict) and isinstance(row.get("evidence_hash"), str)]
        return ProviderResponse(
            claim=Claim(
                statement="annual amount is 1250",
                domain=request.domain,
                probability=0.8,
                claim_type="numeric",
                assertion=NumericAssertion(asserted_value=1250.0),
                evidence_refs=refs,
            ),
            cost=0.0,
            latency_ms=0.0,
            trace_id=f"f040-{self.generate_calls}",
            usage={"simulated": True, "monetary_cost_status": "KNOWN", "monetary_cost_usd": 0.0},
        )


def _submission(
    run,
    claim_hash: str,
    snapshot: str,
    *,
    status: str,
    token: str,
    supersedes: str | None = None,
    minute: int = 0,
) -> VerificationSubmission:
    return VerificationSubmission(
        run_id=run.run_id,
        claim_hash=claim_hash,
        verified_status=status,
        authority_class="deterministic_oracle",
        snapshot_hashes=(snapshot,),
        verifier_id="oracle:order008-f040",
        auth_token=token,
        observed_at=datetime(2026, 8, 20, 11, minute, tzinfo=UTC),
        source_independence_cluster="order008-f040-origin",
        supersedes_receipt_hash=supersedes,
    )


def test_one_active_origin_and_promotion_cascade_revocation(tmp_path) -> None:
    database = f"sqlite:///{tmp_path / 'f040.db'}"
    engine = MiMicusEngine(database, provider=NearMissProvider())
    run = engine.run(
        RunRequest(
            task="Audit the supplied annual amount.",
            domain="finance",
            source_mode="runtime",
            evidence=[
                EvidenceInput(
                    origin="order008://f040",
                    independence_cluster="evidence-a",
                    content="numeric facts",
                    extracted_facts={"price": 100.0, "users": 12.0, "claimed": 1200.0, "price_period": "annual"},
                )
            ],
            max_agents=1,
            depth="deep",
            learn=True,
        )
    )
    numeric = next(row for row in run.falsifiers if row["primitive"] == "numeric_invariant")
    assert numeric["verdict"] == "PASS"
    claim_hash = str(numeric["target_claim_hashes"][0])
    snapshot = str(numeric["execution_snapshot_hash"])
    token = "order008-f040-authority-token-v1"
    engine.register_verifier_authority(
        verifier_id="oracle:order008-f040",
        authority_class="deterministic_oracle",
        source_independence_cluster="order008-f040-origin",
        auth_token=token,
    )

    first = engine.submit_verification(_submission(run, claim_hash, snapshot, status="FALSIFIED", token=token))
    assert first["accepted"] is True
    assert first["germinal"] is not None
    assert first["germinal"]["status"] == "PROMOTE", first["germinal"]
    candidate_hash = str(first["germinal"]["candidate_hash"])
    assert candidate_hash in {spec.hash for spec in engine.repository.promoted_falsifiers("finance")}
    first_hash = str(first["receipt"]["receipt_hash"])

    unlinked_flip = engine.submit_verification(_submission(run, claim_hash, snapshot, status="SUPPORTED", token=token, minute=1))
    assert unlinked_flip["accepted"] is False
    assert unlinked_flip["receipt"]["rejection_reason"] == "active_adjudication_requires_supersession"

    superseded = engine.submit_verification(
        _submission(
            run,
            claim_hash,
            snapshot,
            status="SUPPORTED",
            token=token,
            supersedes=first_hash,
            minute=2,
        )
    )
    assert superseded["accepted"] is True
    assert superseded["revocation"]["evasions"] >= 1
    assert superseded["revocation"]["mutations"] >= 1
    assert superseded["revocation"]["promotions"] >= 1
    assert superseded["revocation"]["germinal"] >= 1
    assert candidate_hash not in {spec.hash for spec in engine.repository.promoted_falsifiers("finance")}

    restarted = MiMicusEngine(database, provider=NearMissProvider())
    assert candidate_hash not in {spec.hash for spec in restarted.repository.promoted_falsifiers("finance")}
    active = [row for row in restarted.repository.get_run(run.run_id)["verification_receipts"] if row.get("learning_active")]
    assert len(active) == 1
    assert active[0]["verified_status"] == "SUPPORTED"
