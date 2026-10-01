from __future__ import annotations

from dataclasses import replace

import pytest
from pydantic import ValidationError

from mimicus.agents.identity import exact_fingerprint_from_manifest, make_identity
from mimicus.claims.evidence_bundle import EvidenceBundle, EvidenceInput, runtime_evidence_bundle
from mimicus.coalition.selector import AgentCandidate, select_coalition
from mimicus.coalition.threat_profile import ThreatProfile
from mimicus.orchestration.engine import RunRequest, scenario_fixture
from mimicus.plugins.services import BuiltinAgentFactory
from mimicus.providers.openai_agents import OpenAIAgentsProvider
from mimicus.storage.repository import Repository


def test_task_words_never_create_fixture_facts() -> None:
    probes = [
        "TAM numeric price revenue 12x",
        "fresh current stale date",
        "source echo origin citation",
        "citation figure entailment quote",
        "absence counterexample none exist",
    ]
    for task in probes:
        scenario, fixture = scenario_fixture(RunRequest(task=task, domain="audit"))
        assert scenario == "runtime"
        assert fixture == {}
    explicit = RunRequest(task="same words", scenario="tam_12x", source_mode="fixture", fixture={"price": 3, "users": 4, "claimed": 99})
    assert scenario_fixture(explicit)[1] == explicit.fixture


def test_evidence_input_rejects_provenance_spoof_and_oversize() -> None:
    with pytest.raises(ValidationError):
        EvidenceInput.model_validate(
            {
                "origin": "caller",
                "independence_cluster": "c1",
                "content": "x",
                "evidence_hash": "a" * 64,
            }
        )
    with pytest.raises(ValidationError):
        EvidenceInput.model_validate(
            {
                "origin": "caller",
                "source_class": "benchmark_fixture",
                "independence_cluster": "c1",
            }
        )
    with pytest.raises(ValidationError):
        EvidenceInput(origin="caller", independence_cluster="c1", content="x" * 12001)
    rows = [EvidenceInput(origin=f"caller-{i}", independence_cluster=f"c{i}") for i in range(17)]
    with pytest.raises(ValueError):
        runtime_evidence_bundle("r1", rows)


def test_runtime_evidence_canonicalizes_hashes_and_authority() -> None:
    source = EvidenceInput(
        origin="https://example.invalid/a",
        independence_cluster="publisher-a",
        content="Revenue was 42 USD.",
        extracted_facts={"claim_figure": 42},
        units="USD",
    )
    bundle = runtime_evidence_bundle("run-a", [source])
    assert isinstance(bundle, EvidenceBundle)
    item = bundle.items[0]
    assert item.source_class == "caller_supplied"
    assert item.authority_class == "caller_supplied"
    assert item.extraction_method == "caller_supplied"
    assert len(item.evidence_hash) == len(item.snapshot_hash) == len(item.canonical_evidence_hash) == 64
    second = runtime_evidence_bundle("run-b", [source]).items[0]
    assert item.canonical_evidence_hash == second.canonical_evidence_hash
    assert item.evidence_hash != second.evidence_hash


def test_material_identity_mutations_change_fingerprint_and_forgery_is_rejected() -> None:
    factory = BuiltinAgentFactory()
    candidate = factory.candidates()[0]
    identity = factory.identity_for(candidate)
    assert identity.fingerprint_matches_manifest
    assert identity.fingerprint == identity.recompute_fingerprint()
    baseline = identity.material_manifest
    mutations = {
        "runtime_provider_id": "other-provider",
        "runtime_model_id": "other-model",
        "runtime_model_version": "other-version",
        "phenotype": "other-phenotype",
        "phenotype_version": "v999",
        "system_prompt_hash": "1" * 64,
        "tool_manifest_hash": "2" * 64,
        "policy_hash": "3" * 64,
        "provider_adapter_version": "other-adapter",
    }
    for key, value in mutations.items():
        changed = dict(baseline)
        changed[key] = value
        assert exact_fingerprint_from_manifest(changed) != identity.fingerprint
    repo = Repository("sqlite:///:memory:")
    repo.register_identity(identity)
    forged = replace(identity, fingerprint="0" * 64)
    with pytest.raises(ValueError, match="fingerprint/material manifest mismatch"):
        repo.register_identity(forged)
    inspected = repo.inspect_state("general")
    assert inspected["identities"][0]["fingerprint_matches_manifest"] is True
    assert inspected["identities"][0]["recomputed_fingerprint"] == identity.fingerprint


def test_make_identity_binds_adapter_version() -> None:
    one = make_identity(provider="p", model_family="m", phenotype="x", tool_policy_hash="t", provider_adapter_version="adapter-1")
    two = make_identity(provider="p", model_family="m", phenotype="x", tool_policy_hash="t", provider_adapter_version="adapter-2")
    assert one.fingerprint != two.fingerprint
    assert one.material_manifest["provider_adapter_version"] == "adapter-1"


def test_openai_tool_capability_matches_actual_tools_and_identity() -> None:
    class DummyTool:
        name = "source_lookup"
        description = "Acquire explicit source evidence"

    no_tools = OpenAIAgentsProvider("gpt-test")
    with_tools = OpenAIAgentsProvider("gpt-test", tools=(DummyTool(),))
    assert no_tools.capabilities.supports_tools is False
    assert no_tools.capabilities.evidence_acquisition_available is False
    assert with_tools.capabilities.supports_tools is True
    assert with_tools.capabilities.evidence_acquisition_available is True
    assert no_tools.capabilities.tool_manifest_hash != with_tools.capabilities.tool_manifest_hash
    no_tool_fp = BuiltinAgentFactory(no_tools.capabilities).candidates()[0].fingerprint
    tool_fp = BuiltinAgentFactory(with_tools.capabilities).candidates()[0].fingerprint
    assert no_tool_fp != tool_fp


def test_selector_uses_capability_specific_authority_without_positive_transfer() -> None:
    profile = ThreatProfile(domain="research", threats=("mixed",), required_capabilities=("freshness", "independence"), complexity=0.6)
    mixed = AgentCandidate(
        fingerprint="a" * 64,
        name="mixed",
        capabilities=frozenset({"freshness", "independence"}),
        provider="p",
        model="m",
        prompt_hash="p1",
        tool_hash="t1",
        capability_audition_scores={"freshness": 1.0, "independence": 0.0},
        capability_calibration_scores={"freshness": 1.0, "independence": 0.0},
        capability_states={"freshness": "ACTIVE", "independence": "BANKRUPT"},
    )
    independent = AgentCandidate(
        fingerprint="b" * 64,
        name="independent",
        capabilities=frozenset({"independence"}),
        provider="q",
        model="n",
        prompt_hash="p2",
        tool_hash="t2",
        capability_audition_scores={"independence": 0.9},
        capability_calibration_scores={"independence": 0.9},
        capability_states={"independence": "ACTIVE"},
    )
    selected, rationale = select_coalition(profile, [mixed, independent], 2)
    assert [row.fingerprint for row in selected] == [mixed.fingerprint, independent.fingerprint]
    assert rationale["capability_authority"][mixed.fingerprint]["freshness"]["direct_trust"] == 1.0
    assert rationale["capability_authority"][mixed.fingerprint]["independence"]["state"] == "BANKRUPT"
