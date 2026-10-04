from __future__ import annotations

import copy

from mimicus.canonical import sha256_obj
from mimicus.orchestration.causal_replay import build_causal_execution, verify_causal_execution
from mimicus.orchestration.dag_executor import DagExecution, ExecutionMetrics
from mimicus.orchestration.morphology import DagEdge, DagNode, MorphologyName, MorphologyPlan, NodeKind


def _plan() -> MorphologyPlan:
    root = DagNode("root", NodeKind.PROFILE, input_hash=sha256_obj("task"))
    worker = DagNode("worker", NodeKind.AGENT_TASK, ("root",), input_hash=sha256_obj("worker-input"))
    join = DagNode("join", NodeKind.JOIN, ("worker",), input_hash=sha256_obj("join-input"))
    return MorphologyPlan(
        MorphologyName.SOLO,
        [root, worker, join],
        [DagEdge("root", "worker"), DagEdge("worker", "join")],
    )


def _execution() -> DagExecution:
    root_hash = sha256_obj({"root": "ready"})
    worker_hash = sha256_obj({"worker": "done"})
    join_hash = sha256_obj({"join": "done"})
    metrics = ExecutionMetrics(
        work_steps=2,
        critical_steps=2,
        critical_path_ms=7.0,
        observed_wall_ms=5.0,
        serial_work_ms=7.0,
        peak_concurrency=1,
        parallel_speedup_estimate=1.0,
        parallel_efficiency=1.0,
        subtask_finish_rate=1.0,
        avoidable_serialization_count=0,
    )
    return DagExecution(
        outputs={"root": {"root": "ready"}, "worker": {"worker": "done"}, "join": {"join": "done"}},
        output_hashes={"root": root_hash, "worker": worker_hash, "join": join_hash},
        metrics=metrics,
        schedule=[
            {"node_id": "worker", "duration_ms": 4.0, "scheduler_turn": 1, "output_hash": worker_hash, "status": "COMPLETED"},
            {"node_id": "join", "duration_ms": 3.0, "scheduler_turn": 2, "output_hash": join_hash, "status": "COMPLETED"},
        ],
    )


def _rehash(record: dict[str, object]) -> dict[str, object]:
    cloned = copy.deepcopy(record)
    semantic = cloned["semantic"]
    assert isinstance(semantic, dict)
    cloned["semantic_hash"] = sha256_obj(semantic)
    return cloned


def test_causal_hash_ignores_incidental_run_and_scheduler_metadata() -> None:
    plan = _plan()
    execution = _execution()

    first = build_causal_execution(
        plan,
        execution,
        precompleted_ids={"root"},
        incidental={"run_id": "run-a", "timestamp": "2026-10-03T22:00:00Z", "schedule": execution.schedule},
    )
    second = build_causal_execution(
        plan,
        execution,
        precompleted_ids={"root"},
        incidental={"run_id": "run-b", "timestamp": "2027-01-01T00:00:00Z", "schedule": [{"scheduler_turn": 99}]},
    )

    assert first["semantic_hash"] == second["semantic_hash"]
    assert first["incidental"] != second["incidental"]
    assert verify_causal_execution(first)["verified"] is True
    nodes = {row["node_id"]: row for row in first["semantic"]["nodes"]}
    assert nodes["root"]["status"] == "PRECOMPLETED"
    assert nodes["worker"]["prerequisite_output_hashes"] == {"root": execution.output_hashes["root"]}


def test_causal_verifier_detects_parent_output_binding_tamper_even_when_rehashed() -> None:
    record = build_causal_execution(_plan(), _execution(), precompleted_ids={"root"})
    tampered = copy.deepcopy(record)
    nodes = {row["node_id"]: row for row in tampered["semantic"]["nodes"]}
    nodes["worker"]["prerequisite_output_hashes"]["root"] = "0" * 64
    tampered = _rehash(tampered)

    result = verify_causal_execution(tampered)

    assert result["verified"] is False
    assert "prerequisite output" in str(result["reason"])


def test_causal_verifier_detects_output_hash_tamper_even_when_rehashed() -> None:
    record = build_causal_execution(_plan(), _execution(), precompleted_ids={"root"})
    tampered = copy.deepcopy(record)
    nodes = {row["node_id"]: row for row in tampered["semantic"]["nodes"]}
    nodes["root"]["output_hash"] = "f" * 64
    tampered = _rehash(tampered)

    result = verify_causal_execution(tampered)

    assert result["verified"] is False


def test_causal_verifier_rejects_missing_prerequisite_and_cycle() -> None:
    record = build_causal_execution(_plan(), _execution(), precompleted_ids={"root"})

    missing = copy.deepcopy(record)
    nodes = {row["node_id"]: row for row in missing["semantic"]["nodes"]}
    nodes["worker"]["prerequisites"] = ["missing"]
    nodes["worker"]["prerequisite_output_hashes"] = {"missing": "a" * 64}
    missing = _rehash(missing)
    assert verify_causal_execution(missing)["verified"] is False

    cyclic = copy.deepcopy(record)
    nodes = {row["node_id"]: row for row in cyclic["semantic"]["nodes"]}
    nodes["root"]["prerequisites"] = ["join"]
    nodes["root"]["prerequisite_output_hashes"] = {"join": nodes["join"]["output_hash"]}
    cyclic = _rehash(cyclic)
    assert verify_causal_execution(cyclic)["verified"] is False
