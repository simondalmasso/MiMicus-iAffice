from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import NAMESPACE_URL, uuid4, uuid5

from pydantic import BaseModel, ConfigDict, Field

from mimicus.agents.auditions import audition
from mimicus.agents.calibration import CalibrationLedger
from mimicus.canonical import sha256_obj, sha256_text
from mimicus.claims.models import Claim
from mimicus.coalition.selector import AgentCandidate, select_coalition
from mimicus.coalition.sparse_comm import sparse_edges
from mimicus.coalition.threat_profile import profile_task
from mimicus.coalition.topology import topology_for_size
from mimicus.events.ledger import EventLedger
from mimicus.falsifiers.builtins import builtin_specs
from mimicus.falsifiers.market import FalsifierMarket
from mimicus.falsifiers.primitives import execute_primitive
from mimicus.memory.gates import promotion_gate, write_gate
from mimicus.memory.models import MemoryItem
from mimicus.orchestration.progress_ledger import ProgressLedger
from mimicus.orchestration.replay import verify_replay
from mimicus.orchestration.task_ledger import TaskLedger
from mimicus.providers.base import Provider, ProviderRequest
from mimicus.providers.scripted import ScriptedProvider
from mimicus.storage.repository import Repository
from mimicus.types import ClaimStatus, Verdict


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task: str = Field(min_length=1)
    domain: str | None = None
    budget_usd: float = Field(default=0.0, ge=0.0)
    max_agents: int = Field(default=4, ge=1, le=8)
    depth: Literal["fast", "normal", "deep"] = "normal"
    learn: bool = False
    scenario: str | None = None
    fixture: dict[str, Any] = Field(default_factory=dict)


class RunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    run_id: str
    status: Literal["answered", "inconclusive", "failed"]
    answer: str
    confidence: float
    final_claims: list[dict[str, Any]]
    disagreements: list[dict[str, Any]]
    falsifiers: list[dict[str, Any]]
    evidence_provenance: dict[str, Any]
    coalition: dict[str, Any]
    budget: dict[str, Any]
    ledger_head: str
    memory_changes: list[dict[str, Any]]
    germinal_changes: list[dict[str, Any]]
    replay_verified: bool
    event_types: list[str]
    plugin_hashes: list[str]


def _fingerprint(name: str, provider: str = "scripted", model: str = "fixture-v1", prompt: str | None = None, tool: str | None = None) -> str:
    return sha256_obj({
        "provider": provider,
        "model": model,
        "version": "1",
        "system_prompt_hash": sha256_text(prompt or name),
        "tool_manifest_hash": sha256_text(tool or f"tools:{name}"),
        "policy_hash": sha256_text("mimicus-v0.1"),
    })


def default_candidates() -> list[AgentCandidate]:
    rows = [
        ("numeric-1", {"numeric", "synthesize"}, "provider-a", "math-v1"),
        ("source-1", {"source", "freshness", "independence"}, "provider-b", "research-v1"),
        ("counterexample-1", {"counterexample", "source"}, "provider-c", "hunt-v1"),
        ("critic-1", {"critic", "entailment"}, "provider-d", "critic-v1"),
        ("synth-1", {"synthesize"}, "provider-e", "synth-v1"),
    ]
    return [
        AgentCandidate(
            fingerprint=_fingerprint(name, provider, model),
            name=name,
            capabilities=frozenset(caps),
            provider=provider,
            model=model,
            prompt_hash=sha256_text(name),
            tool_hash=sha256_text(f"tools:{name}"),
        )
        for name, caps, provider, model in rows
    ]


def scenario_fixture(request: RunRequest) -> tuple[str, dict[str, Any]]:
    text = f"{request.scenario or ''} {request.task}".lower()
    fixture = dict(request.fixture)
    if fixture:
        return request.scenario or "custom", fixture
    if any(token in text for token in ("tam", "12x", "12×")):
        return "tam_12x", {"claim_statement": "TAM is 1,000 annual units", "claim_type": "numeric", "probability": 0.94, "price": 10.0, "users": 100.0, "price_period": "monthly", "claimed": 1000.0}
    if "echo" in text or "same origin" in text:
        return "echo_chamber", {"claim_statement": "Three independent sources corroborate the claim", "claim_type": "factual", "probability": 0.9, "clusters": ["origin-wire", "origin-wire", "origin-wire"], "texts": ["same syndicated report"] * 3}
    if "fresh" in text or "stale" in text:
        return "freshness", {"claim_statement": "The evidence is current", "claim_type": "temporal", "probability": 0.85, "evidence_date": "2025-01-01T00:00:00+00:00", "as_of": "2026-08-17T00:00:00+00:00"}
    if "entail" in text or "citation" in text or "figure" in text:
        return "citation_entailment", {"claim_statement": "The cited source supports figure 42", "claim_type": "numeric", "probability": 0.88, "claim_figure": 42, "evidence_spans": [{"span_id": "e1", "supported_figures": [41], "material_support": True}]}
    if "absence" in text or "counterexample" in text or "none exist" in text:
        return "counterexample", {"claim_statement": "No target exists", "claim_type": "factual", "probability": 0.86, "absence_key": "target", "registry": {"target": {"id": "known-counterexample"}}, "registry_snapshot_hash": "b" * 64}
    return "general", {"claim_statement": request.task, "claim_type": "other", "probability": 0.5}


def _spec_keys(profile_caps: tuple[str, ...], scenario: str) -> list[str]:
    if scenario == "tam_12x":
        return ["F1"]
    if scenario == "echo_chamber":
        return ["F3"]
    if scenario == "freshness":
        return ["F2"]
    if scenario == "citation_entailment":
        return ["F4"]
    if scenario == "counterexample":
        return ["F5"]
    keys: list[str] = []
    mapping = {"numeric": "F1", "freshness": "F2", "independence": "F3", "entailment": "F4", "counterexample": "F5"}
    for cap in profile_caps:
        key = mapping.get(cap)
        if key and key not in keys:
            keys.append(key)
    return keys


class MiMicusEngine:
    def __init__(self, database_url: str = "sqlite:///:memory:", *, plugin_hashes: list[str] | None = None, provider: Provider | None = None) -> None:
        self.repository = Repository(database_url)
        self.calibration = CalibrationLedger()
        self.provider = provider or ScriptedProvider()
        self.plugin_hashes = plugin_hashes or []

    def run(self, request: RunRequest) -> RunResult:
        run_id = str(uuid4())
        domain = request.domain or "general"
        scenario, fixture = scenario_fixture(request)
        ledger = EventLedger(run_id)
        progress = ProgressLedger()
        task_hash = sha256_obj({"task": request.task, "domain": domain, "fixture": fixture})
        config_hash = sha256_obj({"budget_usd": request.budget_usd, "max_agents": request.max_agents, "depth": request.depth, "learn": request.learn})
        ledger.append("run_started", {"task_hash": task_hash, "config_hash": config_hash, "plugin_hashes": self.plugin_hashes})
        task_ledger = TaskLedger(task=request.task, domain=domain, budget_usd=request.budget_usd, constraints={"max_agents": request.max_agents, "depth": request.depth}, plan=["profile", "audition", "coalition", "sealed-first-pass", "falsify", "synthesize", "learn", "replay"])
        progress.advance("INIT", 1.0)

        profile = profile_task(request.task, domain, scenario)
        ledger.append("threat_profiled", profile.model_dump(mode="json"))
        progress.advance("PROFILE_TASK", 0.9)
        ledger.append("verified_memory_loaded", {"domain": domain, "count": 0})
        progress.advance("LOAD_VERIFIED_MEMORY", 0.85)

        candidates = default_candidates()
        audited: list[AgentCandidate] = []
        canary_for = {"numeric": "parameter_trap", "freshness": "temporal_decoy", "independence": "semantic_decoy", "entailment": "granularity_trap", "counterexample": "prerequisite_blindness", "synthesize": "capability_mirage", "source": "semantic_decoy"}
        expected_answer = {"parameter_trap": "parameter", "temporal_decoy": "fresh", "semantic_decoy": "relevant", "granularity_trap": "granular", "prerequisite_blindness": "missing", "capability_mirage": "reject"}
        target_cap = profile.required_capabilities[0]
        category = canary_for.get(target_cap, "semantic_decoy")
        for candidate in candidates:
            passed_answer = expected_answer[category] if target_cap in candidate.capabilities or "synthesize" in candidate.capabilities else "wrong"
            result = audition(candidate.fingerprint, domain, category, passed_answer)
            calibration = self.calibration.get(candidate.fingerprint, domain)
            calibration.update(predicted_probability=0.8, outcome=result.passed, canary=True)
            ledger.append("agent_auditioned", {"fingerprint": candidate.fingerprint, "domain": domain, "category": category, "passed": result.passed, "score": result.score})
            audited.append(AgentCandidate(**{**candidate.__dict__, "audition_score": result.score, "calibration_score": calibration.trust}))
        progress.advance("AUDITION_CANDIDATES", 0.72)

        selected, rationale = select_coalition(profile, audited, request.max_agents)
        topology = topology_for_size(len(selected), profile.complexity)
        ledger.append("coalition_selected", {"members": [member.fingerprint for member in selected], "topology": topology, "rationale": rationale})
        progress.advance("SELECT_COALITION", 0.62)

        claims: list[Claim] = []
        for member in selected:
            sealed_context_id = str(uuid5(NAMESPACE_URL, f"{run_id}:{member.fingerprint}:sealed"))
            response = self.provider.generate(ProviderRequest(request.task, domain, member.name, sealed_context_id, fixture))
            claims.append(response.claim)
            ledger.append("claim_proposed", {"claim_hash": response.claim.hash, "fingerprint": member.fingerprint, "sealed_context_id": sealed_context_id, "probability": response.claim.probability, "provider_trace_id": response.trace_id})
        progress.advance("SEALED_FIRST_PASS", 0.55)
        ledger.append("claim_graph_built", {"claims": [claim.hash for claim in claims], "edges": 0})

        all_specs = builtin_specs(domain)
        candidate_specs = [all_specs[key] for key in _spec_keys(profile.required_capabilities, scenario)]
        for spec in candidate_specs:
            ledger.append("falsifier_proposed", {"spec_hash": spec.hash, "id": spec.id, "primitive": spec.primitive})
        max_tests = {"fast": 1, "normal": 3, "deep": 5}[request.depth]
        selected_specs, scores = FalsifierMarket().select(candidate_specs, budget_usd=request.budget_usd, max_tests=max_tests, information_floor=0.05)
        ledger.append("falsifier_market_scored", {"scores": [score.__dict__ for score in scores], "budget_usd": request.budget_usd, "max_tests": max_tests})
        if candidate_specs and not selected_specs:
            ledger.append("budget_exhausted", {"reason": "no candidate fits budget/information threshold"})
        for spec in selected_specs:
            ledger.append("falsifier_selected", {"spec_hash": spec.hash, "primitive": spec.primitive})

        executions = []
        for spec in selected_specs:
            execution = execute_primitive(spec, fixture)
            executions.append(execution)
            ledger.append("falsifier_executed", execution.model_dump(mode="json"))
        progress.advance("EXECUTE_FALSIFIERS", 0.25 if executions else 0.55)

        if not claims:
            final_status = ClaimStatus.INCONCLUSIVE
        elif any(execution.verdict == Verdict.FAIL for execution in executions):
            final_status = ClaimStatus.FALSIFIED
        elif executions and all(execution.verdict == Verdict.PASS for execution in executions):
            final_status = ClaimStatus.SUPPORTED
        else:
            final_status = ClaimStatus.INCONCLUSIVE
        for claim in claims:
            claim.status = final_status
            ledger.append("claim_updated", {"claim_id": claim.claim_id, "claim_hash": claim.hash, "status": claim.status.value})

        disagreement = 0.0
        if len(claims) > 1:
            probs = [claim.probability for claim in claims]
            disagreement = max(probs) - min(probs)
        edges = sparse_edges([member.fingerprint for member in selected], disagreement, k=2, round_index=0)
        for edge in edges:
            ledger.append("communication_edge_opened", edge.__dict__)
        ledger.append("consensus_stabilized", {"disagreement": disagreement, "edges": len(edges), "stagnation_count": progress.stagnation_count})
        progress.advance("SPARSE_CHALLENGE", 0.18 if executions else 0.52)

        if final_status == ClaimStatus.FALSIFIED:
            failed = next(execution for execution in executions if execution.verdict == Verdict.FAIL)
            answer = f"Claim falsified by {next(spec.primitive for spec in selected_specs if spec.hash == failed.spec_hash)}."
            confidence = 0.98
            status: Literal["answered", "inconclusive", "failed"] = "answered"
        elif final_status == ClaimStatus.SUPPORTED:
            answer = "Claim passed the selected deterministic falsifier scope."
            confidence = 0.85
            status = "answered"
        else:
            answer = "INCONCLUSIVE: verified evidence is insufficient under the configured budget/scope."
            confidence = 0.0
            status = "inconclusive"
        ledger.append("final_verified", {"status": final_status.value, "answer_hash": sha256_text(answer), "confidence": confidence})

        memory_changes: list[dict[str, Any]] = []
        if request.learn and executions:
            decisive = next((execution for execution in executions if execution.verdict in {Verdict.FAIL, Verdict.PASS}), None)
            if decisive is not None and claims:
                item = MemoryItem(
                    claim_hash=claims[0].hash,
                    content=f"Verified falsifier {decisive.spec_hash} produced {decisive.verdict.value} for scenario {scenario}",
                    owner_fingerprint=selected[0].fingerprint if selected else "system",
                    domain=domain,
                    origin_clusters=[decisive.execution_snapshot_hash],
                    authority=0.9,
                    deterministic_verification=True,
                    verified_clusters=[decisive.execution_snapshot_hash],
                )
                ledger.append("memory_candidate_written", {"memory_id": item.memory_id, "claim_hash": item.claim_hash, "authority": item.authority})
                written = write_gate(item)
                promoted = promotion_gate(written)
                ledger.append("memory_promoted", {"memory_id": promoted.memory_id, "status": promoted.status.value, "authority": promoted.authority})
                memory_changes.append(promoted.model_dump(mode="json"))
        progress.advance("LEARN_VERIFIED_ONLY", 0.08)

        ledger.append("run_completed", {"status": status, "task_ledger_hash": sha256_obj(task_ledger), "progress_ledger_hash": sha256_obj(progress)})
        replay = verify_replay(ledger.events, ledger.head)
        result = RunResult(
            run_id=run_id,
            status=status,
            answer=answer,
            confidence=confidence,
            final_claims=[claim.model_dump(mode="json") | {"claim_hash": claim.hash} for claim in claims],
            disagreements=[] if disagreement <= 0.05 else [{"probability_span": disagreement}],
            falsifiers=[
                execution.model_dump(mode="json")
                | {"id": next(spec.id for spec in selected_specs if spec.hash == execution.spec_hash), "primitive": next(spec.primitive for spec in selected_specs if spec.hash == execution.spec_hash)}
                for execution in executions
            ],
            evidence_provenance={"scenario": scenario, "fixture_hash": sha256_obj(fixture), "source_clusters": fixture.get("clusters", []), "pinned_registry_hash": fixture.get("registry_snapshot_hash")},
            coalition={"members": [member.fingerprint for member in selected], "names": [member.name for member in selected], "topology": topology, "rationale": rationale},
            budget={"limit_usd": request.budget_usd, "spent_usd": sum(execution.cost for execution in executions), "latency_ms": sum(execution.latency_ms for execution in executions), "max_tests": max_tests},
            ledger_head=ledger.head,
            memory_changes=memory_changes,
            germinal_changes=[],
            replay_verified=bool(replay["verified"]),
            event_types=[event.event_type for event in ledger.events],
            plugin_hashes=self.plugin_hashes,
        )
        self.repository.save_run(run_id=run_id, task_hash=task_hash, config_hash=config_hash, status=status, ledger_head=ledger.head, result=result.model_dump(mode="json"), events=ledger.events)
        return result

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        result = self.repository.get_run(run_id)
        if result is None:
            return None
        events = self.repository.get_events(run_id)
        replay = verify_replay(events, str(result["ledger_head"]))
        return result | {"replay_state": replay, "events": events}
