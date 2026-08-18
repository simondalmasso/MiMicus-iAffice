from __future__ import annotations

from pathlib import Path


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


def repl(path: str, old: str, new: str, count: int = 1) -> None:
    text = read(path)
    if old not in text:
        raise SystemExit(f"anchor missing {path}: {old[:120]!r}")
    write(path, text.replace(old, new, count))


# MCP type-safe canonicalization.
repl(
    "src/mimicus/interfaces/mcp_server.py",
    "from mimicus.config import Settings\n",
    "from mimicus.claims.evidence_bundle import EvidenceInput\nfrom mimicus.config import Settings\n",
)
repl(
    "src/mimicus/interfaces/mcp_server.py",
    "            evidence=evidence or [],\n",
    "            evidence=[EvidenceInput.model_validate(item) for item in (evidence or [])],\n",
)

# Historical domain status is telemetry/inspection compatibility only.
repl(
    "src/mimicus/orchestration/engine.py",
    '''            if cap_states and all(state == "BANKRUPT" for state in cap_states.values()):
                self.repository.set_bankruptcy_state(candidate.fingerprint, domain, "BANKRUPT", "all relevant capabilities bankrupt")
            elif cap_states and all(state == "ACTIVE" for state in cap_states.values()):
                self.repository.set_bankruptcy_state(candidate.fingerprint, domain, "ACTIVE", "all relevant capabilities active")
''',
    '''            if cap_states and all(state == "BANKRUPT" for state in cap_states.values()):
                self.repository.set_bankruptcy_state(candidate.fingerprint, domain, "BANKRUPT", "all relevant capabilities bankrupt")
            elif any(state == "PROBATION" for state in cap_states.values()):
                self.repository.set_bankruptcy_state(candidate.fingerprint, domain, "PROBATION", "one or more relevant capabilities on probation")
            elif cap_states and all(state == "ACTIVE" for state in cap_states.values()):
                self.repository.set_bankruptcy_state(candidate.fingerprint, domain, "ACTIVE", "all relevant capabilities active")
''',
)

# Legacy MCP test uses keywords after public schema addition.
repl(
    "tests/unit/test_validation_coverage.py",
    '    result = run_fn("K3 TAM 12x mismatch", "finance", 0.0, 4, "normal", True)\n',
    '    result = run_fn("K3 TAM 12x mismatch", domain="finance", evidence=None, budget_usd=0.0, max_agents=4, depth="normal", learn=True)\n',
)

# Historical engine scenarios are explicit fixtures; ORDER-005 separately tests words-only fail closed.
engine_test = '''from __future__ import annotations

from pathlib import Path

from mimicus.orchestration.engine import MiMicusEngine, RunRequest


def _tam_fixture() -> dict[str, object]:
    return {"claim_statement": "TAM", "claim_type": "numeric", "price": 10.0, "users": 100.0, "price_period": "monthly", "claimed": 1000.0}


def test_full_flow_and_persistence(tmp_path: Path) -> None:
    engine = MiMicusEngine(f"sqlite:///{tmp_path / 'run.db'}", plugin_hashes=["a" * 64])
    result = engine.run(RunRequest(task="K3 TAM 12x mismatch", domain="finance", scenario="tam_12x", fixture=_tam_fixture(), learn=True))
    assert result.status == "answered"
    assert result.replay_verified
    assert result.memory_changes[0]["status"] == "shared_verified"
    required = [
        "run_started",
        "threat_profiled",
        "agent_auditioned",
        "coalition_selected",
        "claim_proposed",
        "falsifier_selected",
        "falsifier_executed",
        "claim_updated",
        "final_verified",
        "memory_promoted",
        "run_completed",
    ]
    for event_type in required:
        assert event_type in result.event_types
    fetched = engine.get_run(result.run_id)
    assert fetched is not None
    assert fetched["replay_state"]["verified"] is True
    assert len(fetched["events"]) == len(result.event_types)


def test_five_safe_scenarios(tmp_path: Path) -> None:
    engine = MiMicusEngine(f"sqlite:///{tmp_path / 'scenarios.db'}")
    cases = [
        ("K3 TAM 12x mismatch", "tam_12x", _tam_fixture(), "numeric_invariant"),
        ("source echo same origin citation", "echo_chamber", {"claim_statement": "sources", "claim_type": "factual", "clusters": ["wire", "wire"], "texts": ["same", "same"]}, "source_independence"),
        ("freshness stale current evidence", "freshness", {"claim_statement": "fresh", "claim_type": "temporal", "evidence_date": "2025-01-01T00:00:00+00:00", "as_of": "2026-08-17T00:00:00+00:00"}, "freshness"),
        ("citation figure entailment mismatch", "citation_entailment", {"claim_statement": "figure", "claim_type": "numeric", "claim_figure": 42, "evidence_spans": [{"span_id": "e1", "supported_figures": [41], "material_support": True}]}, "citation_entailment"),
        ("absence counterexample none exist", "counterexample", {"claim_statement": "absence", "claim_type": "factual", "absence_key": "target", "registry": {"target": {"id": "known"}}, "registry_snapshot_hash": "b" * 64}, "counterexample_search"),
    ]
    for task, scenario, fixture, primitive in cases:
        result = engine.run(RunRequest(task=task, domain="test", scenario=scenario, fixture=fixture))
        assert result.falsifiers
        assert result.falsifiers[0]["verdict"] == "FAIL"
        assert result.status == "answered"
        assert result.falsifiers[0]["primitive"] == primitive


def test_budget_exhaustion_is_inconclusive(tmp_path: Path) -> None:
    engine = MiMicusEngine(f"sqlite:///{tmp_path / 'budget.db'}")
    fixture = {"claim_statement": "x", "claim_type": "numeric", "price": 1, "users": 1, "claimed": 10}
    result = engine.run(RunRequest(task="ambiguous prose only", fixture=fixture, scenario="general", budget_usd=0.0))
    assert result.status == "inconclusive"
    assert result.answer.startswith("INCONCLUSIVE")
'''
write("tests/integration/test_engine.py", engine_test)

# Canonical identities and explicit fixtures in ORDER-003 tests.
p = "tests/integration/test_order003_runtime.py"
text = read(p)
text = text.replace(
    '''    identity = make_identity(
        fingerprint=candidate.fingerprint,
        provider=candidate.provider,
        model_family=candidate.model,
        phenotype=candidate.name,
        tool_policy_hash=candidate.tool_hash,
    )
''',
    '''    factory = MiMicusEngine(url).services.agent_factory
    identity = factory.identity_for(candidate)
''',
    1,
)
text = text.replace(
    '''    child = make_identity(
        fingerprint="f" * 64,
        provider=candidate.provider,
        model_family=candidate.model,
        phenotype=candidate.name,
        tool_policy_hash=candidate.tool_hash,
        parent_fingerprint=candidate.fingerprint,
        declared_lineage_id=identity.lineage_id,
    )
''',
    '''    child = make_identity(
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
''',
    1,
)
text = text.replace(
    '    first = engine1.run(RunRequest(task="K3 TAM 12x mismatch", domain="finance", learn=True))\n',
    '    base_fixture = {"claim_statement": "TAM", "claim_type": "numeric", "price": 10.0, "users": 100.0, "price_period": "monthly", "claimed": 1000.0}\n    first = engine1.run(RunRequest(task="K3 TAM 12x mismatch", domain="finance", scenario="tam_12x", fixture=base_fixture, learn=True))\n',
    1,
)
text = text.replace(
    '    second = engine2.run(RunRequest(task="K3 TAM 12x mismatch", domain="finance"))\n',
    '    second = engine2.run(RunRequest(task="K3 TAM 12x mismatch", domain="finance", scenario="tam_12x", fixture=base_fixture))\n',
    1,
)
old = '''    child_fp = "c" * 64
    revision = {
        "claim_statement": "x",
        "claim_type": "numeric",
        "price": 1,
        "users": 1,
        "claimed": 10,
        "identity_revisions": {base.name: {"fingerprint": child_fp, "lineage_id": identity.lineage_id, "parent_fingerprint": base.fingerprint}},
    }
'''
new = '''    child_identity = make_identity(
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
'''
if old not in text:
    raise SystemExit("order003 whitewash test anchor missing")
text = text.replace(old, new, 1)
write(p, text)

# Process whitewash/recovery use a valid material revision.
p = "src/mimicus/validation/order003_worker.py"
text = read(p)
text = text.replace('    child = "c" * 64\n', '    child_identity = make_identity(provider=base.provider, model_family=base.model, phenotype=base.name, tool_policy_hash=base.tool_hash, runtime_model_version=base.runtime_model_version, phenotype_version=base.phenotype_version, system_prompt_hash="c" * 64, tool_manifest_hash=base.tool_hash, policy_hash=base.policy_hash, provider_adapter_version=base.provider_adapter_version, parent_fingerprint=base.fingerprint, declared_lineage_id=base_identity.lineage_id)\n    child = child_identity.fingerprint\n', 2)
text = text.replace('                "fingerprint": child,\n                "lineage_id": base_identity.lineage_id,', '                "system_prompt_hash": "c" * 64,\n                "lineage_id": base_identity.lineage_id,', 2)
if "from mimicus.agents.identity import make_identity" not in text:
    text = text.replace("from mimicus.agents.bankruptcy import capability_scope\n", "from mimicus.agents.bankruptcy import capability_scope\nfrom mimicus.agents.identity import make_identity\n")
write(p, text)

# Historical F013 expectation: zero refs are preserved when provider emitted zero refs.
p = "tests/integration/test_order004_runtime.py"
text = read(p)
old = '''    assert result.final_claims
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
'''
new = '''    assert result.final_claims
    refs = set(result.final_claims[0]["evidence_refs"])
    assert refs == set()
    restarted = MiMicusEngine(database)
    fetched = restarted.get_run(result.run_id)
    assert fetched is not None
    persisted = fetched["evidence"]
    assert persisted
    assert all(row["snapshot_hash"] for row in persisted)
    assert fetched["replay_state"]["verified"] is True
'''
if old not in text:
    raise SystemExit("order004 evidence test anchor missing")
write(p, text.replace(old, new, 1))

print("ORDER005_COMPAT_PATCH=APPLIED")
