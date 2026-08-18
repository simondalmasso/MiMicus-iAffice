from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from mimicus.agents.calibration import capability_scope
from mimicus.claims.evidence_bundle import EvidenceInput
from mimicus.claims.models import Claim
from mimicus.orchestration.engine import MiMicusEngine, RunRequest
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
from mimicus.providers.base import ProviderRequest, ProviderResponse
from mimicus.providers.scripted import ScriptedProvider
from mimicus.storage.repository import Repository
from mimicus.storage.swarm_state import SwarmStateStore
from mimicus.verification.models import VerificationSubmission


def _evidence(facts: dict[str, Any], *, cluster: str = "audit-primary") -> list[EvidenceInput]:
    return [
        EvidenceInput(
            origin="audit://structured",
            independence_cluster=cluster,
            content="ORDER-006 structured audit evidence",
            extracted_facts=facts,
            observed_at=datetime(2026, 8, 18, 10, tzinfo=UTC),
        )
    ]


def _numeric_facts(claimed: float = 1200.0) -> dict[str, Any]:
    return {"price": 10.0, "users": 10.0, "price_period": "monthly", "claimed": claimed}


def test_real_microauditions_fail_incompetent_and_persist_bankruptcy(tmp_path: Path) -> None:
    database = f"sqlite:///{tmp_path / 'auditions.db'}"
    incompetent = ScriptedProvider(audition_competence={"numeric-1": frozenset()})
    engine = MiMicusEngine(database, provider=incompetent)
    fingerprint = next(row.fingerprint for row in engine.services.agent_factory.candidates() if row.name == "numeric-1")
    last = None
    for _ in range(3):
        last = engine.run(RunRequest(task="Assess the structured bundle.", domain="finance", evidence=_evidence(_numeric_facts()), max_agents=1))
    assert last is not None
    audition_rows = [row for row in last.evidence_provenance["auditions"] if row["capability"] == "numeric"]
    assert audition_rows and audition_rows[0]["provider_executed"] is True and audition_rows[0]["passed"] is False
    scope = capability_scope("finance", "numeric", "numeric_canary")
    assert engine.repository.bankruptcy_state(fingerprint, scope) == "BANKRUPT"
    assert fingerprint not in last.coalition["members"]
    restarted = MiMicusEngine(database, provider=incompetent)
    assert restarted.repository.calibration(fingerprint, scope)["attempts"] == 3
    again = restarted.run(RunRequest(task="Assess the structured bundle.", domain="finance", evidence=_evidence(_numeric_facts()), max_agents=1))
    assert fingerprint not in again.coalition["members"]

    competent = MiMicusEngine(f"sqlite:///{tmp_path / 'competent.db'}", provider=ScriptedProvider())
    good = competent.run(RunRequest(task="Assess the structured bundle.", domain="finance", evidence=_evidence(_numeric_facts()), max_agents=1))
    good_rows = [row for row in good.evidence_provenance["auditions"] if row["capability"] == "numeric"]
    assert good_rows and good_rows[0]["passed"] is True
    assert good.coalition["members"]


def test_receipt_drives_real_germinal_and_restart_reuses_promoted_falsifier(tmp_path: Path) -> None:
    database = f"sqlite:///{tmp_path / 'germinal.db'}"
    engine = MiMicusEngine(database)
    # Parent tolerance is 5%; 4% error passes parent, while the safe deterministic
    # mutation policy tightens to 2% after a verified false negative.
    result = engine.run(RunRequest(task="Assess the structured bundle.", domain="finance", evidence=_evidence(_numeric_facts(1248.0)), learn=True))
    assert result.falsifiers and result.falsifiers[0]["verdict"] == "PASS"
    claim_hash = result.final_claims[0]["claim_hash"]
    snapshot = result.falsifiers[0]["execution_snapshot_hash"]
    observed = datetime(2026, 8, 18, 11, tzinfo=UTC)
    submission = VerificationSubmission(
        run_id=result.run_id,
        claim_hash=claim_hash,
        verified_status="FALSIFIED",
        authority_class="deterministic_oracle",
        evidence_hashes=tuple(result.evidence_provenance["provider_input_evidence_hashes"]),
        snapshot_hashes=(snapshot,),
        verifier_id="oracle:numeric-registry",
        observed_at=observed,
        source_independence_cluster="numeric-registry-v1",
    )
    verified = engine.submit_verification(submission)
    assert verified["accepted"] is True
    assert verified["attributions"] and verified["attributions"][0]["capability"] == "numeric"
    assert verified["germinal"] is not None
    assert verified["germinal"]["germinal_entry_state"] == "GERMINAL_QUARANTINE"
    assert verified["germinal"]["status"] == "PROMOTE"
    unrelated = engine.calibration.get_capability(result.final_claims[0]["contributor_fingerprint"], "finance", "freshness", "freshness_verified_task")
    assert unrelated.attempts == 0

    duplicate = submission.model_copy(update={"observed_at": observed + timedelta(hours=1), "evidence_hashes": ()})
    repeated = engine.submit_verification(duplicate)
    assert repeated["duplicate"] is True
    invalid = engine.submit_verification(
        submission.model_copy(
            update={
                "claim_hash": "0" * 64,
                "verifier_id": "oracle:other",
                "source_independence_cluster": "other-cluster",
            }
        )
    )
    assert invalid["accepted"] is False
    assert invalid["receipt"]["rejection_reason"] == "claim_hash_not_bound_to_run"

    restarted = MiMicusEngine(database)
    rerun = restarted.run(RunRequest(task="Assess the structured bundle.", domain="finance", evidence=_evidence(_numeric_facts(1248.0)), learn=True))
    assert rerun.persistent_falsifiers_reused
    assert rerun.falsifiers and rerun.falsifiers[0]["verdict"] == "FAIL"
    fetched = restarted.get_run(result.run_id)
    assert fetched is not None and fetched["verification_receipts"]


class TypedRecordingProvider(ScriptedProvider):
    def __init__(self) -> None:
        super().__init__()
        self.tasks: list[tuple[str, str]] = []

    async def generate_request_async(self, request: ProviderRequest) -> ProviderResponse:
        self.tasks.append((request.phenotype, request.task))
        response = await super().generate_request_async(request)
        claim_type = {
            "numeric-1": "numeric",
            "source-1": "temporal",
            "critic-1": "factual",
            "counterexample-1": "factual",
            "synth-1": "other",
        }.get(request.phenotype, "other")
        probability = {
            "numeric-1": 0.52,
            "source-1": 0.88,
            "critic-1": 0.61,
            "counterexample-1": 0.73,
        }.get(request.phenotype, 0.67)
        claim = Claim(
            statement=f"{request.phenotype}:{request.task}",
            domain=request.domain,
            probability=probability,
            claim_type=claim_type,  # type: ignore[arg-type]
            evidence_refs=list(response.claim.evidence_refs),
        )
        return replace(response, claim=claim)


def test_claim_aware_runtime_market_and_real_hierarchical_subtasks(tmp_path: Path) -> None:
    provider = TypedRecordingProvider()
    engine = MiMicusEngine(f"sqlite:///{tmp_path / 'market.db'}", provider=provider)
    facts = _numeric_facts() | {
        "evidence_date": "2026-08-17T00:00:00+00:00",
        "as_of": "2026-08-18T00:00:00+00:00",
    }
    market = engine.run(RunRequest(task="Assess this bundle.", domain="research", evidence=_evidence(facts), max_agents=4, depth="deep"))
    bids = market.evidence_provenance["claim_aware_market"]["selected"]
    targets = {row["target_claim_hash"]: row["spec_hash"] for row in bids}
    assert len(set(targets.values())) >= 2
    assert all(row["selection_reason"].startswith("claim-aware") for row in bids)
    assert all(row["target_claim_hashes"] and row["selection_reason"] for row in market.falsifiers)

    provider.tasks.clear()
    full = facts | {
        "clusters": ["primary-a", "primary-b"],
        "texts": ["alpha", "beta"],
        "claim_figure": 42,
        "evidence_spans": [{"span_id": "s1", "supported_figures": [42], "material_support": True}],
        "absence_key": "missing-target",
        "registry": {},
        "registry_snapshot_hash": "d" * 64,
    }
    original_task = "Evaluate the supplied structured material."
    hierarchical = engine.run(RunRequest(task=original_task, domain="research", evidence=_evidence(full), max_agents=4, depth="deep"))
    assert hierarchical.morphology == "hierarchical_fanout_fanin"
    hashes = [row["subtask_hash"] for row in hierarchical.subtasks]
    objectives = [row["objective"] for row in hierarchical.subtasks]
    assert len(set(hashes)) >= 2 and len(set(objectives)) >= 2
    worker_tasks = [task for _phenotype, task in provider.tasks]
    assert worker_tasks and original_task not in worker_tasks
    assert len(set(worker_tasks)) >= 2
    assert hierarchical.coalition["subtask_assignments"]


def test_all_five_morphologies_are_runtime_reachable(tmp_path: Path) -> None:
    cases: list[tuple[str, list[EvidenceInput]]] = [
        ("solo", _evidence(_numeric_facts())),
        ("paired_verify", []),
        (
            "parallel_fanout",
            _evidence(
                _numeric_facts()
                | {
                    "evidence_date": "2026-08-17T00:00:00+00:00",
                    "as_of": "2026-08-18T00:00:00+00:00",
                }
            ),
        ),
        (
            "sparse_graph",
            _evidence(
                _numeric_facts()
                | {
                    "evidence_date": "2026-08-17T00:00:00+00:00",
                    "as_of": "2026-08-18T00:00:00+00:00",
                    "absence_key": "x",
                    "registry": {},
                    "registry_snapshot_hash": "e" * 64,
                }
            ),
        ),
        (
            "hierarchical_fanout_fanin",
            _evidence(
                _numeric_facts()
                | {
                    "evidence_date": "2026-08-17T00:00:00+00:00",
                    "as_of": "2026-08-18T00:00:00+00:00",
                    "clusters": ["a", "b"],
                    "texts": ["a", "b"],
                    "claim_figure": 42,
                    "evidence_spans": [{"span_id": "s", "supported_figures": [42], "material_support": True}],
                    "absence_key": "x",
                    "registry": {},
                    "registry_snapshot_hash": "f" * 64,
                }
            ),
        ),
    ]
    observed: dict[str, Any] = {}
    for index, (expected, evidence) in enumerate(cases):
        provider = TypedRecordingProvider()
        engine = MiMicusEngine(f"sqlite:///{tmp_path / f'morph-{index}.db'}", provider=provider)
        result = engine.run(RunRequest(task="Assess the supplied material.", domain="test", evidence=evidence, max_agents=4, depth="deep"))
        observed[expected] = result
        assert result.morphology == expected
    assert len(observed["solo"].coalition["members"]) == 1
    assert len(observed["paired_verify"].coalition["members"]) == 2
    assert observed["paired_verify"].challenge_edge_count >= 1
    assert len(observed["parallel_fanout"].coalition["members"]) == 2
    assert observed["parallel_fanout"].challenge_edge_count == 0
    assert len(observed["sparse_graph"].coalition["members"]) >= 3
    assert observed["sparse_graph"].challenge_edge_count >= 1
    assert len(observed["hierarchical_fanout_fanin"].subtasks) >= 2


class TwoSynthFactory(BuiltinAgentFactory):
    _PHENOTYPES = (
        ("synth-a", frozenset({"synthesize"}), "synth-a-v1"),
        ("synth-b", frozenset({"synthesize"}), "synth-b-v1"),
    )


class ThreeSynthFactory(BuiltinAgentFactory):
    _PHENOTYPES = TwoSynthFactory._PHENOTYPES + (("synth-c", frozenset({"synthesize"}), "synth-c-v1"),)


def _services(database: str, names: int) -> RuntimeServices:
    competence = {name: frozenset({"synthesize"}) for name in ("synth-a", "synth-b", "synth-c")}
    provider = ScriptedProvider(audition_competence=competence)
    repository = Repository(database)
    factory = (TwoSynthFactory if names == 2 else ThreeSynthFactory)(provider.capabilities)
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


def test_verified_cofailure_and_marginal_value_change_future_coalition_after_restart(tmp_path: Path) -> None:
    database = f"sqlite:///{tmp_path / 'cofailure.db'}"
    engine = MiMicusEngine(database, services=_services(database, 2))
    failed_pair: set[str] | None = None
    for episode in range(5):
        result = engine.run(RunRequest(task="Assess an underdetermined question.", domain="general", max_agents=2))
        pair = {row["contributor_fingerprint"] for row in result.final_claims}
        failed_pair = pair if failed_pair is None else failed_pair
        assert pair == failed_pair and len(pair) == 2
        for index, claim in enumerate(result.final_claims):
            receipt = VerificationSubmission(
                run_id=result.run_id,
                claim_hash=claim["claim_hash"],
                verified_status="FALSIFIED",
                authority_class="trusted_human",
                verifier_id=f"verifier:{episode}:{index}",
                observed_at=datetime(2026, 8, 18, 12, episode, tzinfo=UTC),
                source_independence_cluster=f"verified-episode-{episode}-{index}",
            )
            assert engine.submit_verification(receipt)["accepted"] is True
    assert failed_pair is not None
    learned = SwarmStateStore(engine.repository.engine).learned_state("general")
    pair_rows = [row for row in learned["pairwise_cofailure"] if {row["agent_a"], row["agent_b"]} == failed_pair]
    assert pair_rows and pair_rows[0]["verified_episodes"] >= 5 and pair_rows[0]["cofailures"] >= 5
    assert pair_rows[0]["confidence"] > 0.0

    restarted = MiMicusEngine(database, services=_services(database, 3))
    future = restarted.run(RunRequest(task="Assess an underdetermined question.", domain="general", max_agents=2))
    names = set(future.coalition["names"])
    assert "synth-c" in names
    assert set(future.coalition["members"]) != failed_pair
