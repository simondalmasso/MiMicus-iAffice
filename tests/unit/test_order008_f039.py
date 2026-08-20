from __future__ import annotations

from mimicus.canonical import sha256_obj
from mimicus.claims.evidence_bundle import EvidenceInput
from mimicus.claims.models import Claim, NumericAssertion
from mimicus.falsifiers.spec import FalsifierExecution
from mimicus.orchestration.engine import MiMicusEngine, RunRequest
from mimicus.orchestration.production_synthesis import synthesize_production
from mimicus.types import Verdict


def _hierarchy_evidence() -> EvidenceInput:
    registry: dict[str, object] = {}
    return EvidenceInput(
        origin="order008://f039-kill",
        independence_cluster="f039-a",
        content="structured evidence for all required hierarchical predicates",
        extracted_facts={
            "price": 100,
            "users": 12,
            "claimed": 1200,
            "price_period": "annual",
            "evidence_date": "2026-08-19T00:00:00+00:00",
            "as_of": "2026-08-20T00:00:00+00:00",
            "clusters": ["f039-a", "f039-b"],
            "texts": ["independent alpha source", "independent beta source"],
            "claim_figure": "1200",
            "evidence_spans": [{"span_id": "s1", "supported_figures": ["1200"], "material_support": True}],
            "absence_key": "missing-prerequisite",
            "registry": registry,
            "registry_snapshot_hash": sha256_obj(registry),
        },
    )


def _execution(claim: Claim, *, verdict: Verdict, marker: str) -> FalsifierExecution:
    return FalsifierExecution(
        spec_hash=marker * 64,
        verdict=verdict,
        execution_snapshot_hash=("f" if marker != "f" else "e") * 64,
        target_claim_hashes=(claim.identity_hash,),
    )


def test_six_required_subtasks_compose_supported_runtime(tmp_path) -> None:
    engine = MiMicusEngine(f"sqlite:///{tmp_path / 'f039-supported.db'}")
    run = engine.run(
        RunRequest(
            task="Resolve every required audit predicate.",
            domain="research",
            source_mode="runtime",
            evidence=[_hierarchy_evidence()],
            depth="deep",
            max_agents=4,
            max_concurrency=4,
        )
    )
    assert run.morphology == "hierarchical_fanout_fanin"
    required = set(run.hierarchy_execution["required_subtasks"])
    assert len(required) == 6
    assert run.hierarchy_execution["complete"] is True
    assert run.swarm_decision["epistemic_status"] == "SUPPORTED", run.swarm_decision
    fan_in = run.swarm_decision["hierarchical_fan_in"]
    assert fan_in is not None
    assert fan_in["status"] == "SUPPORTED"
    assert len(fan_in["subtask_decisions"]) == 6
    assert {row["subtask_hash"] for row in fan_in["subtask_decisions"]} == required
    assert {row["status"] for row in fan_in["subtask_decisions"]} == {"SUPPORTED"}
    assert len(fan_in["provenance_identities"]) == 6
    assert set(fan_in["provenance_identities"]) <= set(run.swarm_decision["provenance_hashes"])
    assert required <= set(run.swarm_decision["provenance_hashes"])
    assert len(fan_in["falsifier_snapshot_hashes"]) >= 6
    for row in fan_in["subtask_decisions"]:
        assert row["claims"]
        assert all(claim["statement"] in run.swarm_decision["candidate_answer"] for claim in row["claims"])


def test_one_required_subtask_unresolved_forces_inconclusive(tmp_path) -> None:
    run = MiMicusEngine(f"sqlite:///{tmp_path / 'f039-unresolved.db'}").run(
        RunRequest(
            task="Resolve every required audit predicate.",
            domain="research",
            source_mode="runtime",
            evidence=[_hierarchy_evidence()],
            depth="deep",
            max_agents=3,
            max_concurrency=3,
        )
    )
    assert run.morphology == "hierarchical_fanout_fanin"
    assert run.hierarchy_execution["unresolved_subtasks"]
    assert run.swarm_decision["epistemic_status"] == "INCONCLUSIVE"
    fan_in = run.swarm_decision["hierarchical_fan_in"]
    assert fan_in["unresolved_subtasks"]


def test_conflict_is_scoped_to_same_subtask_only() -> None:
    same = "a" * 64
    a = Claim(statement="value is ten", domain="test", probability=0.9, claim_type="numeric", assertion=NumericAssertion(asserted_value=10))
    b = Claim(statement="value is eleven", domain="test", probability=0.9, claim_type="numeric", assertion=NumericAssertion(asserted_value=11))
    conflict = synthesize_production(
        [("fa", a, 0.9, same), ("fb", b, 0.9, same)],
        [_execution(a, verdict=Verdict.PASS, marker="1"), _execution(b, verdict=Verdict.PASS, marker="2")],
        [],
        budget={},
        coverage_complete=True,
        morphology="hierarchical_fanout_fanin",
        subtasks=[{"subtask_hash": same, "dependency_group": "g"}],
        hierarchy_execution={"required_subtasks": [same], "unresolved_subtasks": []},
    )
    assert conflict.epistemic_status == "INCONCLUSIVE"
    assert any(row.get("kind") == "same_subtask_conflict" for row in conflict.unresolved_disagreements)

    left = "b" * 64
    right = "c" * 64
    independent = synthesize_production(
        [("fa", a, 0.9, left), ("fb", b, 0.9, right)],
        [_execution(a, verdict=Verdict.PASS, marker="3"), _execution(b, verdict=Verdict.PASS, marker="4")],
        [],
        budget={},
        coverage_complete=True,
        morphology="hierarchical_fanout_fanin",
        subtasks=[
            {"subtask_hash": left, "dependency_group": "left"},
            {"subtask_hash": right, "dependency_group": "right"},
        ],
        hierarchy_execution={"required_subtasks": [left, right], "unresolved_subtasks": []},
    )
    assert independent.epistemic_status == "SUPPORTED"
    assert not any(row.get("kind") == "same_subtask_conflict" for row in independent.unresolved_disagreements)
    assert set(independent.hierarchical_fan_in.provenance_identities) == {a.identity_hash, b.identity_hash}  # type: ignore[union-attr]


def test_decisive_required_falsification_changes_composite() -> None:
    left = "d" * 64
    right = "e" * 64
    a = Claim(statement="predicate A", domain="test", probability=0.9, claim_type="numeric", assertion=NumericAssertion(asserted_value=10))
    b = Claim(statement="predicate B", domain="test", probability=0.9, claim_type="numeric", assertion=NumericAssertion(asserted_value=11))
    decision = synthesize_production(
        [("fa", a, 0.9, left), ("fb", b, 0.9, right)],
        [_execution(a, verdict=Verdict.PASS, marker="5"), _execution(b, verdict=Verdict.FAIL, marker="6")],
        [],
        budget={},
        coverage_complete=True,
        morphology="hierarchical_fanout_fanin",
        subtasks=[
            {"subtask_hash": left, "dependency_group": "left"},
            {"subtask_hash": right, "dependency_group": "right"},
        ],
        hierarchy_execution={"required_subtasks": [left, right], "unresolved_subtasks": []},
    )
    assert decision.epistemic_status == "FALSIFIED"
    assert decision.hierarchical_fan_in is not None
    assert decision.hierarchical_fan_in.falsified_subtasks == (right,)
