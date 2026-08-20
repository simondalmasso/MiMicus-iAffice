from __future__ import annotations

import copy
from datetime import UTC, datetime

from sqlalchemy import update

from mimicus.canonical import canonical_json, sha256_obj
from mimicus.claims.evidence_bundle import EvidenceInput
from mimicus.claims.models import Claim, NumericAssertion
from mimicus.falsifiers.builtins import builtin_specs
from mimicus.falsifiers.primitives import execute_claim_bound
from mimicus.orchestration.communication import ChallengeRequest, ChallengeResponse
from mimicus.orchestration.engine import MiMicusEngine, RunRequest
from mimicus.orchestration.semantic_replay import semantic_replay
from mimicus.plugins.services import (
    BuiltinAgentFactory,
    ImmuneMemoryService,
    LedgerTelemetryService,
    LocalSandboxService,
    MimicusCoalitionService,
    RepositoryStorage,
    RuntimeServices,
    SafeFalsifierService,
    SparseCommunicationService,
)
from mimicus.providers.scripted import ScriptedProvider
from mimicus.storage.models import RunRow
from mimicus.storage.repository import Repository
from mimicus.storage.swarm_state import SwarmStateStore
from mimicus.types import ClaimStatus, Verdict
from mimicus.verification.models import VerificationSubmission


class TwoSynthFactory(BuiltinAgentFactory):
    _PHENOTYPES = (
        ("synth-a", frozenset({"synthesize"}), "synth-a-v1"),
        ("synth-b", frozenset({"synthesize"}), "synth-b-v1"),
    )


class NoProgressProvider(ScriptedProvider):
    async def challenge_async(self, request: ChallengeRequest) -> ChallengeResponse:
        self.challenge_calls += 1
        return ChallengeResponse(
            disposition="unchanged",
            revised_probability=0.5,
            revised_status=ClaimStatus.PROPOSED,
            new_evidence_refs=list(request.evidence_refs),
            rationale_summary="deterministic no-progress challenge",
            provider_call_id=f"no-progress-{self.challenge_calls}",
            cost=0.0,
            usage={"simulated": True, "calls": 1, "monetary_cost_status": "KNOWN", "monetary_cost_usd": 0.0},
        )


def _services(database: str, provider: ScriptedProvider | None = None) -> RuntimeServices:
    provider = provider or ScriptedProvider(
        audition_competence={
            "synth-a": frozenset({"synthesize"}),
            "synth-b": frozenset({"synthesize"}),
        }
    )
    repository = Repository(database)
    factory = TwoSynthFactory(provider.capabilities)
    return RuntimeServices(
        storage=RepositoryStorage(repository),
        provider=provider,
        agent_factory=factory,
        falsifiers=SafeFalsifierService(),
        memory=ImmuneMemoryService(repository),
        coalition=MimicusCoalitionService(),
        communication=SparseCommunicationService(),
        sandbox=LocalSandboxService(),
        telemetry=LedgerTelemetryService(),
    )


def _evidence(label: str = "runtime") -> EvidenceInput:
    return EvidenceInput(
        origin=f"order008://{label}",
        independence_cluster=f"order008-{label}",
        content="ORDER-008 executable runtime evidence",
        extracted_facts={"context": label},
    )


def _selected_claim(run) -> dict[str, object]:
    selected = set(run.swarm_decision["selected_claim_hashes"])
    assert selected
    return next(row for row in run.final_claims if row["claim_hash"] in selected)


def _verification(
    run,
    claim: dict[str, object],
    *,
    verifier_id: str,
    cluster: str,
    token: str,
    status: str = "SUPPORTED",
    supersedes: str | None = None,
    minute: int = 0,
) -> VerificationSubmission:
    refs = tuple(str(value) for value in claim.get("evidence_refs", []))
    if not refs:
        refs = tuple(str(value) for value in run.evidence_provenance["provider_input_evidence_hashes"])
    return VerificationSubmission(
        run_id=run.run_id,
        claim_hash=str(claim["claim_hash"]),
        verified_status=status,
        authority_class="deterministic_oracle",
        evidence_hashes=refs,
        verifier_id=verifier_id,
        auth_token=token,
        observed_at=datetime(2026, 8, 20, 12, minute, tzinfo=UTC),
        source_independence_cluster=cluster,
        supersedes_receipt_hash=supersedes,
    )


def test_f038_claim_bound_numeric_snapshot_changes_with_exact_assertion() -> None:
    spec = builtin_specs("finance")["F1"]
    context = {"price": 100.0, "users": 12.0, "price_period": "annual"}
    projection_hash = sha256_obj({"order008": "same-evidence"})
    claim_1200 = Claim(
        statement="annual amount is 1200",
        domain="finance",
        probability=0.8,
        claim_type="numeric",
        assertion=NumericAssertion(asserted_value=1200.0),
        evidence_refs=[projection_hash],
    )
    claim_1300 = claim_1200.model_copy(
        update={
            "statement": "annual amount is 1300",
            "assertion": NumericAssertion(asserted_value=1300.0),
        }
    )
    passed = execute_claim_bound(
        spec,
        claim_1200,
        context,
        evidence_projection_hashes=(projection_hash,),
        selection_reason="ORDER-008 F038 kill",
    )
    failed = execute_claim_bound(
        spec,
        claim_1300,
        context,
        evidence_projection_hashes=(projection_hash,),
        selection_reason="ORDER-008 F038 kill",
    )
    assert passed.verdict == Verdict.PASS
    assert failed.verdict == Verdict.FAIL
    assert passed.execution_snapshot_hash != failed.execution_snapshot_hash
    assert passed.evidence["target_claim_identity_hash"] == claim_1200.identity_hash
    assert failed.evidence["target_claim_identity_hash"] == claim_1300.identity_hash
    assert passed.evidence["tested_assertion_hash"] != failed.evidence["tested_assertion_hash"]
    assert passed.evidence["evidence_projection_hashes"] == failed.evidence["evidence_projection_hashes"] == (projection_hash,)


def test_f042_verified_removal_is_selected_claim_scoped_and_revocation_safe(tmp_path) -> None:
    database = f"sqlite:///{tmp_path / 'f042.db'}"
    engine = MiMicusEngine(database, services=_services(database))
    run = engine.run(
        RunRequest(
            task="Assess an underdetermined question.",
            domain="general",
            source_mode="runtime",
            evidence=[_evidence("f042")],
            max_agents=2,
            depth="deep",
            learn=True,
        )
    )
    assert run.morphology == "paired_verify"
    assert len(run.final_claims) == 2
    selected = _selected_claim(run)
    selected_fp = str(selected["contributor_fingerprint"])
    unrelated = next(row for row in run.final_claims if row["contributor_fingerprint"] != selected_fp)
    unrelated_fp = str(unrelated["contributor_fingerprint"])

    token = "order008-f042-authority-token-v1"
    verifier_id = "oracle:order008-f042"
    cluster = "order008-f042-authority"
    engine.register_verifier_authority(
        verifier_id=verifier_id,
        authority_class="deterministic_oracle",
        source_independence_cluster=cluster,
        auth_token=token,
    )
    verified = engine.submit_verification(
        _verification(
            run,
            selected,
            verifier_id=verifier_id,
            cluster=cluster,
            token=token,
        )
    )
    assert verified["accepted"] is True
    removals = verified["removal_attributions"]
    assert removals
    assert {row["fingerprint"] for row in removals} == {selected_fp}
    assert unrelated_fp not in {row["fingerprint"] for row in removals}
    assert all(row["method"] == "production_decision_leave_one_out_v2" for row in removals)
    assert all(row["decision_before_hash"] and row["decision_without_hash"] for row in removals)
    assert all(row["decision_before_hash"] != row["decision_without_hash"] for row in removals)
    assert all(set(row["verified_scope"]) == {str(selected["claim_hash"])} for row in removals)

    first_hash = str(verified["receipt"]["receipt_hash"])
    flipped = engine.submit_verification(
        _verification(
            run,
            selected,
            verifier_id=verifier_id,
            cluster=cluster,
            token=token,
            status="FALSIFIED",
            supersedes=first_hash,
            minute=1,
        )
    )
    assert flipped["accepted"] is True
    assert flipped["revocation"]["removals"] >= 1
    active_removals = SwarmStateStore(engine.repository.engine).learned_state("general")["removal_attributions"]
    assert all(row["receipt_hash"] != first_hash for row in active_removals)


def test_f043_runtime_learning_memory_restart_revocation_and_no_progress(tmp_path) -> None:
    database = f"sqlite:///{tmp_path / 'f043.db'}"
    engine = MiMicusEngine(database, provider=ScriptedProvider())
    token = "order008-f043-authority-token-v1"
    verifier_id = "oracle:order008-f043"
    cluster = "order008-f043-authority"
    engine.register_verifier_authority(
        verifier_id=verifier_id,
        authority_class="deterministic_oracle",
        source_independence_cluster=cluster,
        auth_token=token,
    )

    inert = engine.run(
        RunRequest(
            task="Answer only from the runtime evidence.",
            domain="general",
            source_mode="runtime",
            evidence=[_evidence("f043-inert")],
            max_agents=1,
            learn=False,
        )
    )
    inert_claim = _selected_claim(inert)
    inert_verified = engine.submit_verification(
        _verification(
            inert,
            inert_claim,
            verifier_id=verifier_id,
            cluster=cluster,
            token=token,
        )
    )
    assert inert_verified["accepted"] is True
    assert inert_verified["learning_enabled_for_run"] is False
    assert inert_verified["attributions"] == []
    assert inert_verified["removal_attributions"] == []
    assert inert_verified["memory_changes"] == []
    inert_learning = SwarmStateStore(engine.repository.engine).learned_state("general")
    assert inert_learning["pairwise_cofailure"] == []
    assert inert_learning["marginal_value"] == []
    assert inert_learning["removal_attributions"] == []

    learning = engine.run(
        RunRequest(
            task="Answer only from the runtime evidence.",
            domain="general",
            source_mode="runtime",
            evidence=[_evidence("f043-learning")],
            max_agents=1,
            learn=True,
        )
    )
    learning_claim = _selected_claim(learning)
    learned = engine.submit_verification(
        _verification(
            learning,
            learning_claim,
            verifier_id=verifier_id,
            cluster=cluster,
            token=token,
            minute=2,
        )
    )
    assert learned["accepted"] is True
    assert learned["learning_enabled_for_run"] is True
    assert learned["attributions"]
    assert learned["memory_changes"]
    memory_id = str(learned["memory_changes"][0]["memory_id"])

    restarted = MiMicusEngine(database, provider=ScriptedProvider())
    reused = restarted.run(
        RunRequest(
            task="Use prior verified memory if eligible.",
            domain="general",
            source_mode="runtime",
            evidence=[_evidence("f043-reuse")],
            max_agents=1,
            learn=False,
        )
    )
    assert memory_id in reused.persistent_memory_reused
    assert reused.progress
    persisted = restarted.repository.inspect_state(reused.run_id)
    assert persisted["progress"]

    learned_hash = str(learned["receipt"]["receipt_hash"])
    revoked = restarted.submit_verification(
        _verification(
            learning,
            learning_claim,
            verifier_id=verifier_id,
            cluster=cluster,
            token=token,
            status="FALSIFIED",
            supersedes=learned_hash,
            minute=3,
        )
    )
    assert revoked["accepted"] is True
    assert revoked["revocation"]["memory"] >= 1

    restarted_again = MiMicusEngine(database, provider=ScriptedProvider())
    after_revocation = restarted_again.run(
        RunRequest(
            task="Do not reuse revoked memory.",
            domain="general",
            source_mode="runtime",
            evidence=[_evidence("f043-after-revoke")],
            max_agents=1,
            learn=False,
        )
    )
    assert memory_id not in after_revocation.persistent_memory_reused

    progress_db = f"sqlite:///{tmp_path / 'f043-progress.db'}"
    no_progress_provider = NoProgressProvider(
        audition_competence={
            "synth-a": frozenset({"synthesize"}),
            "synth-b": frozenset({"synthesize"}),
        }
    )
    progress_engine = MiMicusEngine(progress_db, services=_services(progress_db, no_progress_provider))
    bounded = progress_engine.run(
        RunRequest(
            task="Assess an underdetermined question.",
            domain="general",
            source_mode="runtime",
            evidence=[_evidence("f043-progress")],
            max_agents=2,
            learn=False,
        )
    )
    communications = bounded.persistent_state["communications"]
    assert communications
    assert max(int(row["round"]) for row in communications) <= 3
    assert any(row["step"] == "replan" and row["progress"] is False for row in bounded.progress)
    assert bounded.status == "inconclusive"


def test_f044_semantic_reexecution_tamper_and_nonreplayable_truth(tmp_path) -> None:
    database = f"sqlite:///{tmp_path / 'f044.db'}"
    engine = MiMicusEngine(database, provider=ScriptedProvider())
    run = engine.run(
        RunRequest(
            task="Audit the numeric runtime evidence.",
            domain="finance",
            source_mode="runtime",
            evidence=[
                EvidenceInput(
                    origin="order008://f044",
                    independence_cluster="order008-f044",
                    content="numeric runtime evidence",
                    extracted_facts={"price": 100.0, "users": 12.0, "price_period": "annual", "claimed": 1200.0},
                )
            ],
            max_agents=1,
            depth="deep",
            learn=False,
        )
    )
    replayed = semantic_replay(engine.repository, run.run_id)
    assert replayed["verified"] is True
    assert replayed["integrity_verified"] is True
    assert replayed["semantic_reexecution_verified"] is True
    assert replayed["claim_identity_verified"] is True
    assert replayed["falsifier_reexecution_verified"] is True
    assert replayed["decision_reexecution_verified"] is True
    assert replayed["plan_contract_verified"] is True

    persisted = engine.repository.get_run(run.run_id)
    assert persisted is not None
    tampered = copy.deepcopy(persisted)
    tampered["semantic_replay"]["input_material"]["task"] = "tampered semantic task"
    with engine.repository.engine.begin() as connection:
        connection.execute(
            update(RunRow)
            .where(RunRow.run_id == run.run_id)
            .values(result_json=canonical_json(tampered))
        )
    detected = semantic_replay(engine.repository, run.run_id)
    assert detected["verified"] is False
    assert detected["integrity_verified"] is True
    assert detected["semantic_reexecution_verified"] is False
    assert detected["status"] == "SEMANTIC_INPUT_TAMPERED"

    nondeterministic_db = f"sqlite:///{tmp_path / 'f044-live.db'}"
    nondeterministic = MiMicusEngine(
        nondeterministic_db,
        provider=ScriptedProvider(provider_id="nondeterministic-provider", model_id="live-like"),
    )
    live_run = nondeterministic.run(
        RunRequest(
            task="Assess runtime evidence without claiming exact provider replay.",
            domain="general",
            source_mode="runtime",
            evidence=[_evidence("f044-live")],
            max_agents=1,
            learn=False,
        )
    )
    live_replay = semantic_replay(nondeterministic.repository, live_run.run_id)
    assert live_replay["integrity_verified"] is True
    assert live_replay["semantic_reexecution_verified"] is False
    assert live_replay["status"] == "INTEGRITY_VERIFIED_PROVIDER_NOT_SEMANTICALLY_REPLAYABLE"
