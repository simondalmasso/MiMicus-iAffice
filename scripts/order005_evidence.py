from __future__ import annotations

import json
import tempfile
from dataclasses import replace
from pathlib import Path
from typing import Any

from mimicus.agents.calibration import capability_scope
from mimicus.agents.identity import exact_fingerprint_from_manifest
from mimicus.claims.evidence_bundle import EvidenceInput
from mimicus.claims.models import Claim
from mimicus.orchestration.engine import MiMicusEngine, RunRequest
from mimicus.plugins.services import BuiltinAgentFactory
from mimicus.providers.base import Provider, ProviderCapabilities, ProviderRequest, ProviderResponse
from mimicus.providers.openai_agents import OpenAIAgentsProvider
from mimicus.storage.repository import Repository


def _write(root: Path, name: str, payload: dict[str, Any]) -> None:
    (root / name).write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")


class BindingProvider(Provider):
    def __init__(self) -> None:
        self.calls = 0
        self._caps = ProviderCapabilities(
            provider_id="order005-binding",
            model_id="fixture",
            version="1",
            adapter_version="binding-v1",
            known_zero_cost=True,
            estimated_max_cost_per_call=0.0,
            pricing_metadata_authoritative=True,
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._caps

    async def generate_request_async(self, request: ProviderRequest) -> ProviderResponse:
        self.calls += 1
        valid = str(request.evidence[0]["evidence_hash"]) if request.evidence else ""
        refs = [valid, "f" * 64] if valid else ["f" * 64]
        return ProviderResponse(
            claim=Claim(statement="provider claim", domain=request.domain, probability=0.71, claim_type="factual", evidence_refs=refs),
            cost=0.0,
            latency_ms=1.0,
            trace_id=f"binding-{self.calls}",
            usage={"provider": "order005-binding"},
        )


class CostProvider(Provider):
    def __init__(self, max_cost: float | None, actual_cost: float = 0.0) -> None:
        self.calls = 0
        self.actual_cost = actual_cost
        self._caps = ProviderCapabilities(
            provider_id="order005-cost",
            model_id="fixture",
            version="1",
            adapter_version="cost-v1",
            known_zero_cost=False,
            estimated_max_cost_per_call=max_cost,
            pricing_metadata_authoritative=max_cost is not None,
        )

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self._caps

    async def generate_request_async(self, request: ProviderRequest) -> ProviderResponse:
        self.calls += 1
        return ProviderResponse(
            claim=Claim(statement="paid claim", domain=request.domain, probability=0.6, claim_type="factual"),
            cost=self.actual_cost,
            latency_ms=1.0,
            trace_id=f"paid-{self.calls}",
            usage={},
        )


def no_synthetic_runtime(root: Path) -> dict[str, Any]:
    probes = [
        "TAM numeric price revenue 12x mismatch",
        "fresh current stale date evidence",
        "source echo origin citation report",
        "citation figure entailment mismatch",
        "absence counterexample none exist registry",
    ]
    rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="order005-nosynth-") as directory:
        engine = MiMicusEngine(f"sqlite:///{Path(directory) / 'runtime.db'}")
        for task in probes:
            result = engine.run(RunRequest(task=task, domain="audit"))
            verdicts = [row["verdict"] for row in result.falsifiers]
            passed = (
                result.status == "inconclusive"
                and result.evidence_provenance["source_mode"] == "runtime"
                and result.evidence_provenance["provider_input_evidence_hashes"] == []
                and bool(verdicts)
                and all(verdict == "INCONCLUSIVE" for verdict in verdicts)
                and "evidence_missing" in result.event_types
                and all(not claim["evidence_refs"] for claim in result.final_claims)
            )
            assert passed
            rows.append(
                {
                    "task": task,
                    "run_id": result.run_id,
                    "status": result.status,
                    "source_mode": result.evidence_provenance["source_mode"],
                    "provider_input_evidence_hashes": result.evidence_provenance["provider_input_evidence_hashes"],
                    "falsifier_verdicts": verdicts,
                    "evidence_missing_event": "evidence_missing" in result.event_types,
                    "pass": passed,
                }
            )
    payload = {"pass": all(row["pass"] for row in rows), "task_word_fixture_activation": False, "probes": rows}
    _write(root, "NO_SYNTHETIC_RUNTIME_EVIDENCE.json", payload)
    return payload


def identity_recompute(root: Path) -> dict[str, Any]:
    factory = BuiltinAgentFactory()
    identity = factory.identity_for(factory.candidates()[0])
    baseline = identity.material_manifest
    mutations = {
        "runtime_provider_id": "provider-mutated",
        "runtime_model_id": "model-mutated",
        "runtime_model_version": "runtime-mutated",
        "phenotype": "phenotype-mutated",
        "phenotype_version": "phenotype-version-mutated",
        "system_prompt_hash": "1" * 64,
        "tool_manifest_hash": "2" * 64,
        "policy_hash": "3" * 64,
        "provider_adapter_version": "adapter-mutated",
    }
    mutation_rows = {}
    for key, value in mutations.items():
        changed = dict(baseline)
        changed[key] = value
        mutated = exact_fingerprint_from_manifest(changed)
        assert mutated != identity.fingerprint
        mutation_rows[key] = {"fingerprint": mutated, "changed": True}
    repo = Repository("sqlite:///:memory:")
    repo.register_identity(identity)
    rejected = False
    try:
        repo.register_identity(replace(identity, fingerprint="0" * 64))
    except ValueError:
        rejected = True
    assert rejected
    state = repo.inspect_state("general")
    inspected = state["identities"][0]
    assert inspected["fingerprint_matches_manifest"] is True
    assert inspected["recomputed_fingerprint"] == identity.fingerprint
    payload = {
        "pass": True,
        "fingerprint": identity.fingerprint,
        "recomputed_fingerprint": identity.recompute_fingerprint(),
        "fingerprint_matches_manifest": identity.fingerprint_matches_manifest,
        "material_manifest": baseline,
        "material_mutations": mutation_rows,
        "forged_fingerprint_rejected": rejected,
        "inspection": inspected,
    }
    _write(root, "IDENTITY_FINGERPRINT_RECOMPUTE.json", payload)
    return payload


def provider_binding(root: Path) -> dict[str, Any]:
    evidence = [
        EvidenceInput(
            origin="caller://report-a", independence_cluster="publisher-a", content="Report A", extracted_facts={"clusters": ["publisher-a", "publisher-b"], "texts": ["A", "B"]}
        ),
        EvidenceInput(origin="caller://report-b", independence_cluster="publisher-b", content="Report B"),
    ]
    with tempfile.TemporaryDirectory(prefix="order005-binding-") as directory:
        database = f"sqlite:///{Path(directory) / 'binding.db'}"
        provider = BindingProvider()
        engine = MiMicusEngine(database, provider=provider)
        result = engine.run(RunRequest(task="plain synthesis", domain="general", evidence=evidence, max_agents=1))
        assert provider.calls == 1
        refs = list(result.final_claims[0]["evidence_refs"])
        usage = result.evidence_provenance["provider_usages"][0]["usage"]
        assert len(refs) == 1
        assert usage["evidence_refs_validated"] == refs
        assert usage["evidence_refs_rejected"] == ["f" * 64]
        assert set(refs) <= set(result.evidence_provenance["provider_input_evidence_hashes"])
        restarted = MiMicusEngine(database, provider=BindingProvider())
        fetched = restarted.get_run(result.run_id)
        assert fetched is not None and fetched["replay_state"]["verified"] is True
        resolved = restarted.repository.resolve_evidence(result.run_id, refs)
        assert set(resolved) == set(refs)
        restart_payload = {
            "pass": True,
            "run_id": result.run_id,
            "provider_input_evidence_hashes": result.evidence_provenance["provider_input_evidence_hashes"],
            "claim_evidence_refs": refs,
            "resolved_after_restart": sorted(resolved),
            "replay_verified": fetched["replay_state"]["verified"],
        }
    binding_payload = {
        "pass": True,
        "provider_calls": provider.calls,
        "supplied": usage["evidence_hashes_supplied"],
        "claimed": usage["evidence_refs_claimed"],
        "validated": usage["evidence_refs_validated"],
        "rejected": usage["evidence_refs_rejected"],
        "unknown_reference_rejected": True,
        "base_evidence_auto_attach": False,
    }
    _write(root, "PROVIDER_EVIDENCE_BINDING.json", binding_payload)
    _write(root, "EVIDENCE_RESTART_RESOLUTION.json", restart_payload)
    return binding_payload


def skill_authority(root: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="order005-skill-") as directory:
        database = f"sqlite:///{Path(directory) / 'skills.db'}"
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
        freshness_scope = capability_scope("research", "freshness", "freshness_canary")
        independence_scope = capability_scope("research", "independence", "independence_canary")
        freshness = engine.repository.bankruptcy_state(source.fingerprint, freshness_scope)
        independence = engine.repository.bankruptcy_state(source.fingerprint, independence_scope)
        authority = result.coalition["rationale"]["capability_authority"][source.fingerprint]
        restarted = MiMicusEngine(database)
        assert freshness == "ACTIVE" and independence == "BANKRUPT"
        assert restarted.repository.bankruptcy_state(source.fingerprint, freshness_scope) == "ACTIVE"
        assert restarted.repository.bankruptcy_state(source.fingerprint, independence_scope) == "BANKRUPT"
        payload = {
            "pass": True,
            "fingerprint": source.fingerprint,
            "freshness_state": freshness,
            "independence_state": independence,
            "freshness_authority": authority["freshness"],
            "independence_authority": authority["independence"],
            "restart_preserved": True,
            "domain_aggregate_grants_positive_authority": False,
        }
    _write(root, "SKILL_CONDITIONAL_AUTHORITY.json", payload)
    return payload


def capability_truth(root: Path) -> dict[str, Any]:
    class DummyTool:
        name = "source_lookup"
        description = "Explicit evidence acquisition tool"

    no_tools = OpenAIAgentsProvider("gpt-test")
    with_tools = OpenAIAgentsProvider("gpt-test", tools=(DummyTool(),))
    no_caps = no_tools.capabilities
    tool_caps = with_tools.capabilities
    no_fp = BuiltinAgentFactory(no_caps).candidates()[0].fingerprint
    tool_fp = BuiltinAgentFactory(tool_caps).candidates()[0].fingerprint
    assert no_caps.supports_tools is False and no_caps.evidence_acquisition_available is False
    assert tool_caps.supports_tools is True and tool_caps.evidence_acquisition_available is True
    assert no_caps.tool_manifest_hash != tool_caps.tool_manifest_hash and no_fp != tool_fp
    payload = {
        "pass": True,
        "without_tools": no_caps.__dict__,
        "with_tools": tool_caps.__dict__,
        "identity_without_tools": no_fp,
        "identity_with_tools": tool_fp,
        "tool_manifest_changes_identity": no_fp != tool_fp,
        "fake_web_by_prompt": False,
    }
    _write(root, "PROVIDER_CAPABILITY_TRUTH.json", payload)
    return payload


def pricing_preflight(root: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="order005-cost-") as directory:
        unknown = CostProvider(None)
        unknown_engine = MiMicusEngine(f"sqlite:///{Path(directory) / 'unknown.db'}", provider=unknown)
        unknown_result = unknown_engine.run(RunRequest(task="fresh source citation figure counterexample", domain="research", budget_usd=1.0, max_agents=4))
        unknown_preflight = unknown_result.evidence_provenance["pricing_preflight"]
        assert unknown_preflight["planned_paid_calls"] > 1
        assert unknown_preflight["status"] == "PRICING_PREFLIGHT_REQUIRED"
        assert unknown.calls == 0 and unknown_result.provider_call_count == 0

        known = CostProvider(0.01, 0.01)
        known_engine = MiMicusEngine(f"sqlite:///{Path(directory) / 'known.db'}", provider=known)
        known_result = known_engine.run(RunRequest(task="fresh source citation figure counterexample", domain="research", budget_usd=0.01, max_agents=4))
        known_preflight = known_result.evidence_provenance["pricing_preflight"]
        assert known_preflight["status"] == "DEGRADED_BEFORE_EXECUTION"
        assert known.calls == 1 and known_result.provider_call_count == 1
    payload = {
        "pass": True,
        "unknown_cost": {"preflight": unknown_preflight, "provider_calls": unknown.calls, "partial_swarm_executed": False},
        "known_insufficient": {"preflight": known_preflight, "provider_calls": known.calls, "degraded_before_execution": True},
        "false_zero_cost": False,
    }
    _write(root, "ONLINE_COST_PREFLIGHT.json", payload)
    return payload


def main() -> int:
    import sys

    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("evidence/ORDER-005")
    root.mkdir(parents=True, exist_ok=True)
    results = {
        "F018": no_synthetic_runtime(root),
        "F019": identity_recompute(root),
        "F020": provider_binding(root),
        "F021": skill_authority(root),
        "F022_CAPABILITIES": capability_truth(root),
        "F022_PREFLIGHT": pricing_preflight(root),
    }
    assert all(payload["pass"] for payload in results.values())
    print(json.dumps({"ORDER_005_EVIDENCE": "PASS", "gates": sorted(results)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
