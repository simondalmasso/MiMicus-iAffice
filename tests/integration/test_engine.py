from __future__ import annotations

from pathlib import Path

from mimicus.orchestration.engine import MiMicusEngine, RunRequest


def test_full_flow_and_persistence(tmp_path: Path) -> None:
    engine = MiMicusEngine(f"sqlite:///{tmp_path / 'run.db'}", plugin_hashes=["a" * 64])
    result = engine.run(RunRequest(task="K3 TAM 12x mismatch", domain="finance", learn=True))
    assert result.status == "answered"
    assert result.replay_verified
    assert result.memory_changes[0]["status"] == "shared_verified"
    required = [
        "run_started",
        "threat_profiled",
        "agent_auditioned",
        "coalition_selected",
        "claim_proposed",
        "falsifier_selected",
        "falsifier_executed",
        "claim_updated",
        "final_verified",
        "memory_promoted",
        "run_completed",
    ]
    for event_type in required:
        assert event_type in result.event_types
    fetched = engine.get_run(result.run_id)
    assert fetched is not None
    assert fetched["replay_state"]["verified"] is True
    assert len(fetched["events"]) == len(result.event_types)


def test_five_safe_scenarios(tmp_path: Path) -> None:
    engine = MiMicusEngine(f"sqlite:///{tmp_path / 'scenarios.db'}")
    tasks = [
        "K3 TAM 12x mismatch",
        "source echo same origin citation",
        "freshness stale current evidence",
        "citation figure entailment mismatch",
        "absence counterexample none exist",
    ]
    expected = [
        "numeric_invariant",
        "source_independence",
        "freshness",
        "citation_entailment",
        "counterexample_search",
    ]
    for task, primitive in zip(tasks, expected, strict=True):
        result = engine.run(RunRequest(task=task, domain="test"))
        assert result.falsifiers
        assert result.falsifiers[0]["verdict"] == "FAIL"
        assert result.status == "answered"
        assert result.falsifiers[0]["primitive"] == primitive


def test_budget_exhaustion_is_inconclusive(tmp_path: Path) -> None:
    engine = MiMicusEngine(f"sqlite:///{tmp_path / 'budget.db'}")
    fixture = {"claim_statement": "x", "claim_type": "numeric", "price": 1, "users": 1, "claimed": 10}
    result = engine.run(
        RunRequest(task="ambiguous prose only", fixture=fixture, scenario="general", budget_usd=0.0)
    )
    assert result.status == "inconclusive"
    assert result.answer.startswith("INCONCLUSIVE")
