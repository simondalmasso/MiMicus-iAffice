from __future__ import annotations

import asyncio
from pathlib import Path
from time import perf_counter

from mimicus.agents.identity import make_identity
from mimicus.coalition.threat_profile import profile_task
from mimicus.falsifiers.builtins import builtin_specs
from mimicus.memory.models import MemoryItem
from mimicus.orchestration.dag_executor import DagExecutor
from mimicus.orchestration.engine import MiMicusEngine, RunRequest, default_candidates
from mimicus.orchestration.morphology import DagNode, MorphologyName, MorphologyPlan, NodeKind, compile_morphology
from mimicus.orchestration.proximity import SemanticSignature, proposal_marginal_value, semantic_proximity
from mimicus.providers.scripted import ScriptedProvider
from mimicus.storage.repository import Repository
from mimicus.types import MemoryStatus


def test_semantic_proximity_clone_origin_and_contradiction() -> None:
    clone_a = SemanticSignature("Revenue is 42 USD", "finance", "numeric", "USD", evidence_clusters=("wire-a",), numeric_value=42)
    clone_b = SemanticSignature("Revenue is 42 USD", "finance", "numeric", "USD", evidence_clusters=("wire-a",), numeric_value=42)
    exact = semantic_proximity(clone_a, clone_b)
    assert exact.score >= 0.8
    assert exact.marginal_novelty <= 0.2
    paraphrase = SemanticSignature("The revenue equals USD 42", "finance", "numeric", "USD", evidence_clusters=("wire-a",), numeric_value=42)
    assert semantic_proximity(clone_a, paraphrase).evidence_overlap == 1.0
    contradiction = SemanticSignature("Revenue is not 42 USD", "finance", "numeric", "USD", evidence_clusters=("wire-b",), numeric_value=41)
    contradicted = semantic_proximity(clone_a, contradiction)
    assert contradicted.useful_contradiction
    assert contradicted.marginal_novelty >= 0.65
    value, comparisons = proposal_marginal_value(contradiction, [clone_a])
    assert value >= 0.65 and comparisons


def test_morphology_compiles_distinct_executable_dags() -> None:
    simple = compile_morphology(
        task_hash="a" * 64,
        selected_fingerprints=["b" * 64],
        falsifier_hashes=["c" * 64],
        complexity=0.2,
        required_capabilities=("numeric",),
        max_concurrency=4,
        learn=False,
    )
    mixed = compile_morphology(
        task_hash="d" * 64,
        selected_fingerprints=["e" * 64, "f" * 64, "1" * 64],
        falsifier_hashes=["2" * 64, "3" * 64],
        complexity=0.9,
        required_capabilities=("source", "freshness", "entailment"),
        max_concurrency=4,
        learn=True,
        force_sparse=True,
    )
    assert simple.name == MorphologyName.SOLO
    assert mixed.name == MorphologyName.SPARSE_GRAPH
    assert simple.plan_hash != mixed.plan_hash
    assert any(node.kind == NodeKind.CHALLENGE for node in mixed.nodes)
    assert any(node.kind == NodeKind.GERMINAL for node in mixed.nodes)


def test_dag_executor_overlaps_independent_delays_and_bounds_concurrency() -> None:
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
    execution = asyncio.run(DagExecutor(max_concurrency=2).execute(plan, handler, precompleted={"root": {"done": True}}))
    wall = (perf_counter() - started) * 1000.0
    assert wall < 425.0
    assert execution.metrics.peak_concurrency == 2
    assert execution.metrics.serial_work_ms >= 450.0
    assert execution.metrics.critical_path_ms < execution.metrics.serial_work_ms
    assert execution.metrics.parallel_efficiency > 0.5


def test_repository_persists_calibration_memory_falsifier_and_identity(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'state.db'}"
    repo = Repository(url)
    candidate = default_candidates()[0]
    factory = MiMicusEngine(url).services.agent_factory
    identity = factory.identity_for(candidate)
    repo.register_identity(identity)
    row = {}
    for _ in range(3):
        row = repo.record_calibration(candidate.fingerprint, "finance", predicted_probability=0.9, outcome=False, canary=True)
    assert row["attempts"] == 3 and row["canary_failure_streak"] == 3
    repo.set_bankruptcy_state(candidate.fingerprint, "finance", "BANKRUPT", "test")
    child = make_identity(
        provider=candidate.provider,
        model_family=candidate.model,
        phenotype=candidate.name,
        tool_policy_hash=candidate.tool_hash,
        runtime_model_version=candidate.runtime_model_version,
        phenotype_version=candidate.phenotype_version,
        system_prompt_hash="f" * 64,
        tool_manifest_hash=candidate.tool_hash,
        policy_hash=candidate.policy_hash,
        provider_adapter_version=candidate.provider_adapter_version,
        parent_fingerprint=candidate.fingerprint,
        declared_lineage_id=identity.lineage_id,
    )
    repo.register_identity(child)
    assert repo.lineage_has_bankrupt_predecessor(identity.lineage_id, "finance", exclude_fingerprint=child.fingerprint)
    item = MemoryItem(
        claim_hash="a" * 64,
        content="verified",
        owner_fingerprint=candidate.fingerprint,
        domain="finance",
        origin_clusters=["cluster-a"],
        authority=0.9,
        status=MemoryStatus.SHARED_VERIFIED,
        deterministic_verification=True,
        verified_clusters=["cluster-a"],
    )
    repo.save_memory_transition(item, reason="test promotion", from_status="private_verified")
    original = builtin_specs("finance")["F1"]
    spec = original.model_copy(update={"version": "9.9.9", "parent_hash": original.hash})
    repo.persist_falsifier(spec, lifecycle_state="PROMOTE", domain="finance", decision={"test": True})
    reopened = Repository(url)
    assert reopened.calibration(candidate.fingerprint, "finance")["attempts"] == 3
    assert reopened.bankruptcy_state(candidate.fingerprint, "finance") == "BANKRUPT"
    assert reopened.eligible_memory("finance")[0].memory_id == item.memory_id
    assert any(saved.hash == spec.hash for saved in reopened.promoted_falsifiers("finance"))


def test_engine_restart_memory_reuse_and_falsifier_germinal_reuse(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'restart.db'}"
    engine1 = MiMicusEngine(url)
    base_fixture = {"claim_statement": "TAM", "claim_type": "numeric", "price": 10.0, "users": 100.0, "price_period": "monthly", "claimed": 1000.0}
    first = engine1.run(RunRequest(task="K3 TAM 12x mismatch", domain="finance", scenario="tam_12x", fixture=base_fixture, learn=True))
    assert first.memory_changes and first.memory_changes[0]["status"] == "shared_verified"
    engine2 = MiMicusEngine(url)
    second = engine2.run(RunRequest(task="K3 TAM 12x mismatch", domain="finance", scenario="tam_12x", fixture=base_fixture))
    assert first.memory_changes[0]["memory_id"] in second.persistent_memory_reused
    fetched = engine2.get_run(first.run_id)
    assert fetched is not None and fetched["replay_state"]["verified"] is True
    evasion_fixture = {
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
    promoted = engine2.run(RunRequest(task="TAM slight mismatch", domain="finance", scenario="tam_12x", fixture=evasion_fixture, learn=True))
    assert promoted.germinal_changes and promoted.germinal_changes[0]["status"] == "PROMOTE"
    engine3 = MiMicusEngine(url)
    reuse_fixture = {key: value for key, value in evasion_fixture.items() if key != "confirmed_evasion"}
    reused = engine3.run(RunRequest(task="TAM slight mismatch", domain="finance", scenario="tam_12x", fixture=reuse_fixture))
    assert reused.persistent_falsifiers_reused
    assert reused.falsifiers[0]["verdict"] == "FAIL"


def test_bankruptcy_enforcement_whitewash_probation_and_recovery(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'bankrupt.db'}"
    probe = MiMicusEngine(url)
    base = probe.services.agent_factory.candidates()[0]
    identity = probe.services.agent_factory.identity_for(base)
    fail_fixture = {"claim_statement": "x", "claim_type": "numeric", "price": 1, "users": 1, "claimed": 10, "audition_fail_names": [base.name]}
    for _ in range(3):
        probe.run(RunRequest(task="numeric mismatch", domain="finance", scenario="tam_12x", fixture=fail_fixture))
    assert probe.repository.bankruptcy_state(base.fingerprint, "finance") == "BANKRUPT"
    child_identity = make_identity(
        provider=base.provider,
        model_family=base.model,
        phenotype=base.name,
        tool_policy_hash=base.tool_hash,
        runtime_model_version=base.runtime_model_version,
        phenotype_version=base.phenotype_version,
        system_prompt_hash="c" * 64,
        tool_manifest_hash=base.tool_hash,
        policy_hash=base.policy_hash,
        provider_adapter_version=base.provider_adapter_version,
        parent_fingerprint=base.fingerprint,
        declared_lineage_id=identity.lineage_id,
    )
    child_fp = child_identity.fingerprint
    revision = {
        "claim_statement": "x",
        "claim_type": "numeric",
        "price": 1,
        "users": 1,
        "claimed": 10,
        "identity_revisions": {base.name: {"system_prompt_hash": "c" * 64, "lineage_id": identity.lineage_id, "parent_fingerprint": base.fingerprint}},
    }
    whitewash = MiMicusEngine(url).run(RunRequest(task="numeric mismatch", domain="finance", scenario="tam_12x", fixture=revision))
    assert child_fp in whitewash.lineage_exclusions["probation"]
    assert child_fp not in whitewash.coalition["members"]
    revision["recovery_names"] = [base.name]
    recovered = MiMicusEngine(url).run(RunRequest(task="numeric mismatch", domain="finance", scenario="tam_12x", fixture=revision))
    assert child_fp not in recovered.lineage_exclusions["probation"]
    assert MiMicusEngine(url).repository.bankruptcy_state(child_fp, "finance") == "ACTIVE"


def test_sparse_communication_is_real_provider_work_and_plan_changes(tmp_path: Path) -> None:
    provider = ScriptedProvider()
    engine = MiMicusEngine(f"sqlite:///{tmp_path / 'comm.db'}", provider=provider)
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
    assert result.provider_call_count == provider.total_calls
    persisted = engine.get_run(result.run_id)
    assert persisted is not None and persisted["persistent_state"]["communications"]


def test_plugin_runtime_services_are_functional(tmp_path: Path) -> None:
    engine = MiMicusEngine(f"sqlite:///{tmp_path / 'plugin.db'}")
    services = engine.services
    assert isinstance(services.storage.repository, Repository)
    assert services.agent_factory.candidates()
    assert services.falsifiers.specs("x")
    assert services.sandbox.permits("numeric_invariant")
    assert not services.sandbox.permits("unknown")
    assert services.memory.retrieve("missing") == []
    threat = profile_task("numeric", "finance", "tam_12x")
    selected, _ = services.coalition.select(threat, services.agent_factory.candidates(), 2)
    assert selected
    services.telemetry.increment("x")
    assert services.telemetry.snapshot() == {"x": 1}
