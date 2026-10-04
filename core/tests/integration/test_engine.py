from __future__ import annotations

from pathlib import Path

from mimicus.orchestration.engine import MiMicusEngine, RunRequest


def _tam_fixture() -> dict[str, object]:
    return {"claim_statement": "TAM", "claim_type": "numeric", "price": 10.0, "users": 100.0, "price_period": "monthly", "claimed": 1000.0}


def test_full_flow_and_persistence(tmp_path: Path) -> None:
    engine = MiMicusEngine(f"sqlite:///{tmp_path / 'run.db'}", plugin_hashes=["a" * 64])
    result = engine.run(RunRequest(task="K3 TAM 12x mismatch", domain="finance", scenario="tam_12x", source_mode="fixture", fixture=_tam_fixture(), learn=True))
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
    cases = [
        ("K3 TAM 12x mismatch", "tam_12x", _tam_fixture(), "numeric_invariant"),
        (
            "source echo same origin citation",
            "echo_chamber",
            {"claim_statement": "sources", "claim_type": "factual", "clusters": ["wire", "wire"], "texts": ["same", "same"]},
            "source_independence",
        ),
        (
            "freshness stale current evidence",
            "freshness",
            {"claim_statement": "fresh", "claim_type": "temporal", "evidence_date": "2025-01-01T00:00:00+00:00", "as_of": "2026-08-17T00:00:00+00:00"},
            "freshness",
        ),
        (
            "citation figure entailment mismatch",
            "citation_entailment",
            {"claim_statement": "figure", "claim_type": "numeric", "claim_figure": 42, "evidence_spans": [{"span_id": "e1", "supported_figures": [41], "material_support": True}]},
            "citation_entailment",
        ),
        (
            "absence counterexample none exist",
            "counterexample",
            {"claim_statement": "absence", "claim_type": "factual", "absence_key": "target", "registry": {"target": {"id": "known"}}, "registry_snapshot_hash": "b" * 64},
            "counterexample_search",
        ),
    ]
    for task, scenario, fixture, primitive in cases:
        result = engine.run(RunRequest(task=task, domain="test", scenario=scenario, source_mode="fixture", fixture=fixture))
        assert result.falsifiers
        assert result.falsifiers[0]["verdict"] == "FAIL"
        assert result.status == "answered"
        assert result.falsifiers[0]["primitive"] == primitive


def test_budget_exhaustion_is_inconclusive(tmp_path: Path) -> None:
    engine = MiMicusEngine(f"sqlite:///{tmp_path / 'budget.db'}")
    fixture = {"claim_statement": "x", "claim_type": "numeric", "price": 1, "users": 1, "claimed": 10}
    result = engine.run(RunRequest(task="ambiguous prose only", source_mode="fixture", fixture=fixture, scenario="general", budget_usd=0.0))
    assert result.status == "inconclusive"
    assert result.answer.startswith("INCONCLUSIVE")
