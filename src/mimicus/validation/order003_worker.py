from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
from time import perf_counter
from typing import Any

from mimicus.agents.identity import make_identity
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
    owner = engine.services.agent_factory.candidates()[0].fingerprint
    verified = MemoryItem(claim_hash="a" * 64, content="persistent verified memory", owner_fingerprint=owner, domain="finance", origin_clusters=["independent-a", "independent-b"], authority=0.92, status=MemoryStatus.SHARED_VERIFIED, deterministic_verification=True, verified_clusters=["independent-a", "independent-b"])
    rejected = MemoryItem(claim_hash="b" * 64, content="quarantined poison", owner_fingerprint=owner, domain="finance", origin_clusters=["poison"], authority=0.99, status=MemoryStatus.QUARANTINED, deterministic_verification=False, verified_clusters=[])
    assert write_gate(verified).allowed
    engine.repository.save_memory_transition(verified, reason="ORDER-003 process seed", from_status="private_verified")
    engine.repository.save_memory_transition(rejected, reason="ORDER-003 process quarantine", from_status="candidate")
    return {"stage": "seed_memory", "pass": True, "verified_memory_id": verified.memory_id, "rejected_memory_id": rejected.memory_id}


def reuse_memory() -> dict[str, Any]:
    engine = _engine()
    result = engine.run(RunRequest(task="K3 TAM 12x mismatch", domain="finance", scenario="tam_12x", fixture={"claim_statement": "TAM", "claim_type": "numeric", "price": 10.0, "users": 100.0, "price_period": "monthly", "claimed": 1000.0}))
    reused = set(result.persistent_memory_reused)
    assert reused
    assert all("quarantined" not in memory_id for memory_id in reused)
    return {"stage": "reuse_memory", "pass": True, "run_id": result.run_id, "reused": sorted(reused), "status": result.status}


def seed_germinal() -> dict[str, Any]:
    engine = _engine()
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
    result = engine.run(RunRequest(task="TAM slight mismatch", domain="finance", scenario="tam_12x", fixture=fixture, learn=True))
    assert result.germinal_changes and result.germinal_changes[0]["status"] == "PROMOTE"
    return {"stage": "seed_germinal", "pass": True, "run_id": result.run_id, "changes": result.germinal_changes}


def reuse_germinal() -> dict[str, Any]:
    engine = _engine()
    fixture = {"claim_statement": "slight mismatch", "claim_type": "numeric", "price": 10.0, "users": 10.0, "price_period": "annual", "claimed": 104.0}
    result = engine.run(RunRequest(task="TAM slight mismatch", domain="finance", scenario="tam_12x", fixture=fixture))
    assert result.persistent_falsifiers_reused
    return {"stage": "reuse_germinal", "pass": True, "run_id": result.run_id, "reused": result.persistent_falsifiers_reused, "verdicts": result.falsifiers}


async def _parallel_probe() -> dict[str, Any]:
    root = DagNode("root", NodeKind.PROFILE)
    left = DagNode("left", NodeKind.AGENT_TASK, ("root",))
    right = DagNode("right", NodeKind.AGENT_TASK, ("root",))
    join = DagNode("join", NodeKind.JOIN, ("left", "right"))
    plan = MorphologyPlan(MorphologyName.PARALLEL_FANOUT, [root, left, right, join], [])
    root.status = "COMPLETED"

    async def handler(node: DagNode) -> object:
        if node.kind == NodeKind.AGENT_TASK:
            await asyncio.sleep(0.25)
        return {"node": node.node_id}

    started = perf_counter()
    result = await DagExecutor(max_concurrency=2).execute(plan, handler, precompleted={"root": {"done": True}})
    wall = (perf_counter() - started) * 1000.0
    return {
        "stage": "parallel",
        "pass": result.metrics.peak_concurrency == 2 and wall < 425.0,
        "wall_ms": wall,
        "peak_concurrency": result.metrics.peak_concurrency,
        "serial_work_ms": result.metrics.serial_work_ms,
        "critical_path_ms": result.metrics.critical_path_ms,
        "parallel_speedup_estimate": result.metrics.parallel_speedup_estimate,
        "parallel_efficiency": result.metrics.parallel_efficiency,
        "avoidable_serialization_count": result.metrics.avoidable_serialization_count,
        "output_hashes": result.output_hashes,
    }


def parallel() -> dict[str, Any]:
    result = asyncio.run(_parallel_probe())
    assert result["pass"]
    return result


def proximity() -> dict[str, Any]:
    base = SemanticSignature("Revenue is 42 USD", "finance", "numeric", "USD", evidence_clusters=("wire-a",), numeric_value=42)
    clone = SemanticSignature("Revenue is 42 USD", "finance", "numeric", "USD", evidence_clusters=("wire-a",), numeric_value=42)
    contradiction = SemanticSignature("Revenue is not 42 USD", "finance", "numeric", "USD", evidence_clusters=("wire-b",), numeric_value=41)
    clone_result = semantic_proximity(base, clone)
    contradiction_result = semantic_proximity(base, contradiction)
    assert clone_result.score >= 0.8 and clone_result.marginal_novelty <= 0.2
    assert contradiction_result.useful_contradiction and contradiction_result.marginal_novelty >= 0.65
    return {"stage": "proximity", "pass": True, "clone": clone_result.__dict__, "contradiction": contradiction_result.__dict__}


def bankrupt_seed() -> dict[str, Any]:
    engine = _engine()
    candidate = engine.services.agent_factory.candidates()[0]
    fixture = {"claim_statement": "bad canary", "claim_type": "numeric", "price": 1.0, "users": 1.0, "claimed": 10.0, "audition_fail_names": [candidate.name]}
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
                "provenance": "ORDER-003 process whitewash probe",
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
        "agent_probabilities": {"source-1": 0.9, "critic-1": 0.2},
    }
    result = engine.run(RunRequest(task="source citation fresh figure echo mixed evidence", domain="research", scenario="general", fixture=fixture, max_concurrency=4))
    assert result.morphology == "sparse_graph"
    assert result.challenge_edge_count >= 1
    assert provider.challenge_calls == result.challenge_edge_count
    persisted = engine.get_run(result.run_id)
    assert persisted is not None and persisted["persistent_state"]["communications"]
    return {"stage": "sparse", "pass": True, "run_id": result.run_id, "morphology": result.morphology, "challenge_edges": result.challenge_edge_count, "provider_calls": result.provider_call_count, "persisted": persisted["persistent_state"]["communications"]}


def mcp_restart() -> dict[str, Any]:
    db_url = _db()
    if not db_url.startswith("sqlite:///"):
        raise RuntimeError("ORDER-003 MCP process evidence currently requires SQLite path")
    db_path = db_url.removeprefix("sqlite:///")

    def start() -> tuple[subprocess.Popen[str], int]:
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = int(sock.getsockname()[1])
        sock.close()
        env = os.environ.copy()
        env.pop("OPENAI_API_KEY", None)
        proc = subprocess.Popen(
            [sys.executable, "-m", "mimicus.interfaces.cli", "serve", "--profile", "offline", "--host", "127.0.0.1", "--port", str(port)],
            env={**env, "MIMICUS_DATABASE_URL": f"sqlite:///{db_path}"},
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return proc, port

    proc1, port1 = start()
    try:
        first = _mcp_call(port1, "run_mimicus", {"task": "K3 TAM 12x mismatch", "domain": "finance", "budget_usd": 0.0})
    finally:
        proc1.terminate()
        proc1.wait(timeout=5)
    proc2, port2 = start()
    try:
        fetched = _mcp_call(port2, "get_mimicus_run", {"run_id": first["run_id"]})
    finally:
        proc2.terminate()
        proc2.wait(timeout=5)
    assert fetched["found"] and fetched["replay_state"]["verified"] is True
    return {"stage": "mcp_restart", "pass": True, "run_id": first["run_id"], "first_status": first["status"], "restart_replay_verified": fetched["replay_state"]["verified"]}


STAGES = {
    "seed_memory": seed_memory,
    "reuse_memory": reuse_memory,
    "seed_germinal": seed_germinal,
    "reuse_germinal": reuse_germinal,
    "parallel": parallel,
    "proximity": proximity,
    "bankrupt_seed": bankrupt_seed,
    "whitewash": whitewash,
    "recovery": recovery,
    "sparse": sparse,
    "mcp_restart": mcp_restart,
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in STAGES:
        raise SystemExit(f"usage: python -m mimicus.validation.order003_worker <{'|'.join(STAGES)}>")
    result = STAGES[sys.argv[1]]()
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
