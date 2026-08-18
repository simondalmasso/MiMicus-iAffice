from __future__ import annotations

import json
import sys
import tempfile
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from mimicus.agents.calibration import capability_scope
from mimicus.claims.evidence_bundle import EvidenceInput
from mimicus.claims.models import Claim
from mimicus.coalition.threat_profile import profile_task
from mimicus.falsifiers.spec import FalsifierExecution
from mimicus.orchestration.engine import MiMicusEngine, RunRequest
from mimicus.orchestration.synthesis import synthesize_swarm
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
from mimicus.types import Verdict
from mimicus.verification.models import VerificationSubmission


def _write(root: Path, name: str, payload: dict[str, Any]) -> None:
    (root / name).write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


def _evidence(facts: dict[str, Any], *, cluster: str = "audit-primary") -> list[EvidenceInput]:
    return [
        EvidenceInput(
            origin="audit://order006/structured",
            independence_cluster=cluster,
            content="ORDER-006 structured audit evidence",
            extracted_facts=facts,
            observed_at=datetime(2026, 8, 18, 10, tzinfo=UTC),
        )
    ]


def _numeric(claimed: float = 1200.0) -> dict[str, Any]:
    return {"price": 10.0, "users": 10.0, "price_period": "monthly", "claimed": claimed}


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


class TwoSynthFactory(BuiltinAgentFactory):
    _PHENOTYPES = (
        ("synth-a", frozenset({"synthesize"}), "synth-a-v1"),
        ("synth-b", frozenset({"synthesize"}), "synth-b-v1"),
    )


class ThreeSynthFactory(BuiltinAgentFactory):
    _PHENOTYPES = TwoSynthFactory._PHENOTYPES + (("synth-c", frozenset({"synthesize"}), "synth-c-v1"),)


def _services(database: str, count: int) -> RuntimeServices:
    competence = {name: frozenset({"synthesize"}) for name in ("synth-a", "synth-b", "synth-c")}
    provider = ScriptedProvider(audition_competence=competence)
    repository = Repository(database)
    factory = (TwoSynthFactory if count == 2 else ThreeSynthFactory)(provider.capabilities)
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


def real_microauditions(root: Path) -> dict[str, Any]:
    db = f"sqlite:///{root / 'auditions.db'}"
    incompetent = ScriptedProvider(audition_competence={"numeric-1": frozenset()})
    engine = MiMicusEngine(db, provider=incompetent)
    fp = next(row.fingerprint for row in engine.services.agent_factory.candidates() if row.name == "numeric-1")
    runs = []
    last = None
    for _ in range(3):
        last = engine.run(RunRequest(task="Assess the supplied bundle.", domain="finance", evidence=_evidence(_numeric()), max_agents=1))
        runs.append(last.run_id)
    assert last is not None
    rows = [row for row in last.evidence_provenance["auditions"] if row["capability"] == "numeric"]
    scope = capability_scope("finance", "numeric", "numeric_canary")
    assert rows and rows[0]["provider_executed"] is True and rows[0]["passed"] is False
    assert engine.repository.bankruptcy_state(fp, scope) == "BANKRUPT"
    restarted = MiMicusEngine(db, provider=incompetent)
    persisted = restarted.repository.calibration(fp, scope)
    assert persisted["attempts"] == 3
    after = restarted.run(RunRequest(task="Assess the supplied bundle.", domain="finance", evidence=_evidence(_numeric()), max_agents=1))
    assert fp not in after.coalition["members"]
    competent = MiMicusEngine(f"sqlite:///{root / 'competent.db'}", provider=ScriptedProvider())
    good = competent.run(RunRequest(task="Assess the supplied bundle.", domain="finance", evidence=_evidence(_numeric()), max_agents=1))
    good_rows = [row for row in good.evidence_provenance["auditions"] if row["capability"] == "numeric"]
    assert good_rows and good_rows[0]["provider_executed"] is True and good_rows[0]["passed"] is True
    payload = {
        "pass": True,
        "real_provider_execution": True,
        "incompetent": {"fingerprint": fp, "run_ids": runs, "audition": rows[0], "state": "BANKRUPT"},
        "restart": {"attempts": persisted["attempts"], "excluded_after_restart": fp not in after.coalition["members"]},
        "competent": {"run_id": good.run_id, "audition": good_rows[0], "selected": bool(good.coalition["members"])},
    }
    _write(root, "REAL_MICRO_AUDITIONS.json", payload)
    return payload


def receipt_and_germinal(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    db = f"sqlite:///{root / 'germinal.db'}"
    engine = MiMicusEngine(db)
    verifier_token = "order006-evidence-oracle-token-v1"
    engine.register_verifier_authority(
        verifier_id="oracle:order006-numeric-registry",
        authority_class="deterministic_oracle",
        source_independence_cluster="order006-numeric-registry-v1",
        auth_token=verifier_token,
    )
    run = engine.run(RunRequest(task="Assess the supplied bundle.", domain="finance", evidence=_evidence(_numeric(1248.0)), learn=True))
    assert run.falsifiers and run.falsifiers[0]["verdict"] == "PASS"
    claim = run.final_claims[0]
    observed = datetime(2026, 8, 18, 11, tzinfo=UTC)
    submission = VerificationSubmission(
        run_id=run.run_id,
        claim_hash=claim["claim_hash"],
        verified_status="FALSIFIED",
        authority_class="deterministic_oracle",
        evidence_hashes=tuple(run.evidence_provenance["provider_input_evidence_hashes"]),
        snapshot_hashes=(run.falsifiers[0]["execution_snapshot_hash"],),
        verifier_id="oracle:order006-numeric-registry",
        auth_token=verifier_token,
        observed_at=observed,
        source_independence_cluster="order006-numeric-registry-v1",
    )
    accepted = engine.submit_verification(submission)
    assert accepted["accepted"] is True and accepted["attributions"]
    assert accepted["germinal"] and accepted["germinal"]["germinal_entry_state"] == "GERMINAL_QUARANTINE"
    duplicate = engine.submit_verification(submission.model_copy(update={"observed_at": observed + timedelta(hours=2), "evidence_hashes": ()}))
    assert duplicate["duplicate"] is True
    bad = engine.submit_verification(
        submission.model_copy(
            update={
                "claim_hash": "0" * 64,
                "verifier_id": "oracle:order006-other",
                "source_independence_cluster": "order006-other",
            }
        )
    )
    assert bad["accepted"] is False and bad["receipt"]["rejection_reason"] == "claim_hash_not_bound_to_run"
    restarted = MiMicusEngine(db)
    rerun = restarted.run(RunRequest(task="Assess the supplied bundle.", domain="finance", evidence=_evidence(_numeric(1248.0)), learn=True))
    assert rerun.persistent_falsifiers_reused and rerun.falsifiers[0]["verdict"] == "FAIL"
    fetched = restarted.get_run(run.run_id)
    assert fetched and fetched["verification_receipts"] and fetched["replay_state"]["verified"] is True
    receipt_payload = {
        "pass": True,
        "run_id": run.run_id,
        "claim_hash": claim["claim_hash"],
        "accepted_receipt": accepted["receipt"],
        "attributions": accepted["attributions"],
        "duplicate_same_origin_blocked": duplicate["duplicate"],
        "mismatched_claim_fail_closed": bad["receipt"]["rejection_reason"],
        "restart_receipts": fetched["verification_receipts"],
        "replay_verified": fetched["replay_state"]["verified"],
    }
    germinal_payload = {
        "pass": True,
        "parent_execution": run.falsifiers[0],
        "verified_contradiction": accepted["receipt"],
        "germinal": accepted["germinal"],
        "restart_run_id": rerun.run_id,
        "promoted_reused": rerun.persistent_falsifiers_reused,
        "later_verdict": rerun.falsifiers[0]["verdict"],
        "generated_executable_code": False,
    }
    _write(root, "VERIFICATION_RECEIPTS.json", receipt_payload)
    _write(root, "RUNTIME_GERMINAL_LOOP.json", germinal_payload)
    return receipt_payload, germinal_payload


def market_hierarchy_synthesis_profile(root: Path) -> dict[str, Any]:
    provider = TypedRecordingProvider()
    engine = MiMicusEngine(f"sqlite:///{root / 'market.db'}", provider=provider)
    facts = _numeric() | {"evidence_date": "2026-08-17T00:00:00+00:00", "as_of": "2026-08-18T00:00:00+00:00"}
    market = engine.run(RunRequest(task="Assess this bundle.", domain="research", evidence=_evidence(facts), max_agents=4, depth="deep"))
    bids = market.evidence_provenance["claim_aware_market"]["selected"]
    target_specs = {row["target_claim_hash"]: row["spec_hash"] for row in bids}
    assert len(set(target_specs.values())) >= 2
    assert all(row["target_claim_hashes"] and row["selection_reason"] for row in market.falsifiers)
    market_payload = {
        "pass": True,
        "run_id": market.run_id,
        "claims": market.final_claims,
        "selected_bids": bids,
        "executions": market.falsifiers,
        "distinct_target_specs": len(set(target_specs.values())),
    }
    _write(root, "CLAIM_AWARE_FALSIFIER_MARKET.json", market_payload)

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
    worker_tasks = [task for _name, task in provider.tasks]
    assert hierarchical.morphology == "hierarchical_fanout_fanin"
    assert len({row["subtask_hash"] for row in hierarchical.subtasks}) >= 2
    assert worker_tasks and original_task not in worker_tasks and len(set(worker_tasks)) >= 2
    hierarchy_payload = {
        "pass": True,
        "run_id": hierarchical.run_id,
        "morphology": hierarchical.morphology,
        "subtasks": hierarchical.subtasks,
        "worker_tasks": worker_tasks,
        "assignments": hierarchical.coalition["subtask_assignments"],
        "original_task_replayed_to_workers": original_task in worker_tasks,
    }
    _write(root, "HIERARCHICAL_SUBTASKS.json", hierarchy_payload)

    a = Claim(statement="candidate A", domain="test", probability=0.82, claim_type="factual")
    b = Claim(statement="candidate B", domain="test", probability=0.55, claim_type="factual")
    passed = FalsifierExecution(
        spec_hash="a" * 64,
        verdict=Verdict.PASS,
        execution_snapshot_hash="b" * 64,
        target_claim_hashes=(a.hash,),
        selection_reason="ORDER-006 synthesis probe",
    )
    supported = synthesize_swarm([("fp-a", a, 0.8), ("fp-b", b, 0.4)], [passed], [], budget={}, coverage_complete=True)
    failed = passed.model_copy(update={"verdict": Verdict.FAIL, "execution_snapshot_hash": "c" * 64})
    falsified = synthesize_swarm([("fp-a", a, 0.8), ("fp-b", b, 0.4)], [failed], [], budget={}, coverage_complete=True)
    assert supported.candidate_answer == falsified.candidate_answer == "candidate A"
    assert falsified.epistemic_status == "FALSIFIED"
    assert supported.hash != falsified.hash
    synthesis_payload = {
        "pass": True,
        "supported_decision": supported.model_dump(mode="json") | {"hash": supported.hash},
        "falsified_decision": falsified.model_dump(mode="json") | {"hash": falsified.hash},
        "materially_changed": supported.hash != falsified.hash,
    }
    _write(root, "SWARM_DECISION_SYNTHESIS.json", synthesis_payload)

    p1 = profile_task(
        "Please inspect this bundle.",
        "finance",
        evidence_facts=_numeric(),
        available_capabilities=("numeric", "synthesize"),
        budget_usd=0.0,
        max_concurrency=2,
    )
    p2 = profile_task(
        "Cosmetically different wording with no numeric keyword.",
        "finance",
        evidence_facts=_numeric(),
        available_capabilities=("numeric", "synthesize"),
        budget_usd=0.0,
        max_concurrency=2,
    )
    assert "numeric" in p1.required_capabilities and p1.required_capabilities == p2.required_capabilities
    assert any(row.get("source") == "evidence_schema" for row in p1.signal_provenance)
    profile_payload = {
        "pass": True,
        "first": p1.model_dump(mode="json"),
        "renamed": p2.model_dump(mode="json"),
        "same_required_capabilities": p1.required_capabilities == p2.required_capabilities,
    }
    _write(root, "THREAT_PROFILE_STRUCTURAL.json", profile_payload)
    return {"market": market_payload, "hierarchy": hierarchy_payload, "synthesis": synthesis_payload, "profile": profile_payload}


def all_five(root: Path) -> dict[str, Any]:
    cases: list[tuple[str, list[EvidenceInput]]] = [
        ("solo", _evidence(_numeric())),
        ("paired_verify", []),
        ("parallel_fanout", _evidence(_numeric() | {"evidence_date": "2026-08-17T00:00:00+00:00", "as_of": "2026-08-18T00:00:00+00:00"})),
        (
            "sparse_graph",
            _evidence(
                _numeric()
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
                _numeric()
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
        engine = MiMicusEngine(f"sqlite:///{root / f'morph-{index}.db'}", provider=TypedRecordingProvider())
        result = engine.run(RunRequest(task="Assess the supplied material.", domain="test", evidence=evidence, max_agents=4, depth="deep"))
        assert result.morphology == expected
        observed[expected] = {
            "run_id": result.run_id,
            "members": len(result.coalition["members"]),
            "subtasks": len(result.subtasks),
            "challenge_edges": result.challenge_edge_count,
            "critical_path": result.critical_path_summary,
            "concurrency": result.concurrency_summary,
            "plan_hash": result.plan_hash,
        }
    assert observed["solo"]["members"] == 1
    assert observed["paired_verify"]["members"] == 2 and observed["paired_verify"]["challenge_edges"] >= 1
    assert observed["parallel_fanout"]["members"] == 2 and observed["parallel_fanout"]["challenge_edges"] == 0
    assert observed["sparse_graph"]["members"] >= 3 and observed["sparse_graph"]["challenge_edges"] >= 1
    assert observed["hierarchical_fanout_fanin"]["subtasks"] >= 2
    payload = {"pass": True, "classes": observed, "all_five": sorted(observed)}
    _write(root, "MORPHOLOGY_ALL_FIVE.json", payload)
    return payload


def cofailure(root: Path) -> dict[str, Any]:
    db = f"sqlite:///{root / 'cofailure.db'}"
    engine = MiMicusEngine(db, services=_services(db, 2))
    verifier_token = "order006-evidence-cofailure-token-v1"
    engine.register_verifier_authority(
        verifier_id="order006:cofailure:authority",
        authority_class="trusted_human",
        source_independence_cluster="order006-cofailure-authority",
        auth_token=verifier_token,
    )
    failed_pair: set[str] | None = None
    run_ids: list[str] = []
    for episode in range(5):
        result = engine.run(
            RunRequest(
                task="Assess an underdetermined question.",
                domain="general",
                max_agents=2,
                evidence=_evidence({"context": f"cofailure-{episode}"}),
            )
        )
        run_ids.append(result.run_id)
        pair = {row["contributor_fingerprint"] for row in result.final_claims}
        failed_pair = pair if failed_pair is None else failed_pair
        assert pair == failed_pair and len(pair) == 2
        for claim in result.final_claims:
            verified = engine.submit_verification(
                VerificationSubmission(
                    run_id=result.run_id,
                    claim_hash=claim["claim_hash"],
                    verified_status="FALSIFIED",
                    authority_class="trusted_human",
                    evidence_hashes=tuple(result.evidence_provenance["provider_input_evidence_hashes"]),
                    verifier_id="order006:cofailure:authority",
                    auth_token=verifier_token,
                    observed_at=datetime(2026, 8, 18, 12, episode, tzinfo=UTC),
                    source_independence_cluster="order006-cofailure-authority",
                )
            )
            assert verified["accepted"] is True
    assert failed_pair is not None
    learned = SwarmStateStore(engine.repository.engine).learned_state("general")
    pair_rows = [row for row in learned["pairwise_cofailure"] if {row["agent_a"], row["agent_b"]} == failed_pair]
    assert pair_rows and pair_rows[0]["verified_episodes"] >= 5 and pair_rows[0]["cofailures"] >= 5
    restarted = MiMicusEngine(db, services=_services(db, 3))
    future = restarted.run(RunRequest(task="Assess an underdetermined question.", domain="general", max_agents=2))
    assert "synth-c" in set(future.coalition["names"])
    assert set(future.coalition["members"]) != failed_pair
    payload = {
        "pass": True,
        "verified_episode_run_ids": run_ids,
        "failed_pair": sorted(failed_pair),
        "learned_state": learned,
        "restart_run_id": future.run_id,
        "future_names": future.coalition["names"],
        "future_members": future.coalition["members"],
        "selection_changed_after_restart": set(future.coalition["members"]) != failed_pair,
    }
    _write(root, "COFAILURE_ATTRIBUTION.json", payload)
    return payload


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mimicus-order006-probes-") as directory:
        probe_root = Path(directory)
        auditions = real_microauditions(probe_root)
        receipts, germinal = receipt_and_germinal(probe_root)
        other = market_hierarchy_synthesis_profile(probe_root)
        morphologies = all_five(probe_root)
        learning = cofailure(probe_root)
        for name in (
            "REAL_MICRO_AUDITIONS.json",
            "VERIFICATION_RECEIPTS.json",
            "RUNTIME_GERMINAL_LOOP.json",
            "CLAIM_AWARE_FALSIFIER_MARKET.json",
            "SWARM_DECISION_SYNTHESIS.json",
            "HIERARCHICAL_SUBTASKS.json",
            "COFAILURE_ATTRIBUTION.json",
            "MORPHOLOGY_ALL_FIVE.json",
            "THREAT_PROFILE_STRUCTURAL.json",
        ):
            (output_dir / name).write_text((probe_root / name).read_text(encoding="utf-8"), encoding="utf-8")
    persistence = {
        "pass": True,
        "microaudition_restart": auditions["restart"],
        "receipt_restart_replay_verified": receipts["replay_verified"],
        "germinal_promoted_reused": bool(germinal["promoted_reused"]),
        "cofailure_selection_changed_after_restart": learning["selection_changed_after_restart"],
    }
    _write(output_dir, "PERSISTENCE_RESTART.json", persistence)
    report = {
        "order": "ORDER-006",
        "passed": all(
            [
                auditions["pass"],
                receipts["pass"],
                germinal["pass"],
                other["market"]["pass"],
                other["hierarchy"]["pass"],
                other["synthesis"]["pass"],
                other["profile"]["pass"],
                morphologies["pass"],
                learning["pass"],
                persistence["pass"],
            ]
        ),
    }
    _write(output_dir, "ORDER006_E2E.json", report)
    return report


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("evidence/ORDER-006")
    report = run(output)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
