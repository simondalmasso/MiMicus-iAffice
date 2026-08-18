from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import tempfile
import types
from pathlib import Path
from typing import Any

from mimicus.agents.calibration import capability_scope
from mimicus.agents.identity import exact_fingerprint
from mimicus.claims.models import Claim
from mimicus.coalition.selector import correlation
from mimicus.falsifiers.builtins import builtin_specs
from mimicus.falsifiers.market import FalsifierMarket, falsifier_proximity, falsifier_signature
from mimicus.memory.gates import write_gate
from mimicus.memory.models import MemoryItem
from mimicus.orchestration.budget import BudgetLedger
from mimicus.orchestration.dag_executor import DagExecutionError, DagExecutor
from mimicus.orchestration.engine import MiMicusEngine, RunRequest
from mimicus.orchestration.morphology import DagNode, MorphologyName, MorphologyPlan, NodeKind, compile_morphology
from mimicus.providers.openai_agents import OpenAIAgentsProvider
from mimicus.providers.scripted import ScriptedProvider
from mimicus.types import MemoryStatus
from mimicus.validation.order003_worker import _mcp_stage


def _database() -> str:
    return os.environ["MIMICUS_DATABASE_URL"]


def _critic(engine: MiMicusEngine):
    return next(candidate for candidate in engine.services.agent_factory.candidates() if candidate.name == "critic-1")


def specialist_freshness() -> dict[str, Any]:
    engine = MiMicusEngine(_database())
    critic = _critic(engine)
    fixture = {
        "claim_statement": "dated observation",
        "claim_type": "temporal",
        "evidence_date": "2026-08-10T00:00:00+00:00",
        "as_of": "2026-08-17T00:00:00+00:00",
    }
    results = [engine.run(RunRequest(task="Evaluate temporal freshness from supplied evidence", domain="research", scenario="freshness", fixture=fixture)) for _ in range(3)]
    scope = capability_scope("research", "entailment", "entailment_canary")
    row = engine.repository.calibration(critic.fingerprint, scope)
    assert row["attempts"] == 0
    return {
        "pass": True,
        "critic_fingerprint": critic.fingerprint,
        "critic_entailment_attempts": row["attempts"],
        "freshness_coalitions": [result.coalition["members"] for result in results],
    }


def specialist_entailment() -> dict[str, Any]:
    engine = MiMicusEngine(_database())
    critic = _critic(engine)
    fixture = {
        "claim_statement": "reported figure",
        "claim_type": "numeric",
        "claim_figure": 42,
        "evidence_spans": [{"span_id": "a", "supported_figures": [42], "material_support": True}],
    }
    result = engine.run(RunRequest(task="Evaluate citation entailment for supplied figure", domain="research", scenario="citation_entailment", fixture=fixture))
    assert critic.fingerprint in result.coalition["members"]
    return {"pass": True, "critic_fingerprint": critic.fingerprint, "selected": True, "run_id": result.run_id}


def specialist_bankrupt() -> dict[str, Any]:
    engine = MiMicusEngine(_database())
    critic = _critic(engine)
    fixture = {
        "claim_statement": "reported figure",
        "claim_type": "numeric",
        "claim_figure": 42,
        "evidence_spans": [{"span_id": "a", "supported_figures": [42], "material_support": True}],
        "audition_fail_capabilities": ["entailment"],
    }
    for _ in range(3):
        engine.run(RunRequest(task="Evaluate citation entailment for supplied figure", domain="research", scenario="citation_entailment", fixture=fixture))
    scope = capability_scope("research", "entailment", "entailment_canary")
    state = engine.repository.bankruptcy_state(critic.fingerprint, scope)
    assert state == "BANKRUPT"
    return {
        "pass": True,
        "critic_fingerprint": critic.fingerprint,
        "capability_scope": scope,
        "capability_state": state,
        "legacy_domain_projection": engine.repository.bankruptcy_state(critic.fingerprint, "research"),
    }


def specialist_recovery() -> dict[str, Any]:
    engine = MiMicusEngine(_database())
    critic = _critic(engine)
    fixture = {
        "claim_statement": "reported figure",
        "claim_type": "numeric",
        "claim_figure": 42,
        "evidence_spans": [{"span_id": "a", "supported_figures": [42], "material_support": True}],
    }
    excluded = engine.run(RunRequest(task="Evaluate citation entailment for supplied figure", domain="research", scenario="citation_entailment", fixture=fixture))
    assert critic.fingerprint not in excluded.coalition["members"]
    recovered = engine.run(
        RunRequest(
            task="Evaluate citation entailment for supplied figure",
            domain="research",
            scenario="citation_entailment",
            fixture=fixture | {"recovery_names": ["critic-1"]},
        )
    )
    scope = capability_scope("research", "entailment", "entailment_canary")
    assert engine.repository.bankruptcy_state(critic.fingerprint, scope) == "ACTIVE"
    assert critic.fingerprint in recovered.coalition["members"]
    return {
        "pass": True,
        "excluded_before_recovery": True,
        "active_after_recovery": True,
        "selected_after_recovery": True,
        "recovery_run_id": recovered.run_id,
    }


def memory_seed() -> dict[str, Any]:
    engine = MiMicusEngine(_database())
    result = engine.run(RunRequest(task="numeric annual consistency", domain="finance", scenario="tam_12x", learn=True))
    assert result.memory_changes
    trusted = result.memory_changes[0]
    blocked = write_gate(
        MemoryItem(
            claim_hash="e" * 64,
            content="quarantined poison must not reach provider",
            owner_fingerprint="external",
            domain="finance",
            origin_clusters=["unverified"],
            authority=0.99,
        )
    )
    assert blocked.status == MemoryStatus.QUARANTINED
    engine.repository.save_memory_transition(blocked, reason="ORDER-004 negative memory fixture", from_status="candidate")
    return {"pass": True, "trusted_memory_id": trusted["memory_id"], "blocked_memory_id": blocked.memory_id, "run_id": result.run_id}


def memory_openai() -> dict[str, Any]:
    captured: dict[str, Any] = {}
    module = types.ModuleType("agents")

    class Agent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.name = kwargs["name"]

    class Runner:
        @staticmethod
        async def run(agent, task, max_turns):
            captured["task"] = task
            return types.SimpleNamespace(
                final_output=Claim(statement="provider claim", domain="finance", probability=0.7, claim_type="numeric"),
                last_agent=types.SimpleNamespace(name=agent.name),
                context_wrapper=types.SimpleNamespace(usage=types.SimpleNamespace(input_tokens=40, output_tokens=10, total_tokens=50)),
            )

    module.Agent = Agent
    module.Runner = Runner
    sys.modules["agents"] = module
    provider = OpenAIAgentsProvider("gpt-mock")
    engine = MiMicusEngine(_database(), provider=provider)
    result = engine.run(RunRequest(task="numeric annual consistency", domain="finance", scenario="tam_12x", budget_usd=1.0))
    body = json.loads(str(captured["task"]))
    memory = body["verified_institutional_memory"]
    assert memory
    rendered = json.dumps(memory)
    assert "quarantined poison" not in rendered
    usage_rows = result.evidence_provenance["provider_usages"]
    assert usage_rows and usage_rows[0]["usage"]["verified_memory_items_consumed"] >= 1
    return {
        "pass": True,
        "memory_items_consumed": usage_rows[0]["usage"]["verified_memory_items_consumed"],
        "memory_ids": [item["memory_id"] for item in memory],
        "blocked_content_absent": "quarantined poison" not in rendered,
        "sealed_first_pass": body["sealed_first_pass"],
        "peer_outputs_included": body["peer_outputs_included"],
        "monetary_cost_status": usage_rows[0]["usage"]["monetary_cost_status"],
        "run_budget": result.budget,
    }


def evidence_process() -> dict[str, Any]:
    engine = MiMicusEngine(_database())
    fixture = {"claim_statement": "annual amount", "claim_type": "numeric", "price": 10.0, "users": 10.0, "price_period": "monthly", "claimed": 1000.0}
    result = engine.run(RunRequest(task="numeric annualized consistency", domain="finance", scenario="tam_12x", fixture=fixture))
    fetched = MiMicusEngine(_database()).get_run(result.run_id)
    assert fetched is not None
    refs = {ref for claim in fetched["final_claims"] for ref in claim.get("evidence_refs", [])}
    evidence = fetched["evidence"]
    hashes = {row["evidence_hash"] for row in evidence}
    assert refs and refs <= hashes
    assert fetched["replay_state"]["verified"]
    return {
        "pass": True,
        "run_id": result.run_id,
        "claim_evidence_refs": sorted(refs),
        "persisted_evidence_hashes": sorted(hashes),
        "resolved_count": len(refs),
        "replay_verified": True,
        "evidence": evidence,
    }


def identity_probe() -> dict[str, Any]:
    provider = ScriptedProvider(provider_id="runtime-provider", model_id="runtime-model")
    engine = MiMicusEngine("sqlite:///:memory:", provider=provider)
    candidates = engine.services.agent_factory.candidates()
    left, right = candidates[0], candidates[1]
    base = engine.services.agent_factory.identity_for(left)
    changed = exact_fingerprint(
        provider=base.provider,
        model=base.model_family,
        model_version=base.runtime_model_version,
        phenotype=base.phenotype,
        phenotype_version=base.phenotype_version,
        system_prompt_hash="f" * 64,
        tool_manifest_hash=base.tool_manifest_hash,
        policy_hash=base.policy_hash,
        provider_adapter_version=base.provider_adapter_version,
    )
    assert changed != base.fingerprint
    assert correlation(left, right) >= 0.55
    return {
        "pass": True,
        "provider_capabilities": provider.capabilities.__dict__,
        "identity_manifest": base.material_manifest,
        "fingerprint": base.fingerprint,
        "material_change_fingerprint": changed,
        "material_change_changes_fingerprint": changed != base.fingerprint,
        "same_runtime_model_correlation": correlation(left, right),
        "same_runtime_model_penalized": correlation(left, right) >= 0.55,
    }


def budget_probe() -> dict[str, Any]:
    async def ledger_cases() -> dict[str, Any]:
        race = BudgetLedger(1.0)
        contenders = await asyncio.gather(race.reserve("agent_generation", 1.0), race.reserve("challenge", 1.0))
        unknown = BudgetLedger(1.0)
        reservation = await unknown.reserve("agent_generation", 0.6)
        assert reservation is not None
        await unknown.reconcile(reservation, None)
        released_ledger = BudgetLedger(1.0)
        released_reservation = await released_ledger.reserve("agent_generation", 0.5)
        assert released_reservation is not None
        await released_ledger.release(released_reservation, reason="structured sibling cancellation")
        return {
            "race_winners": sum(item is not None for item in contenders),
            "race": race.snapshot(),
            "unknown": unknown.snapshot(),
            "release": released_ledger.snapshot(),
        }

    cases = asyncio.run(ledger_cases())
    with tempfile.TemporaryDirectory(prefix="mimicus-budget-") as directory:
        paid = ScriptedProvider(default_cost=0.01, challenge_cost=0.01)
        zero = MiMicusEngine(f"sqlite:///{Path(directory) / 'zero.db'}", provider=paid).run(
            RunRequest(task="numeric consistency", domain="finance", scenario="tam_12x", budget_usd=0.0)
        )
        challenge_provider = ScriptedProvider(default_cost=0.005, challenge_cost=0.005)
        challenge = MiMicusEngine(f"sqlite:///{Path(directory) / 'challenge.db'}", provider=challenge_provider).run(
            RunRequest(
                task="source citation figure evidence",
                domain="research",
                scenario="general",
                fixture={
                    "claim_statement": "evidence set",
                    "claim_type": "factual",
                    "agent_cost": 0.005,
                    "challenge_cost": 0.005,
                    "force_sparse": True,
                    "agent_probabilities": {"source-1": 0.9, "critic-1": 0.1},
                },
                budget_usd=0.01,
                max_agents=2,
            )
        )
    assert cases["race_winners"] == 1
    assert paid.total_calls == 0
    assert challenge_provider.challenge_calls == 0
    assert challenge.status == "inconclusive"
    return {
        "pass": True,
        "ledger_cases": cases,
        "zero_budget": {"provider_calls": paid.total_calls, "status": zero.status, "budget": zero.budget},
        "challenge_suppressed": {
            "generate_calls": challenge_provider.generate_calls,
            "challenge_calls": challenge_provider.challenge_calls,
            "status": challenge.status,
            "budget": challenge.budget,
        },
    }


def proximity_probe() -> dict[str, Any]:
    specs = builtin_specs("research")
    clone = specs["F1"].model_copy(update={"id": "F1.clone", "version": "1.0.1"})
    selected_clone, clone_scores = FalsifierMarket().select([specs["F1"], clone], budget_usd=1.0, max_tests=2)
    selected_complementary, complementary_scores = FalsifierMarket().select([specs["F1"], specs["F3"]], budget_usd=1.0, max_tests=2)
    assert len(selected_clone) == 1
    assert len(selected_complementary) == 2
    return {
        "pass": True,
        "near_duplicate_proximity": falsifier_proximity(specs["F1"], clone),
        "signature": falsifier_signature(specs["F1"]).__dict__,
        "near_duplicate_selected": [spec.hash for spec in selected_clone],
        "near_duplicate_scores": [score.__dict__ for score in clone_scores],
        "complementary_selected": [spec.hash for spec in selected_complementary],
        "complementary_scores": [score.__dict__ for score in complementary_scores],
    }


def morphology_probe() -> dict[str, Any]:
    counts = {
        MorphologyName.SOLO: ["a"],
        MorphologyName.PAIRED_VERIFY: ["a", "b"],
        MorphologyName.PARALLEL_FANOUT: ["a", "b", "c"],
        MorphologyName.SPARSE_GRAPH: ["a", "b", "c"],
        MorphologyName.HIERARCHICAL_FANOUT_FANIN: ["a", "b", "c", "d"],
    }
    plans: dict[str, Any] = {}
    signatures: list[str] = []
    for name, members in counts.items():
        plan = compile_morphology(
            task_hash="1" * 64,
            selected_fingerprints=members,
            falsifier_hashes=["f" * 64],
            complexity=0.9,
            required_capabilities=("source", "freshness", "entailment"),
            max_concurrency=4,
            learn=False,
            morphology_override=name,
        )
        signatures.append(plan.structural_signature)
        plans[name.value] = {
            "plan_hash": plan.plan_hash,
            "structural_signature": plan.structural_signature,
            "nodes": [node.kind.value for node in plan.nodes],
            "edges": [edge.__dict__ for edge in plan.edges],
        }
    assert len(set(signatures)) == 5
    return {"pass": True, "all_distinct": True, "classes": plans}


def cancellation_probe() -> dict[str, Any]:
    fast = DagNode("fast", NodeKind.AGENT_TASK, ("root",))
    slow = DagNode("slow", NodeKind.AGENT_TASK, ("root",))
    plan = MorphologyPlan(MorphologyName.PARALLEL_FANOUT, [DagNode("root", NodeKind.PROFILE), fast, slow], [])
    cancelled = False
    side_effect = False

    async def run() -> dict[str, Any]:
        nonlocal cancelled, side_effect

        async def handler(node: DagNode) -> object:
            nonlocal cancelled, side_effect
            if node.node_id == "fast":
                await asyncio.sleep(0.01)
                raise RuntimeError("fatal node")
            if node.node_id == "slow":
                try:
                    await asyncio.sleep(0.25)
                    side_effect = True
                except asyncio.CancelledError:
                    cancelled = True
                    raise
            return node.node_id

        try:
            await DagExecutor(2).execute(plan, handler, precompleted={"root": "done"})
        except DagExecutionError as error:
            await asyncio.sleep(0.3)
            return {"failed_nodes": error.failed_nodes, "cancelled_nodes": error.cancelled_nodes}
        raise AssertionError("fatal task must fail the task group")

    details = asyncio.run(run())
    assert cancelled and not side_effect
    return {
        "pass": True,
        "cancelled_observed": cancelled,
        "post_cancel_side_effect": side_effect,
        "fast_status": fast.status,
        "slow_status": slow.status,
        **details,
    }


WORKERS = {
    "specialist_freshness": specialist_freshness,
    "specialist_entailment": specialist_entailment,
    "specialist_bankrupt": specialist_bankrupt,
    "specialist_recovery": specialist_recovery,
    "memory_seed": memory_seed,
    "memory_openai": memory_openai,
    "evidence": evidence_process,
    "mcp": _mcp_stage,
}


def _run_worker(stage: str, database_url: str) -> dict[str, Any]:
    env = os.environ.copy()
    env["MIMICUS_DATABASE_URL"] = database_url
    env.pop("OPENAI_API_KEY", None)
    completed = subprocess.run(
        [sys.executable, __file__, "--worker", stage],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return json.loads(completed.stdout.strip().splitlines()[-1])


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def materialize(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mimicus-order004-e2e-") as directory:
        root = Path(directory)
        specialist_db = f"sqlite:///{root / 'specialist.db'}"
        specialist = {
            "freshness": _run_worker("specialist_freshness", specialist_db),
            "entailment": _run_worker("specialist_entailment", specialist_db),
            "bankrupt": _run_worker("specialist_bankrupt", specialist_db),
            "recovery": _run_worker("specialist_recovery", specialist_db),
        }
        memory_db = f"sqlite:///{root / 'memory.db'}"
        memory = {
            "seed": _run_worker("memory_seed", memory_db),
            "openai_restart": _run_worker("memory_openai", memory_db),
        }
        evidence = _run_worker("evidence", f"sqlite:///{root / 'evidence.db'}")
        mcp_db = f"sqlite:///{root / 'mcp.db'}"
        mcp = _run_worker("mcp", mcp_db)
    identity = identity_probe()
    budget = budget_probe()
    proximity = proximity_probe()
    morphology = morphology_probe()
    cancellation = cancellation_probe()
    payloads = {
        "SPECIALIST_AUDITIONS.json": specialist,
        "RUNTIME_IDENTITY_CORRELATION.json": identity,
        "OPENAI_MEMORY_INJECTION_MOCK.json": memory,
        "BUDGET_LEDGER.json": budget,
        "EVIDENCE_PERSISTENCE.json": evidence,
        "FALSIFIER_PROXIMITY.json": proximity,
        "MORPHOLOGY_CLASSES.json": morphology,
        "STRUCTURED_CANCELLATION.json": cancellation,
        "MCP_E2E.json": mcp,
    }
    for filename, payload in payloads.items():
        assert (
            all(value.get("pass", True) for value in payload.values())
            if filename in {"SPECIALIST_AUDITIONS.json", "OPENAI_MEMORY_INJECTION_MOCK.json"}
            else payload.get("pass", True)
        )
        _write(output_dir / filename, payload)
    report = {"order": "ORDER-004", "process_level": True, "passed": True, "artifacts": sorted(payloads)}
    _write(output_dir / "ORDER004_E2E.json", report)
    print(json.dumps(report, sort_keys=True))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", nargs="?", type=Path)
    parser.add_argument("--worker", choices=sorted(WORKERS))
    args = parser.parse_args()
    if args.worker:
        print(json.dumps(WORKERS[args.worker](), sort_keys=True))
        return 0
    if args.output_dir is None:
        parser.error("output_dir is required unless --worker is used")
    materialize(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
