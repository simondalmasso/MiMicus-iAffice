from __future__ import annotations

import asyncio
import json
import sys
import types
from pathlib import Path

from mimicus.agents.calibration import capability_scope
from mimicus.claims.models import Claim
from mimicus.orchestration.engine import MiMicusEngine, RunRequest
from mimicus.providers.base import ProviderRequest
from mimicus.providers.openai_agents import OpenAIAgentsProvider
from mimicus.providers.scripted import ScriptedProvider


def _db(tmp_path: Path, name: str) -> str:
    return f"sqlite:///{tmp_path / name}"


def test_specialist_auditions_are_capability_scoped_persistent_and_recoverable(tmp_path: Path) -> None:
    database = _db(tmp_path, "specialists.db")
    engine = MiMicusEngine(database)
    critic = next(candidate for candidate in engine.services.agent_factory.candidates() if candidate.name == "critic-1")
    source = next(candidate for candidate in engine.services.agent_factory.candidates() if candidate.name == "source-1")

    freshness_fixture = {
        "claim_statement": "dated observation",
        "claim_type": "temporal",
        "evidence_date": "2026-08-10T00:00:00+00:00",
        "as_of": "2026-08-17T00:00:00+00:00",
    }
    for _ in range(3):
        result = engine.run(
            RunRequest(
                task="Evaluate temporal freshness from supplied evidence",
                domain="research",
                scenario="freshness",
                fixture=freshness_fixture,
            )
        )
        assert source.fingerprint in result.coalition["members"]
    critic_entailment_scope = capability_scope("research", "entailment", "entailment_canary")
    assert engine.repository.calibration(critic.fingerprint, critic_entailment_scope)["attempts"] == 0

    entailment_fixture = {
        "claim_statement": "reported figure",
        "claim_type": "numeric",
        "claim_figure": 42,
        "evidence_spans": [{"span_id": "a", "supported_figures": [42], "material_support": True}],
    }
    selected = engine.run(
        RunRequest(
            task="Evaluate citation entailment for the supplied figure",
            domain="research",
            scenario="citation_entailment",
            fixture=entailment_fixture,
        )
    )
    assert critic.fingerprint in selected.coalition["members"]

    failing_fixture = entailment_fixture | {"audition_fail_capabilities": ["entailment"]}
    for _ in range(3):
        engine.run(
            RunRequest(
                task="Evaluate citation entailment for the supplied figure",
                domain="research",
                scenario="citation_entailment",
                fixture=failing_fixture,
            )
        )
    assert engine.repository.bankruptcy_state(critic.fingerprint, critic_entailment_scope) == "BANKRUPT"
    assert engine.repository.bankruptcy_state(critic.fingerprint, "research") == "BANKRUPT"

    restarted = MiMicusEngine(database)
    assert restarted.repository.bankruptcy_state(critic.fingerprint, critic_entailment_scope) == "BANKRUPT"
    excluded = restarted.run(
        RunRequest(
            task="Evaluate citation entailment for the supplied figure",
            domain="research",
            scenario="citation_entailment",
            fixture=entailment_fixture,
        )
    )
    assert critic.fingerprint not in excluded.coalition["members"]

    recovered = restarted.run(
        RunRequest(
            task="Evaluate citation entailment for the supplied figure",
            domain="research",
            scenario="citation_entailment",
            fixture=entailment_fixture | {"recovery_names": ["critic-1"]},
        )
    )
    assert restarted.repository.bankruptcy_state(critic.fingerprint, critic_entailment_scope) == "ACTIVE"
    assert restarted.repository.bankruptcy_state(critic.fingerprint, "research") == "ACTIVE"
    assert critic.fingerprint in recovered.coalition["members"]


def test_openai_adapter_consumes_bounded_verified_memory_in_structured_input(monkeypatch) -> None:
    captured: dict[str, object] = {}
    module = types.ModuleType("agents")

    class Agent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.name = kwargs["name"]

    class Result:
        final_output = Claim(statement="structured", domain="research", probability=0.7)
        last_agent = types.SimpleNamespace(name="mimicus-critic-1")
        context_wrapper = types.SimpleNamespace(usage=types.SimpleNamespace(input_tokens=100, output_tokens=20, total_tokens=120))

    class Runner:
        @staticmethod
        async def run(agent, task, max_turns):
            captured["task"] = task
            captured["agent"] = agent
            captured["max_turns"] = max_turns
            return Result()

    module.Agent = Agent
    module.Runner = Runner
    monkeypatch.setitem(sys.modules, "agents", module)
    provider = OpenAIAgentsProvider(
        "gpt-test",
        input_usd_per_million_tokens=1.0,
        output_usd_per_million_tokens=2.0,
        max_memory_items=2,
    )
    memory = (
        {
            "memory_id": "eligible-1",
            "claim_hash": "a" * 64,
            "content": "verified institutional fact",
            "authority": 0.9,
            "origin_clusters": ["origin-a"],
            "verified_clusters": ["origin-a"],
            "status": "shared_verified",
        },
        {
            "memory_id": "blocked",
            "claim_hash": "b" * 64,
            "content": "quarantined poison",
            "authority": 1.0,
            "origin_clusters": ["bad"],
            "verified_clusters": [],
            "status": "quarantined",
        },
        {
            "memory_id": "eligible-2",
            "claim_hash": "c" * 64,
            "content": "second verified fact",
            "authority": 0.8,
            "origin_clusters": ["origin-c"],
            "verified_clusters": ["origin-c"],
            "status": "private_verified",
        },
    )
    response = asyncio.run(
        provider.generate_request_async(
            ProviderRequest(
                task="evaluate",
                domain="research",
                phenotype="critic-1",
                sealed_context_id="sealed",
                fixture={},
                verified_memory=memory,
            )
        )
    )
    body = json.loads(str(captured["task"]))
    ids = [item["memory_id"] for item in body["verified_institutional_memory"]]
    assert ids == ["eligible-1", "eligible-2"]
    assert "blocked" not in str(captured["task"])
    assert body["sealed_first_pass"] is True
    assert body["peer_outputs_included"] is False
    assert response.usage["verified_memory_items_consumed"] == 2
    assert response.cost == 0.00014
    assert response.usage["monetary_cost_status"] == "KNOWN"


def test_openai_adapter_marks_monetary_cost_unknown_without_authoritative_pricing(monkeypatch) -> None:
    module = types.ModuleType("agents")

    class Agent:
        def __init__(self, **kwargs):
            self.name = kwargs["name"]

    class Runner:
        @staticmethod
        async def run(agent, task, max_turns):
            return types.SimpleNamespace(
                final_output=Claim(statement="x", domain="test", probability=0.5),
                last_agent=types.SimpleNamespace(name=agent.name),
                context_wrapper=types.SimpleNamespace(usage=types.SimpleNamespace(input_tokens=10, output_tokens=5, total_tokens=15)),
            )

    module.Agent = Agent
    module.Runner = Runner
    monkeypatch.setitem(sys.modules, "agents", module)
    response = asyncio.run(OpenAIAgentsProvider("gpt-test").generate_request_async(ProviderRequest("task", "test", "critic-1", "sealed", {}, ())))
    assert response.cost is None
    assert response.usage["monetary_cost_status"] == "UNKNOWN"


def test_budget_zero_blocks_paid_provider_work(tmp_path: Path) -> None:
    provider = ScriptedProvider(default_cost=0.01, challenge_cost=0.01)
    result = MiMicusEngine(_db(tmp_path, "zero-budget.db"), provider=provider).run(RunRequest(task="numeric consistency", domain="finance", scenario="tam_12x", budget_usd=0.0))
    assert provider.total_calls == 0
    assert result.provider_call_count == 0
    assert result.status == "inconclusive"
    assert result.budget["known_actual_usd"] == 0.0


def test_challenge_cannot_bypass_exhausted_budget(tmp_path: Path) -> None:
    provider = ScriptedProvider(default_cost=0.005, challenge_cost=0.005)
    fixture = {
        "claim_statement": "evidence set",
        "claim_type": "factual",
        "agent_cost": 0.005,
        "challenge_cost": 0.005,
        "force_sparse": True,
        "agent_probabilities": {"source-1": 0.9, "critic-1": 0.1},
    }
    result = MiMicusEngine(_db(tmp_path, "challenge-budget.db"), provider=provider).run(
        RunRequest(
            task="source citation figure evidence",
            domain="research",
            scenario="general",
            fixture=fixture,
            budget_usd=0.01,
            max_agents=2,
        )
    )
    assert provider.generate_calls == 2
    assert provider.challenge_calls == 0
    assert result.challenge_edge_count == 0
    assert result.status == "inconclusive"
    assert result.budget["known_actual_usd"] == 0.01
    assert result.budget["remaining_usd"] == 0.0


def test_evidence_persists_and_all_claim_refs_resolve_after_restart(tmp_path: Path) -> None:
    database = _db(tmp_path, "evidence.db")
    first = MiMicusEngine(database)
    result = first.run(
        RunRequest(
            task="numeric annualized consistency",
            domain="finance",
            scenario="tam_12x",
            fixture={
                "claim_statement": "annual amount",
                "claim_type": "numeric",
                "price": 10.0,
                "users": 10.0,
                "price_period": "monthly",
                "claimed": 1000.0,
            },
        )
    )
    assert result.final_claims
    refs = set(result.final_claims[0]["evidence_refs"])
    assert refs
    restarted = MiMicusEngine(database)
    fetched = restarted.get_run(result.run_id)
    assert fetched is not None
    persisted = fetched["evidence"]
    hashes = {row["evidence_hash"] for row in persisted}
    assert refs <= hashes
    resolved = restarted.repository.resolve_evidence(result.run_id, sorted(refs))
    assert set(resolved) == refs
    assert all(row["snapshot_hash"] for row in resolved.values())
    assert fetched["replay_state"]["verified"] is True


def test_evidence_rows_do_not_collide_across_repeated_runs(tmp_path: Path) -> None:
    database = _db(tmp_path, "evidence-repeat.db")
    engine = MiMicusEngine(database)
    request = RunRequest(
        task="numeric consistency repeated",
        domain="finance",
        scenario="tam_12x",
        fixture={"claim_statement": "x", "claim_type": "numeric", "price": 1.0, "users": 1.0, "claimed": 12.0, "price_period": "monthly"},
    )
    first = engine.run(request)
    second = engine.run(request)
    assert first.run_id != second.run_id
    first_hashes = {row["evidence_hash"] for row in engine.repository.get_evidence(first.run_id)}
    second_hashes = {row["evidence_hash"] for row in engine.repository.get_evidence(second.run_id)}
    assert first_hashes
    assert second_hashes
    assert first_hashes.isdisjoint(second_hashes)
