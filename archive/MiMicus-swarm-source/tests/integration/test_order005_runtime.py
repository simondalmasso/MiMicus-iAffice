from __future__ import annotations

import asyncio
import json
import sys
import types
from pathlib import Path

from mimicus.agents.calibration import capability_scope
from mimicus.claims.evidence_bundle import EvidenceInput, runtime_evidence_bundle
from mimicus.claims.models import Claim
from mimicus.orchestration.engine import MiMicusEngine, RunRequest
from mimicus.providers.base import Provider, ProviderCapabilities, ProviderRequest, ProviderResponse
from mimicus.providers.openai_agents import OpenAIAgentsProvider


class CitingProvider(Provider):
    def __init__(self, *, cost: float = 0.0, max_cost: float | None = 0.0, known_zero: bool = True) -> None:
        self.calls = 0
        self.cost = cost
        self._caps = ProviderCapabilities(
            provider_id="citing",
            model_id="fixture",
            version="1",
            adapter_version="citing-v1",
            known_zero_cost=known_zero,
            estimated_max_cost_per_call=max_cost,
            pricing_metadata_authoritative=max_cost is not None,
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._caps

    async def generate_request_async(self, request: ProviderRequest) -> ProviderResponse:
        self.calls += 1
        refs = [str(request.evidence[0]["evidence_hash"]), "f" * 64] if request.evidence else ["f" * 64]
        return ProviderResponse(
            claim=Claim(statement="provider claim", domain=request.domain, probability=0.7, claim_type="factual", evidence_refs=refs),
            cost=self.cost,
            latency_ms=1.0,
            trace_id=f"call-{self.calls}",
            usage={"source": "test"},
        )


class UnknownCostProvider(CitingProvider):
    def __init__(self) -> None:
        super().__init__(cost=0.0, max_cost=None, known_zero=False)


class KnownCostProvider(CitingProvider):
    def __init__(self, cost: float = 0.01) -> None:
        super().__init__(cost=cost, max_cost=cost, known_zero=False)


def _evidence() -> list[EvidenceInput]:
    return [
        EvidenceInput(
            origin="caller://report-a",
            independence_cluster="publisher-a",
            content="Public report A",
            extracted_facts={"clusters": ["publisher-a", "publisher-b"], "texts": ["A", "B"]},
        ),
        EvidenceInput(
            origin="caller://report-b",
            independence_cluster="publisher-b",
            content="Public report B",
            extracted_facts={},
        ),
    ]


def test_words_only_runtime_cannot_activate_synthetic_evidence(tmp_path: Path) -> None:
    engine = MiMicusEngine(f"sqlite:///{tmp_path / 'words.db'}")
    probes = [
        "TAM numeric price revenue 12x mismatch",
        "fresh current stale date evidence",
        "source echo origin citation report",
        "citation figure entailment mismatch",
        "absence counterexample none exist registry",
    ]
    for task in probes:
        result = engine.run(RunRequest(task=task, domain="audit"))
        assert result.status == "inconclusive"
        assert result.evidence_provenance["source_mode"] == "runtime"
        assert result.evidence_provenance["provider_input_evidence_hashes"] == []
        assert all(row["verdict"] == "INCONCLUSIVE" for row in result.falsifiers)
        assert "evidence_missing" in result.event_types
        assert all(claim["evidence_refs"] == [] for claim in result.final_claims)


def test_provider_refs_are_bound_to_supplied_evidence_and_resolve_after_restart(tmp_path: Path) -> None:
    database = f"sqlite:///{tmp_path / 'binding.db'}"
    provider = CitingProvider()
    engine = MiMicusEngine(database, provider=provider)
    result = engine.run(RunRequest(task="plain synthesis", domain="general", evidence=_evidence(), max_agents=1))
    assert provider.calls == 1
    assert result.final_claims
    refs = result.final_claims[0]["evidence_refs"]
    assert len(refs) == 1 and refs[0] in result.evidence_provenance["provider_input_evidence_hashes"]
    usage = result.evidence_provenance["provider_usages"][0]["usage"]
    assert usage["evidence_refs_claimed"] == [refs[0], "f" * 64]
    assert usage["evidence_refs_validated"] == refs
    assert usage["evidence_refs_rejected"] == ["f" * 64]
    assert "evidence_ref_rejected" in result.event_types
    restarted = MiMicusEngine(database, provider=CitingProvider())
    fetched = restarted.get_run(result.run_id)
    assert fetched is not None and fetched["replay_state"]["verified"] is True
    resolved = restarted.repository.resolve_evidence(result.run_id, refs)
    assert list(resolved) == refs
    assert resolved[refs[0]]["snapshot_hash"]


def test_openai_adapter_receives_canonical_evidence_and_excludes_blocked_memory(monkeypatch) -> None:
    captured: dict[str, object] = {}
    agents_module = types.ModuleType("agents")

    class Agent:
        def __init__(self, **kwargs):
            self.name = kwargs["name"]

    class Runner:
        @staticmethod
        async def run(agent, task, max_turns):
            captured["task"] = task
            body = json.loads(task)
            valid = body["runtime_evidence"][0]["evidence_hash"]
            return types.SimpleNamespace(
                final_output=Claim(statement="bound", domain="research", probability=0.8, claim_type="factual", evidence_refs=[valid, "e" * 64]),
                last_agent=types.SimpleNamespace(name=agent.name),
                context_wrapper=types.SimpleNamespace(usage=types.SimpleNamespace(input_tokens=10, output_tokens=5, total_tokens=15)),
            )

    agents_module.Agent = Agent
    agents_module.Runner = Runner
    monkeypatch.setitem(sys.modules, "agents", agents_module)
    provider = OpenAIAgentsProvider("gpt-mock")
    bundle = runtime_evidence_bundle("run-mock", _evidence())
    request = ProviderRequest(
        task="evaluate",
        domain="research",
        phenotype="source-1",
        sealed_context_id="sealed",
        fixture={},
        verified_memory=(
            {"memory_id": "ok", "claim_hash": "a" * 64, "content": "verified", "authority": 0.9, "status": "shared_verified", "origin_clusters": ["a"], "verified_clusters": ["a"]},
            {
                "memory_id": "bad",
                "claim_hash": "b" * 64,
                "content": "quarantined poison",
                "authority": 1.0,
                "status": "quarantined",
                "origin_clusters": ["x"],
                "verified_clusters": [],
            },
        ),
        evidence=bundle.provider_payload(),
    )
    response = asyncio.run(provider.generate_request_async(request))
    body = json.loads(str(captured["task"]))
    assert len(body["runtime_evidence"]) == 2
    assert [row["memory_id"] for row in body["verified_institutional_memory"]] == ["ok"]
    assert "quarantined poison" not in str(captured["task"])
    valid = body["runtime_evidence"][0]["evidence_hash"]
    assert response.claim.evidence_refs == [valid]
    assert response.usage["evidence_refs_rejected"] == ["e" * 64]


def test_capability_bankruptcy_is_conditional_and_persists(tmp_path: Path) -> None:
    database = f"sqlite:///{tmp_path / 'skills.db'}"
    engine = MiMicusEngine(database)
    source = next(candidate for candidate in engine.services.agent_factory.candidates() if candidate.name == "source-1")
    fixture = {
        "clusters": ["publisher-a", "publisher-b"],
        "texts": ["A", "B"],
        "evidence_date": "2026-08-17T00:00:00+00:00",
        "as_of": "2026-08-18T00:00:00+00:00",
        "audition_fail_capabilities": ["independence"],
    }
    result = None
    for _ in range(3):
        result = engine.run(RunRequest(task="fresh source echo origin", domain="research", scenario="general", source_mode="fixture", fixture=fixture))
    assert result is not None
    fresh_scope = capability_scope("research", "freshness", "freshness_canary")
    independent_scope = capability_scope("research", "independence", "independence_canary")
    assert engine.repository.bankruptcy_state(source.fingerprint, fresh_scope) == "ACTIVE"
    assert engine.repository.bankruptcy_state(source.fingerprint, independent_scope) == "BANKRUPT"
    authority = result.coalition["rationale"]["capability_authority"][source.fingerprint]
    assert authority["freshness"]["state"] == "ACTIVE"
    assert authority["independence"]["state"] == "BANKRUPT"
    restarted = MiMicusEngine(database)
    assert restarted.repository.bankruptcy_state(source.fingerprint, fresh_scope) == "ACTIVE"
    assert restarted.repository.bankruptcy_state(source.fingerprint, independent_scope) == "BANKRUPT"


def test_unknown_cost_multicall_preflight_executes_no_partial_swarm(tmp_path: Path) -> None:
    provider = UnknownCostProvider()
    engine = MiMicusEngine(f"sqlite:///{tmp_path / 'unknown.db'}", provider=provider)
    result = engine.run(RunRequest(task="fresh source citation figure counterexample", domain="research", budget_usd=1.0, max_agents=4))
    preflight = result.evidence_provenance["pricing_preflight"]
    assert preflight["planned_paid_calls"] > 1
    assert preflight["status"] == "PRICING_PREFLIGHT_REQUIRED"
    assert provider.calls == 0
    assert result.provider_call_count == 0
    assert result.coalition["members"] == []
    assert "pricing_preflight_required" in result.event_types


def test_known_cost_preflight_degrades_before_execution(tmp_path: Path) -> None:
    provider = KnownCostProvider(0.01)
    engine = MiMicusEngine(f"sqlite:///{tmp_path / 'known.db'}", provider=provider)
    result = engine.run(RunRequest(task="fresh source citation figure counterexample", domain="research", budget_usd=0.01, max_agents=4))
    preflight = result.evidence_provenance["pricing_preflight"]
    assert preflight["planned_paid_calls"] > 1
    assert preflight["status"] == "DEGRADED_BEFORE_EXECUTION"
    assert len(result.coalition["members"]) == 1
    assert provider.calls == 1
    assert result.provider_call_count == 1
