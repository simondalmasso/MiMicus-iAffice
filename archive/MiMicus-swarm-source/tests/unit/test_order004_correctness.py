from __future__ import annotations

import asyncio

import pytest

from mimicus.agents.auditions import audition
from mimicus.agents.calibration import CalibrationLedger, capability_scope
from mimicus.agents.identity import exact_fingerprint
from mimicus.claims.evidence import evidence_row, fixture_evidence
from mimicus.coalition.selector import AgentCandidate, correlation
from mimicus.coalition.threat_profile import ThreatProfile
from mimicus.falsifiers.builtins import builtin_specs
from mimicus.falsifiers.market import FalsifierMarket, falsifier_proximity, falsifier_signature
from mimicus.orchestration.budget import BudgetLedger
from mimicus.orchestration.dag_executor import DagExecutionError, DagExecutor
from mimicus.orchestration.morphology import DagNode, MorphologyName, MorphologyPlan, NodeKind, compile_morphology
from mimicus.plugins.services import BuiltinAgentFactory
from mimicus.providers.base import ProviderCapabilities


def test_specialist_na_does_not_create_failure() -> None:
    result = audition(
        "critic-fp",
        "research",
        "temporal_decoy",
        "irrelevant",
        capability="freshness",
        test_family="freshness_canary",
        supported=False,
    )
    assert result.applicability == "NOT_APPLICABLE"
    assert result.passed is None
    assert result.score == 0.5
    assert result.affects_trust is False


def test_capability_calibration_is_not_domain_collapsed() -> None:
    ledger = CalibrationLedger()
    for _ in range(3):
        ledger.record_capability_verified(
            "agent",
            "research",
            "freshness",
            "freshness_canary",
            predicted_probability=0.8,
            outcome=False,
        )
    entailment = ledger.get_capability("agent", "research", "entailment", "entailment_canary")
    freshness = ledger.get_capability("agent", "research", "freshness", "freshness_canary")
    assert freshness.failures == 3
    assert entailment.attempts == 0
    assert entailment.trust == 0.5
    assert capability_scope("research", "freshness", "freshness_canary") != capability_scope("research", "entailment", "entailment_canary")


def _fingerprint(**updates: str) -> str:
    values = {
        "provider": "openai_agents",
        "model": "gpt-test",
        "model_version": "configured:gpt-test",
        "phenotype": "critic-1",
        "phenotype_version": "critic-v2.1",
        "system_prompt_hash": "a" * 64,
        "tool_manifest_hash": "b" * 64,
        "policy_hash": "c" * 64,
        "provider_adapter_version": "adapter-v2.1",
    }
    values.update(updates)
    return exact_fingerprint(**values)


@pytest.mark.parametrize(
    "mutation",
    [
        {"system_prompt_hash": "d" * 64},
        {"tool_manifest_hash": "e" * 64},
        {"provider": "other-provider"},
        {"model": "other-model"},
        {"model_version": "configured:other-model"},
        {"phenotype_version": "critic-v2.2"},
        {"policy_hash": "f" * 64},
        {"provider_adapter_version": "adapter-v3"},
    ],
)
def test_material_identity_changes_exact_fingerprint(mutation: dict[str, str]) -> None:
    assert _fingerprint() != _fingerprint(**mutation)


def test_runtime_capabilities_drive_factory_identity_and_shared_model_correlation() -> None:
    caps = ProviderCapabilities(
        provider_id="openai_agents",
        model_id="gpt-current",
        version="configured:gpt-current",
        adapter_version="openai-adapter-v2.1",
    )
    factory = BuiltinAgentFactory(caps)
    candidates = factory.candidates()
    assert {candidate.provider for candidate in candidates} == {"openai_agents"}
    assert {candidate.model for candidate in candidates} == {"gpt-current"}
    assert {candidate.runtime_model_version for candidate in candidates} == {"configured:gpt-current"}
    assert all(factory.identity_for(candidate).provider_adapter_version == "openai-adapter-v2.1" for candidate in candidates)
    assert correlation(candidates[0], candidates[1]) >= 0.55
    assert candidates[0].fingerprint != candidates[1].fingerprint


def test_correlation_does_not_treat_empty_policy_defaults_as_shared_material() -> None:
    left = AgentCandidate("a", "left", frozenset({"x"}), "p1", "m1", "x", "x")
    right = AgentCandidate("b", "right", frozenset({"y"}), "p2", "m2", "y", "y")
    assert correlation(left, right) == 0.0


def test_budget_race_allows_only_one_last_unit_reservation() -> None:
    async def run() -> tuple[int, dict[str, object]]:
        ledger = BudgetLedger(1.0)
        results = await asyncio.gather(
            ledger.reserve("agent_generation", 1.0),
            ledger.reserve("challenge", 1.0),
        )
        return sum(result is not None for result in results), ledger.snapshot()

    won, snapshot = asyncio.run(run())
    assert won == 1
    assert snapshot["estimated_or_reserved_usd"] == 1.0
    assert snapshot["remaining_usd"] == 0.0


def test_budget_reconcile_unknown_and_release_are_fail_closed() -> None:
    async def run() -> dict[str, object]:
        ledger = BudgetLedger(2.0)
        first = await ledger.reserve("agent_generation", 0.75)
        assert first is not None
        unknown = await ledger.reconcile(first, None)
        assert unknown["status"] == "UNKNOWN"
        second = await ledger.reserve("challenge", 0.5)
        assert second is not None
        released = await ledger.release(second, reason="cancelled sibling")
        assert released["released"] is True
        return ledger.snapshot()

    snapshot = asyncio.run(run())
    assert snapshot["actual_usd"] == "UNKNOWN"
    assert snapshot["unknown_cost_reserved_usd"] == 0.75
    assert snapshot["outstanding_reserved_usd"] == 0.0
    assert snapshot["remaining_usd"] == 1.25


def test_budget_provider_overrun_stops_future_paid_work() -> None:
    async def run() -> tuple[dict[str, object], object]:
        ledger = BudgetLedger(1.0)
        reservation = await ledger.reserve("agent_generation", 0.5)
        assert reservation is not None
        reconciled = await ledger.reconcile(reservation, 1.1)
        blocked = await ledger.reserve("challenge", 0.0, known_zero_cost=True)
        return reconciled, blocked

    reconciled, blocked = asyncio.run(run())
    assert reconciled["fail_closed"] is True
    assert reconciled["provider_overrun_usd"] == pytest.approx(0.6)
    assert blocked is None


def test_budget_rejects_negative_values_and_duplicate_reconcile() -> None:
    with pytest.raises(ValueError):
        BudgetLedger(-1)

    async def run() -> None:
        ledger = BudgetLedger(1)
        with pytest.raises(ValueError):
            await ledger.reserve("x", -0.1)
        reservation = await ledger.reserve("x", 0.1)
        assert reservation is not None
        with pytest.raises(ValueError):
            await ledger.reconcile(reservation, -0.1)

    asyncio.run(run())


def test_falsifier_near_duplicates_compete_as_substitutes() -> None:
    base = builtin_specs("finance")["F1"]
    clone = base.model_copy(update={"id": "F1.clone", "version": "1.0.1"})
    selected, scores = FalsifierMarket().select([base, clone], budget_usd=1.0, max_tests=2)
    assert len(selected) == 1
    assert falsifier_proximity(base, clone) >= 0.8
    assert any(score.retention_reason == "near_duplicate_substitute" for score in scores)
    assert falsifier_signature(base).hash


def test_complementary_falsifiers_remain_eligible() -> None:
    specs = builtin_specs("research")
    selected, scores = FalsifierMarket().select([specs["F1"], specs["F3"]], budget_usd=1.0, max_tests=2)
    assert {spec.primitive for spec in selected} == {"numeric_invariant", "source_independence"}
    assert all(score.utility >= 0 for score in scores)


def _compile(name: MorphologyName) -> MorphologyPlan:
    counts = {
        MorphologyName.SOLO: ["a"],
        MorphologyName.PAIRED_VERIFY: ["a", "b"],
        MorphologyName.PARALLEL_FANOUT: ["a", "b", "c"],
        MorphologyName.SPARSE_GRAPH: ["a", "b", "c"],
        MorphologyName.HIERARCHICAL_FANOUT_FANIN: ["a", "b", "c", "d"],
    }
    return compile_morphology(
        task_hash="1" * 64,
        selected_fingerprints=counts[name],
        falsifier_hashes=["f" * 64],
        complexity=0.9,
        required_capabilities=("source", "freshness", "entailment"),
        max_concurrency=4,
        learn=False,
        force_sparse=name == MorphologyName.SPARSE_GRAPH,
        hierarchical=name == MorphologyName.HIERARCHICAL_FANOUT_FANIN,
        morphology_override=name,
    )


def test_all_advertised_morphologies_have_distinct_structural_signatures() -> None:
    plans = {name: _compile(name) for name in MorphologyName}
    signatures = {name: plan.structural_signature for name, plan in plans.items()}
    assert len(set(signatures.values())) == 5
    assert NodeKind.DECOMPOSE in {node.kind for node in plans[MorphologyName.HIERARCHICAL_FANOUT_FANIN].nodes}
    assert NodeKind.CHALLENGE in {node.kind for node in plans[MorphologyName.PAIRED_VERIFY].nodes}
    assert NodeKind.CHALLENGE in {node.kind for node in plans[MorphologyName.SPARSE_GRAPH].nodes}
    assert NodeKind.CHALLENGE not in {node.kind for node in plans[MorphologyName.PARALLEL_FANOUT].nodes}
    assert sum(node.kind == NodeKind.AGENT_TASK for node in plans[MorphologyName.SOLO].nodes) == 1


def test_morphology_validation_rejects_cycle_and_missing_parent() -> None:
    missing = MorphologyPlan(MorphologyName.SOLO, [DagNode("a", NodeKind.AGENT_TASK, ("missing",))], [])
    with pytest.raises(ValueError, match="missing prerequisite"):
        missing.validate()


def test_structured_cancellation_cancels_and_awaits_sibling() -> None:
    fast = DagNode("fast", NodeKind.AGENT_TASK, ("root",))
    slow = DagNode("slow", NodeKind.AGENT_TASK, ("root",))
    plan = MorphologyPlan(
        MorphologyName.PARALLEL_FANOUT,
        [DagNode("root", NodeKind.PROFILE), fast, slow, DagNode("join", NodeKind.JOIN, ("fast", "slow"))],
        [],
    )
    cancelled = asyncio.Event()
    side_effect = {"happened": False}

    async def handler(node: DagNode) -> object:
        if node.node_id == "fast":
            await asyncio.sleep(0.01)
            raise RuntimeError("fatal")
        if node.node_id == "slow":
            try:
                await asyncio.sleep(0.3)
                side_effect["happened"] = True
            except asyncio.CancelledError:
                cancelled.set()
                raise
        return node.node_id

    async def run() -> None:
        with pytest.raises(DagExecutionError) as exc:
            await DagExecutor(2).execute(plan, handler, precompleted={"root": "done"})
        assert "fast" in exc.value.failed_nodes
        assert "slow" in exc.value.cancelled_nodes
        assert cancelled.is_set()
        await asyncio.sleep(0.35)
        assert side_effect["happened"] is False
        assert fast.status == "FAILED"
        assert slow.status == "CANCELLED"

    asyncio.run(run())


def test_evidence_hash_is_immutable_and_run_scoped() -> None:
    items = fixture_evidence(
        {"price": 10.0, "users": 2.0, "claimed": 240.0, "price_period": "monthly"},
        domain="finance",
        scenario="numeric",
    )
    assert len(items) == 1
    a = evidence_row(items[0], run_id="run-a")
    b = evidence_row(items[0], run_id="run-b")
    raw = evidence_row(items[0])
    assert a["canonical_evidence_hash"] == b["canonical_evidence_hash"] == raw["evidence_hash"]
    assert a["evidence_hash"] != b["evidence_hash"]
    assert a["snapshot_hash"] == b["snapshot_hash"]


def test_threat_profile_fixture_for_distinct_capabilities() -> None:
    profile = ThreatProfile(domain="research", threats=("x",), required_capabilities=("freshness", "entailment"), complexity=0.8)
    factory = BuiltinAgentFactory(ProviderCapabilities(provider_id="p", model_id="m", version="v", adapter_version="a"))
    candidates = factory.candidates()
    assert any("freshness" in candidate.capabilities for candidate in candidates)
    assert any("entailment" in candidate.capabilities for candidate in candidates)
    assert profile.required_capabilities == ("freshness", "entailment")


def test_completion_driven_scheduler_releases_child_before_unrelated_sibling() -> None:
    a = DagNode("a", NodeKind.AGENT_TASK, ("root",))
    b = DagNode("b", NodeKind.AGENT_TASK, ("root",))
    a1 = DagNode("a1", NodeKind.AGENT_TASK, ("a",))
    join = DagNode("join-live", NodeKind.JOIN, ("a1", "b"))
    plan = MorphologyPlan(
        MorphologyName.PARALLEL_FANOUT,
        [DagNode("root", NodeKind.PROFILE), a, b, a1, join],
        [],
    )

    release_a = asyncio.Event()
    release_b = asyncio.Event()
    a_started = asyncio.Event()
    b_started = asyncio.Event()
    a1_started = asyncio.Event()

    async def handler(node: DagNode) -> object:
        if node.node_id == "a":
            a_started.set()
            await release_a.wait()
            return "a-done"
        if node.node_id == "b":
            b_started.set()
            await release_b.wait()
            return "b-done"
        if node.node_id == "a1":
            a1_started.set()
            return "a1-done"
        return node.node_id

    async def run() -> None:
        execution = asyncio.create_task(
            DagExecutor(2).execute(plan, handler, precompleted={"root": "done"})
        )
        try:
            await asyncio.wait_for(a_started.wait(), timeout=2.0)
            await asyncio.wait_for(b_started.wait(), timeout=2.0)
            assert not a1_started.is_set()

            release_a.set()
            await asyncio.wait_for(a1_started.wait(), timeout=2.0)

            # The load-bearing assertion: A1 became eligible after A and began
            # while unrelated sibling B was deliberately still blocked.
            assert not release_b.is_set()
            assert not execution.done()
        finally:
            release_a.set()
            release_b.set()

        result = await asyncio.wait_for(execution, timeout=2.0)
        assert result.outputs["a1"] == "a1-done"
        assert result.metrics.peak_concurrency <= 2

    asyncio.run(run())
