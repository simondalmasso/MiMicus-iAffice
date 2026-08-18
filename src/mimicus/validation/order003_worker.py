from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
from time import perf_counter
from typing import Any

from mimicus.memory.gates import write_gate
from mimicus.memory.models import MemoryItem
from mimicus.orchestration.dag_executor import DagExecutor
from mimicus.orchestration.engine import MiMicusEngine, RunRequest
from mimicus.orchestration.morphology import DagNode, MorphologyName, MorphologyPlan, NodeKind
from mimicus.orchestration.proximity import SemanticSignature, semantic_proximity
from mimicus.providers.scripted import ScriptedProvider
from mimicus.types import MemoryStatus
from mimicus.validation.worker import _mcp_call


def _db() -> str:
    return os.environ["MIMICUS_DATABASE_URL"]


def _engine(provider: ScriptedProvider | None = None) -> MiMicusEngine:
    return MiMicusEngine(_db(), provider=provider)


def seed_memory() -> dict[str, Any]:
    engine = _engine()
    result = engine.run(RunRequest(task="K3 TAM 12x mismatch", domain="finance", learn=True))
    assert result.memory_changes and result.replay_verified
    trusted = str(result.memory_changes[0]["memory_id"])
    quarantined = write_gate(
        MemoryItem(
            claim_hash="e" * 64,
            content="unverified paraphrase must remain quarantined",
            owner_fingerprint="external-untrusted",
            domain="finance",
            origin_clusters=["unverified-origin"],
            authority=0.95,
        )
    )
    engine.repository.save_memory_transition(quarantined, reason="ORDER-003 negative restart fixture", from_status="candidate")
    assert quarantined.status == MemoryStatus.QUARANTINED
    return {
        "stage": "seed_memory",
        "pass": True,
        "run_id": result.run_id,
        "trusted_memory_id": trusted,
        "blocked_memory_id": quarantined.memory_id,
        "ledger_head": result.ledger_head,
        "state": engine.repository.inspect_state(result.run_id),
    }


def reuse_memory() -> dict[str, Any]:
    engine = _engine()
    eligible_before = [item.memory_id for item in engine.repository.eligible_memory("finance")]
    result = engine.run(RunRequest(task="K3 TAM 12x mismatch", domain="finance"))
    assert result.replay_verified
    state = engine.repository.inspect_state(result.run_id)
    return {
        "stage": "reuse_memory",
        "pass": True,
        "run_id": result.run_id,
        "eligible_before": eligible_before,
        "persistent_memory_reused": result.persistent_memory_reused,
        "ledger_head": result.ledger_head,
        "state": state,
    }


def germinal_seed() -> dict[str, Any]:
    fixture = {
        "claim_statement": "slight mismatch",
        "claim_type": "numeric",
        "price": 10.0,
        "users": 10.0,
        "price_period": "annual",
        "claimed": 104.0,
        "confirmed_evasion": True,
        "ground_truth_verdict": "FAIL",
        "ground_truth_hash": "9" * 64,
        "evasion_primitive": "numeric_invariant",
        "mutation_relative_tolerance": 0.02,
    }
    result = _engine().run(RunRequest(task="TAM slight mismatch", domain="finance", scenario="tam_12x", fixture=fixture, learn=True))
    assert result.germinal_changes and result.germinal_changes[0]["status"] == "PROMOTE"
    return {"stage": "germinal_seed", "pass": True, "run_id": result.run_id, "changes": result.germinal_changes, "ledger_head": result.ledger_head}


def germinal_reuse() -> dict[str, Any]:
    fixture = {
        "claim_statement": "slight mismatch",
        "claim_type": "numeric",
        "price": 10.0,
        "users": 10.0,
        "price_period": "annual",
        "claimed": 104.0,
    }
    result = _engine().run(RunRequest(task="TAM slight mismatch", domain="finance", scenario="tam_12x", fixture=fixture))
    assert result.persistent_falsifiers_reused
    assert result.falsifiers and result.falsifiers[0]["verdict"] == "FAIL"
    return {
        "stage": "germinal_reuse",
        "pass": True,
        "run_id": result.run_id,
        "persistent_falsifiers_reused": result.persistent_falsifiers_reused,
        "falsifiers": result.falsifiers,
        "ledger_head": result.ledger_head,
    }


def bankrupt_seed() -> dict[str, Any]:
    engine = _engine()
    candidate = engine.services.agent_factory.candidates()[0]
    fixture = {
        "claim_statement": "bad numeric candidate",
        "claim_type": "numeric",
        "price": 1.0,
        "users": 1.0,
        "claimed": 10.0,
        "audition_fail_names": [candidate.name],
    }
    run_ids: list[str] = []
    for _ in range(3):
        result = engine.run(RunRequest(task="numeric mismatch", domain="finance", scenario="tam_12x", fixture=fixture))
        run_ids.append(result.run_id)
    state = engine.repository.bankruptcy_state(candidate.fingerprint, "finance")
    assert state == "BANKRUPT"
    identity = engine.services.agent_factory.identity_for(candidate)
    return {
        "stage": "bankrupt_seed",
        "pass": True,
        "fingerprint": candidate.fingerprint,
        "lineage_id": identity.lineage_id,
        "state": state,
        "run_ids": run_ids,
    }


def whitewash() -> dict[str, Any]:
    engine = _engine()
    base = engine.services.agent_factory.candidates()[0]
    base_identity = engine.services.agent_factory.identity_for(base)
    child = "c" * 64
    fixture = {
        "claim_statement": "revised identity",
        "claim_type": "numeric",
        "price": 1.0,
        "users": 1.0,
        "claimed": 10.0,
        "identity_revisions": {
            base.name: {
                "fingerprint": child,
                "lineage_id": base_identity.lineage_id,
                "parent_fingerprint": base.fingerprint,
                "provenance": "ORDER-003 process whitewash probe",
            }
        },
    }
    result = engine.run(RunRequest(task="numeric mismatch", domain="finance", scenario="tam_12x", fixture=fixture))
    state = engine.repository.bankruptcy_state(child, "finance")
    assert state == "PROBATION" and child not in result.coalition["members"]
    return {"stage": "whitewash", "pass": True, "child_fingerprint": child, "state": state, "excluded": result.lineage_exclusions, "run_id": result.run_id}


def recovery() -> dict[str, Any]:
    engine = _engine()
    base = engine.services.agent_factory.candidates()[0]
    base_identity = engine.services.agent_factory.identity_for(base)
    child = "c" * 64
    fixture = {
        "claim_statement": "revised identity",
        "claim_type": "numeric",
        "price": 1.0,
        "users": 1.0,
        "claimed": 10.0,
        "recovery_names": [base.name],
        "identity_revisions": {
            base.name: {
                "fingerprint": child,
                "lineage_id": base_identity.lineage_id,
                "parent_fingerprint": base.fingerprint,
                "provenance": "ORDER-003 process recovery probe",
            }
        },
    }
    result = engine.run(RunRequest(task="numeric mismatch", domain="finance", scenario="tam_12x", fixture=fixture))
    state = engine.repository.bankruptcy_state(child, "finance")
    assert state == "ACTIVE"
    return {"stage": "recovery", "pass": True, "child_fingerprint": child, "state": state, "run_id": result.run_id, "coalition": result.coalition}


def sparse() -> dict[str, Any]:
    provider = ScriptedProvider()
    engine = _engine(provider)
    fixture = {
        "claim_statement": "mixed evidence",
        "claim_type": "factual",
        "clusters": ["wire", "wire"],
        "texts": ["same", "same"],
        "evidence_date": "2025-01-01T00:00:00+00:00",
        "as_of": "2026-08-17T00:00:00+00:00",
        "claim_figure": 42,
        "evidence_spans": [{"span_id": "x", "supported_figures": [41], "material_support": True}],
        "force_sparse": True,
        "force_challenge": True,
        "agent_probabilities": {"source-1": 0.92, "critic-1": 0.18},
    }
    result = engine.run(RunRequest(task="source citation fresh figure echo mixed evidence", domain="research", scenario="general", fixture=fixture, max_concurrency=4))
    persisted = engine.get_run(result.run_id)
    assert result.morphology == "sparse_graph"
    assert result.challenge_edge_count > 0
    assert provider.challenge_calls == result.challenge_edge_count
    assert provider.total_calls == result.provider_call_count
    assert persisted is not None
    communications = persisted["persistent_state"]["communications"]
    assert communications
    return {
        "stage": "sparse",
        "pass": True,
        "run_id": result.run_id,
        "plan_hash": result.plan_hash,
        "morphology": result.morphology,
        "provider_calls": provider.total_calls,
        "challenge_calls": provider.challenge_calls,
        "challenge_edges": result.challenge_edge_count,
        "communications": communications,
        "concurrency": result.concurrency_summary,
        "critical_path": result.critical_path_summary,
    }


def parallel() -> dict[str, Any]:
    root = DagNode("root", NodeKind.PROFILE)
    left = DagNode("left", NodeKind.AGENT_TASK, ("root",))
    right = DagNode("right", NodeKind.AGENT_TASK, ("root",))
    join = DagNode("join", NodeKind.JOIN, ("left", "right"))
    plan = MorphologyPlan(MorphologyName.PARALLEL_FANOUT, [root, left, right, join], [])

    async def handler(node: DagNode) -> object:
        if node.kind == NodeKind.AGENT_TASK:
            await asyncio.sleep(0.25)
        return {"node": node.node_id}

    started = perf_counter()
    execution = asyncio.run(DagExecutor(max_concurrency=2).execute(plan, handler, precompleted={"root": {"done": True}}))
    wall = (perf_counter() - started) * 1000.0
    metrics = execution.metrics.as_dict()
    assert wall < 425.0
    assert metrics["peak_concurrency"] >= 2
    assert metrics["critical_path_ms"] < metrics["serial_work_ms"]
    assert metrics["avoidable_serialization_count"] == 0
    assert execution.output_hashes["left"] and execution.output_hashes["right"]
    return {"stage": "parallel", "pass": True, "wall_ms": wall, "threshold_ms": 425.0, "metrics": metrics, "output_hashes": execution.output_hashes, "schedule": execution.schedule}


def proximity() -> dict[str, Any]:
    base = SemanticSignature("Revenue is 42 USD", "finance", "numeric", "USD", evidence_clusters=("origin-a",), numeric_value=42)
    clone = SemanticSignature("Revenue is 42 USD", "finance", "numeric", "USD", evidence_clusters=("origin-a",), numeric_value=42)
    contradiction = SemanticSignature("Revenue is not 42 USD", "finance", "numeric", "USD", evidence_clusters=("origin-b",), numeric_value=41)
    clone_result = semantic_proximity(base, clone)
    contradiction_result = semantic_proximity(base, contradiction)
    assert clone_result.marginal_novelty < contradiction_result.marginal_novelty
    assert contradiction_result.useful_contradiction
    return {"stage": "proximity", "pass": True, "clone": clone_result.__dict__, "contradiction": contradiction_result.__dict__}


def _mcp_stage() -> dict[str, Any]:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = os.environ.copy()
    env.pop("OPENAI_API_KEY", None)
    process = subprocess.Popen(
        [sys.executable, "-m", "mimicus.interfaces.cli", "serve", "--profile", "offline", "--host", "127.0.0.1", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    try:
        response = asyncio.run(_mcp_call(f"http://127.0.0.1:{port}/mcp"))
        run = response["run"]
        fetched = response["fetched"]
        assert fetched.get("replay_state", {}).get("verified") is True
        return {
            "stage": "mcp",
            "pass": True,
            "run_id": run["run_id"],
            "ledger_head": run["ledger_head"],
            "persistent_memory_reused": run.get("persistent_memory_reused", []),
            "plan_hash": run.get("plan_hash"),
            "morphology": run.get("morphology"),
            "replay_verified": True,
            "transport": "streamable-http",
            "path": "/mcp",
            "openai_key_required": False,
        }
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


STAGES = {
    "seed_memory": seed_memory,
    "reuse_memory": reuse_memory,
    "germinal_seed": germinal_seed,
    "germinal_reuse": germinal_reuse,
    "bankrupt_seed": bankrupt_seed,
    "whitewash": whitewash,
    "recovery": recovery,
    "sparse": sparse,
    "parallel": parallel,
    "proximity": proximity,
    "mcp": _mcp_stage,
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in STAGES:
        raise SystemExit(f"usage: {sys.executable} -m mimicus.validation.order003_worker <{'|'.join(STAGES)}>")
    result = STAGES[sys.argv[1]]()
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
