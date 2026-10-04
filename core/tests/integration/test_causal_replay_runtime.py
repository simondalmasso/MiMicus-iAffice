from __future__ import annotations

import copy

from sqlalchemy import update

from mimicus.canonical import canonical_json, sha256_obj
from mimicus.claims.evidence_bundle import EvidenceInput
from mimicus.orchestration.causal_replay import verify_causal_execution
from mimicus.orchestration.engine import MiMicusEngine, RunRequest
from mimicus.orchestration.semantic_replay import semantic_replay
from mimicus.providers.scripted import ScriptedProvider
from mimicus.storage.models import RunRow


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


def test_causal_replay_is_anchored_to_immutable_event_ledger(tmp_path) -> None:
    engine = MiMicusEngine(
        f"sqlite:///{tmp_path / 'causal-anchor.db'}",
        provider=ScriptedProvider(),
    )
    run = engine.run(
        RunRequest(
            task="Assess a supported runtime observation.",
            domain="general",
            source_mode="runtime",
            evidence=[
                EvidenceInput(
                    origin="causal://anchor",
                    independence_cluster="causal-anchor",
                    content="verified runtime observation",
                    extracted_facts={"observed": True},
                )
            ],
            max_agents=1,
            learn=False,
        )
    )

    persisted = engine.repository.get_run(run.run_id)
    assert persisted is not None
    tampered = copy.deepcopy(persisted)
    causal = tampered["causal_execution"]
    semantic_nodes = causal["semantic"]["nodes"]
    parent_ids = {
        parent
        for row in semantic_nodes
        for parent in row["prerequisites"]
    }
    leaf = next(row for row in semantic_nodes if row["node_id"] not in parent_ids)
    leaf["output_hash"] = "f" * 64
    causal["semantic_hash"] = sha256_obj(causal["semantic"])

    snapshot = tampered["semantic_replay"]
    snapshot_causal = snapshot["input_material"]["causal_execution"]
    snapshot_causal["semantic"] = copy.deepcopy(causal["semantic"])
    snapshot_causal["semantic_hash"] = causal["semantic_hash"]
    snapshot["expected"]["causal_semantic_hash"] = causal["semantic_hash"]
    snapshot["input_hash"] = sha256_obj(snapshot["input_material"])
    snapshot["expected_hash"] = sha256_obj(snapshot["expected"])

    with engine.repository.engine.begin() as connection:
        connection.execute(
            update(RunRow)
            .where(RunRow.run_id == run.run_id)
            .values(result_json=canonical_json(tampered))
        )

    detected = semantic_replay(engine.repository, run.run_id)
    assert detected["verified"] is False
    assert detected["causal_contract_verified"] is False
    assert detected["causal_ledger_anchor_verified"] is False
