from __future__ import annotations

from mimicus.claims.evidence_bundle import EvidenceInput
from mimicus.orchestration.causal_replay import verify_causal_execution
from mimicus.orchestration.engine import MiMicusEngine, RunRequest
from mimicus.orchestration.semantic_replay import semantic_replay
from mimicus.providers.scripted import ScriptedProvider


def test_runtime_records_and_semantically_replays_causal_dag(tmp_path) -> None:
    engine = MiMicusEngine(
        f"sqlite:///{tmp_path / 'causal-runtime.db'}",
        provider=ScriptedProvider(),
    )
    run = engine.run(
        RunRequest(
            task="Audit the numeric runtime evidence.",
            domain="finance",
            source_mode="runtime",
            evidence=[
                EvidenceInput(
                    origin="causal://runtime",
                    independence_cluster="causal-runtime",
                    content="numeric runtime evidence",
                    extracted_facts={
                        "price": 100.0,
                        "users": 12.0,
                        "price_period": "annual",
                        "claimed": 1200.0,
                    },
                )
            ],
            max_agents=1,
            depth="deep",
            learn=False,
        )
    )

    assert run.causal_execution["semantic_hash"]
    assert run.causal_execution["semantic"]["plan_hash"] == run.plan_hash
    assert verify_causal_execution(run.causal_execution)["verified"] is True
    statuses = {row["status"] for row in run.causal_execution["semantic"]["nodes"]}
    assert statuses <= {"COMPLETED", "PRECOMPLETED"}
    assert "PRECOMPLETED" in statuses

    replay = semantic_replay(engine.repository, run.run_id)
    assert replay["verified"] is True
    assert replay["causal_contract_verified"] is True


def test_runtime_causal_semantic_hash_excludes_incidental_scheduler_material(tmp_path) -> None:
    engine = MiMicusEngine(
        f"sqlite:///{tmp_path / 'causal-incidental.db'}",
        provider=ScriptedProvider(),
    )
    run = engine.run(
        RunRequest(
            task="Assess a simple supported runtime claim.",
            domain="general",
            source_mode="runtime",
            evidence=[
                EvidenceInput(
                    origin="causal://incidental",
                    independence_cluster="causal-incidental",
                    content="verified runtime observation",
                    extracted_facts={"observed": True},
                )
            ],
            max_agents=1,
            learn=False,
        )
    )

    causal = run.causal_execution
    original_hash = causal["semantic_hash"]
    causal["incidental"]["run_id"] = "different-incidental-run"
    causal["incidental"]["scheduler_schedule"] = [{"scheduler_turn": 999, "duration_ms": 999999.0}]

    assert verify_causal_execution(causal)["verified"] is True
    assert causal["semantic_hash"] == original_hash
