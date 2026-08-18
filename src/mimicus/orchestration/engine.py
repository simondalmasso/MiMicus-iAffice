from __future__ import annotations

import asyncio
from dataclasses import asdict, replace
from typing import Any, Literal
from uuid import NAMESPACE_URL, uuid4, uuid5

from pydantic import BaseModel, ConfigDict, Field

from mimicus.agents.auditions import audition
from mimicus.agents.bankruptcy import BankruptcyRecord, evaluate_bankruptcy, recover
from mimicus.agents.calibration import CalibrationLedger, capability_scope
from mimicus.agents.identity import make_identity
from mimicus.canonical import sha256_obj, sha256_text
from mimicus.claims.evidence import evidence_row, execution_evidence, fixture_evidence
from mimicus.claims.models import Claim
from mimicus.coalition.selector import AgentCandidate, correlation
from mimicus.coalition.threat_profile import profile_task
from mimicus.events.ledger import EventLedger
from mimicus.falsifiers.market import FalsifierMarket
from mimicus.falsifiers.spec import FalsifierExecution, FalsifierSpec
from mimicus.germinal.fossils import seed_fossils
from mimicus.germinal.mutate import mutate_params
from mimicus.germinal.promote import decide
from mimicus.memory.gates import promotion_gate, write_gate
from mimicus.memory.models import MemoryItem
from mimicus.orchestration.budget import BudgetLedger
from mimicus.orchestration.communication import ChallengeRequest, CommunicationCandidate
from mimicus.orchestration.dag_executor import DagExecution, DagExecutor
from mimicus.orchestration.morphology import DagNode, NodeKind, compile_morphology
from mimicus.orchestration.progress_ledger import ProgressLedger
from mimicus.orchestration.proximity import SemanticSignature, semantic_proximity
from mimicus.orchestration.replay import verify_replay
from mimicus.orchestration.task_ledger import TaskLedger
from mimicus.plugins.profiles import build_runtime_services
from mimicus.plugins.registry import PluginKernel
from mimicus.plugins.services import BuiltinAgentFactory, RuntimeServices
from mimicus.providers.base import Provider, ProviderRequest, ProviderResponse
from mimicus.storage.repository import Repository
from mimicus.types import BankruptcyState, ClaimStatus, Verdict


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task: str = Field(min_length=1)
    domain: str | None = None
    budget_usd: float = Field(default=0.0, ge=0.0)
    max_agents: int = Field(default=4, ge=1, le=8)
    max_concurrency: int = Field(default=4, ge=1, le=8)
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
    plan_hash: str
    morphology: str
    provider_call_count: int
    challenge_edge_count: int
    concurrency_summary: dict[str, Any]
    critical_path_summary: dict[str, Any]
    persistent_memory_reused: list[str]
    persistent_falsifiers_reused: list[str]
    lineage_exclusions: dict[str, list[str]]


def _fingerprint(name: str, provider: str = "scripted", model: str = "fixture-v2", prompt: str | None = None, tool: str | None = None) -> str:
    return sha256_obj(
        {
            "provider": provider,
            "model": model,
            "version": "2",
            "system_prompt_hash": sha256_text(prompt or name),
            "tool_manifest_hash": sha256_text(tool or f"tools:{name}"),
            "policy_hash": sha256_text("mimicus-v0.2"),
        }
    )


def default_candidates() -> list[AgentCandidate]:
    return BuiltinAgentFactory().candidates()


def scenario_fixture(request: RunRequest) -> tuple[str, dict[str, Any]]:
    text = f"{request.scenario or ''} {request.task}".lower()
    fixture = dict(request.fixture)
    if fixture:
        return request.scenario or "custom", fixture
    if any(token in text for token in ("tam", "12x", "12×")):
        return "tam_12x", {
            "claim_statement": "TAM is 1,000 annual units",
            "claim_type": "numeric",
            "probability": 0.94,
            "price": 10.0,
            "users": 100.0,
            "price_period": "monthly",
            "claimed": 1000.0,
        }
    if "echo" in text or "same origin" in text:
        return "echo_chamber", {
            "claim_statement": "Three independent sources corroborate the claim",
            "claim_type": "factual",
            "probability": 0.9,
            "clusters": ["origin-wire", "origin-wire", "origin-wire"],
            "texts": ["same syndicated report"] * 3,
        }
    if "fresh" in text or "stale" in text:
        return "freshness", {
            "claim_statement": "The evidence is current",
            "claim_type": "temporal",
            "probability": 0.85,
            "evidence_date": "2025-01-01T00:00:00+00:00",
            "as_of": "2026-08-17T00:00:00+00:00",
        }
    if "entail" in text or "citation" in text or "figure" in text:
        return "citation_entailment", {
            "claim_statement": "The cited source supports figure 42",
            "claim_type": "numeric",
            "probability": 0.88,
            "claim_figure": 42,
            "evidence_spans": [{"span_id": "e1", "supported_figures": [41], "material_support": True}],
        }
    if "absence" in text or "counterexample" in text or "none exist" in text:
        return "counterexample", {
            "claim_statement": "No target exists",
            "claim_type": "factual",
            "probability": 0.86,
            "absence_key": "target",
            "registry": {"target": {"id": "known-counterexample"}},
            "registry_snapshot_hash": "b" * 64,
        }
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


def _trust_from_row(row: dict[str, Any]) -> float:
    attempts = int(row["attempts"])
    return 0.5 if attempts < 3 else int(row["successes"]) / max(1, attempts)


class MiMicusEngine:
    def __init__(
        self,
        database_url: str = "sqlite:///:memory:",
        *,
        plugin_hashes: list[str] | None = None,
        provider: Provider | None = None,
        services: RuntimeServices | None = None,
        profile: str = "offline",
    ) -> None:
        self._kernel: PluginKernel | None
        if services is None:
            built, hashes, kernel = build_runtime_services(profile, database_url, provider_override=provider)
            self.services = built
            self._kernel = kernel
            self.plugin_hashes = plugin_hashes or hashes
        else:
            self.services = services
            self._kernel = None
            self.plugin_hashes = plugin_hashes or []
        self.repository: Repository = self.services.repository
        self.provider = self.services.provider
        self.calibration = CalibrationLedger(self.repository)

    def run(self, request: RunRequest) -> RunResult:
        return asyncio.run(self.run_async(request))

    async def run_async(self, request: RunRequest) -> RunResult:
        run_id = str(uuid4())
        domain = request.domain or "general"
        scenario, fixture = scenario_fixture(request)
        ledger = EventLedger(run_id)
        progress = ProgressLedger()
        progress_rows: list[dict[str, Any]] = []
        task_hash = sha256_obj({"task": request.task, "domain": domain, "fixture": fixture})
        config_hash = sha256_obj(
            {
                "budget_usd": request.budget_usd,
                "max_agents": request.max_agents,
                "max_concurrency": request.max_concurrency,
                "depth": request.depth,
                "learn": request.learn,
            }
        )
        ledger.append("run_started", {"task_hash": task_hash, "config_hash": config_hash, "plugin_hashes": self.plugin_hashes})

        def advance(step: str, uncertainty: float) -> None:
            progress.advance(step, uncertainty)
            progress_rows.append(progress.model_dump(mode="json"))

        advance("INIT", 1.0)
        profile = profile_task(request.task, domain, scenario)
        ledger.append("threat_profiled", profile.model_dump(mode="json"))
        advance("PROFILE_TASK", 0.90)

        retrieved_memory = self.services.memory.retrieve(domain)
        ledger.append(
            "verified_memory_loaded",
            {
                "domain": domain,
                "count": len(retrieved_memory),
                "memory_ids": [item.memory_id for item in retrieved_memory],
                "gate": "RETRIEVAL",
            },
        )
        advance("LOAD_VERIFIED_MEMORY", 0.82)

        candidates = self.services.agent_factory.candidates()
        audited: list[AgentCandidate] = []
        lineage_exclusions: dict[str, list[str]] = {"bankrupt": [], "probation": []}
        canary_for = {
            "numeric": "parameter_trap",
            "freshness": "temporal_decoy",
            "independence": "semantic_decoy",
            "entailment": "granularity_trap",
            "counterexample": "prerequisite_blindness",
            "synthesize": "capability_mirage",
            "source": "semantic_decoy",
        }
        expected_answer = {
            "parameter_trap": "parameter",
            "temporal_decoy": "fresh",
            "semantic_decoy": "relevant",
            "granularity_trap": "granular",
            "prerequisite_blindness": "missing",
            "capability_mirage": "reject",
        }
        failures = {str(value) for value in fixture.get("audition_fail_fingerprints", [])} | {str(value) for value in fixture.get("audition_fail_names", [])}
        fail_caps = {str(value) for value in fixture.get("audition_fail_capabilities", [])}
        recovery = {str(value) for value in fixture.get("recovery_fingerprints", [])} | {str(value) for value in fixture.get("recovery_names", [])}
        revisions = fixture.get("identity_revisions", {})
        for base_candidate in candidates:
            candidate = base_candidate
            identity = self.services.agent_factory.identity_for(candidate)
            if isinstance(revisions, dict) and isinstance(revisions.get(candidate.name), dict):
                revision = revisions[candidate.name]
                revised_fp = str(
                    revision.get("fingerprint") or _fingerprint(candidate.name, candidate.provider, candidate.model, prompt=str(revision.get("prompt_revision", "revision")))
                )
                identity = make_identity(
                    fingerprint=revised_fp,
                    provider=candidate.provider,
                    model_family=candidate.model,
                    phenotype=candidate.name,
                    tool_policy_hash=candidate.tool_hash,
                    runtime_model_version=candidate.runtime_model_version,
                    phenotype_version=candidate.phenotype_version,
                    system_prompt_hash=str(revision.get("system_prompt_hash") or candidate.prompt_hash),
                    tool_manifest_hash=str(revision.get("tool_manifest_hash") or candidate.tool_hash),
                    policy_hash=candidate.policy_hash,
                    provider_adapter_version=candidate.provider_adapter_version,
                    parent_fingerprint=str(revision.get("parent_fingerprint")) if revision.get("parent_fingerprint") else None,
                    declared_lineage_id=str(revision.get("lineage_id")) if revision.get("lineage_id") else identity.lineage_id,
                    revision_provenance=str(revision.get("provenance", "declared ORDER-004 revision")),
                )
                candidate = replace(candidate, fingerprint=revised_fp, prompt_hash=identity.system_prompt_hash, tool_hash=identity.tool_manifest_hash)
            self.repository.register_identity(identity)
            candidate = replace(candidate, lineage_id=identity.lineage_id)
            relevant_caps = [cap for cap in profile.required_capabilities if cap in candidate.capabilities]
            if not relevant_caps:
                ledger.append(
                    "agent_auditioned",
                    {
                        "fingerprint": candidate.fingerprint,
                        "lineage_id": identity.lineage_id,
                        "domain": domain,
                        "capability": None,
                        "test_family": None,
                        "applicability": "NOT_APPLICABLE",
                        "passed": None,
                        "score": 0.5,
                        "routing_state": "ACTIVE",
                    },
                )
                audited.append(replace(candidate, audition_score=0.5, calibration_score=0.5))
                continue

            target_cap = relevant_caps[0]
            category = canary_for.get(target_cap, "semantic_decoy")
            family = f"{target_cap}_canary"
            scoped_state_key = capability_scope(domain, target_cap, family)
            current_state = self.repository.bankruptcy_state(candidate.fingerprint, scoped_state_key)
            known_negative_lineage = self.repository.lineage_has_bankrupt_predecessor(identity.lineage_id, domain, exclude_fingerprint=candidate.fingerprint)
            if known_negative_lineage and current_state == "ACTIVE":
                self.repository.set_bankruptcy_state(candidate.fingerprint, scoped_state_key, "PROBATION", "known lineage has unresolved domain bankruptcy")
                current_state = "PROBATION"
                ledger.append(
                    "bankruptcy_changed",
                    {"fingerprint": candidate.fingerprint, "domain": domain, "capability": target_cap, "state": "PROBATION", "reason": "known-lineage whitewashing defense"},
                )
            forced_fail = candidate.fingerprint in failures or candidate.name in failures or target_cap in fail_caps
            passed_answer = "wrong" if forced_fail else expected_answer[category]
            audition_result = audition(candidate.fingerprint, domain, category, passed_answer, capability=target_cap, test_family=family, supported=True)
            assert audition_result.passed is not None
            calibration = self.calibration.record_capability_verified(
                candidate.fingerprint, domain, target_cap, family, predicted_probability=0.8, outcome=audition_result.passed, canary=True
            )
            # Keep the historical domain summary for ORDER-003 compatibility, but routing decisions below are capability-scoped.
            self.calibration.record_verified(candidate.fingerprint, domain, predicted_probability=0.8, outcome=audition_result.passed, canary=True)
            evaluated = evaluate_bankruptcy(calibration)
            recovery_requested = candidate.fingerprint in recovery or candidate.name in recovery
            if recovery_requested:
                recovered = recover(
                    BankruptcyRecord(candidate.fingerprint, scoped_state_key, BankruptcyState(current_state), "recovery path"), recovery_audition_passed=audition_result.passed
                )
                next_state = recovered.state.value
                reason = recovered.reason or "recovery audition"
            elif evaluated.state == BankruptcyState.BANKRUPT:
                next_state = "BANKRUPT"
                reason = evaluated.reason or "verified capability audition bankruptcy"
            else:
                next_state = current_state
                reason = "direct verified capability calibration"
            if next_state != current_state:
                self.repository.set_bankruptcy_state(candidate.fingerprint, scoped_state_key, next_state, reason)
                ledger.append(
                    "bankruptcy_changed",
                    {"fingerprint": candidate.fingerprint, "domain": domain, "capability": target_cap, "test_family": family, "state": next_state, "reason": reason},
                )
            if next_state == "BANKRUPT":
                self.repository.set_bankruptcy_state(candidate.fingerprint, domain, "BANKRUPT", f"capability {target_cap}: {reason}")
            elif recovery_requested and next_state == "ACTIVE":
                self.repository.set_bankruptcy_state(candidate.fingerprint, domain, "ACTIVE", f"capability {target_cap} recovery audition passed")
            state = self.repository.bankruptcy_state(candidate.fingerprint, scoped_state_key)
            if state == "BANKRUPT":
                lineage_exclusions["bankrupt"].append(candidate.fingerprint)
            elif state == "PROBATION":
                lineage_exclusions["probation"].append(candidate.fingerprint)
            ledger.append(
                "agent_auditioned",
                {
                    "fingerprint": candidate.fingerprint,
                    "lineage_id": identity.lineage_id,
                    "domain": domain,
                    "capability": target_cap,
                    "category": category,
                    "test_family": family,
                    "applicability": "APPLICABLE",
                    "passed": audition_result.passed,
                    "score": audition_result.score,
                    "direct_attempts": calibration.attempts,
                    "direct_brier": calibration.brier_score,
                    "routing_state": state,
                },
            )
            audited.append(
                replace(candidate, audition_score=audition_result.score, calibration_score=calibration.trust, bankrupt=state == "BANKRUPT", probation=state == "PROBATION")
            )
        advance("AUDITION_CANDIDATES", 0.70)

        selected, rationale = self.services.coalition.select(profile, audited, request.max_agents)
        ledger.append("coalition_selected", {"members": [member.fingerprint for member in selected], "rationale": rationale})
        advance("SELECT_COALITION", 0.60)

        injected_by_agent: dict[str, list[dict[str, Any]]] = {}
        persistent_memory_reused: set[str] = set()
        for member in selected:
            injected: list[dict[str, Any]] = []
            for item in retrieved_memory:
                allowed = self.services.memory.injectable(item, member.fingerprint, domain)
                ledger.append(
                    "memory_cross_agent_gate",
                    {
                        "memory_id": item.memory_id,
                        "target_fingerprint": member.fingerprint,
                        "allowed": allowed,
                        "gate": "CROSS_AGENT",
                    },
                )
                if allowed:
                    injected.append(item.model_dump(mode="json"))
                    persistent_memory_reused.add(item.memory_id)
            injected_by_agent[member.fingerprint] = injected

        builtins = self.services.falsifiers.specs(domain)
        base_specs = [builtins[key] for key in _spec_keys(profile.required_capabilities, scenario)]
        promoted = self.repository.promoted_falsifiers(domain)
        promoted_by_primitive: dict[str, FalsifierSpec] = {}
        for spec in promoted:
            promoted_by_primitive[spec.primitive] = max(spec, promoted_by_primitive.get(spec.primitive, spec), key=lambda row: row.version)
        candidate_specs: list[FalsifierSpec] = []
        persistent_falsifiers_reused: list[str] = []
        for spec in base_specs:
            replacement = promoted_by_primitive.get(spec.primitive)
            if replacement is not None:
                candidate_specs.append(replacement)
                persistent_falsifiers_reused.append(replacement.hash)
            else:
                candidate_specs.append(spec)
        for spec in promoted:
            if spec.hash not in {row.hash for row in candidate_specs} and (not base_specs or spec.primitive in {row.primitive for row in base_specs}):
                candidate_specs.append(spec)
                persistent_falsifiers_reused.append(spec.hash)
        for spec in candidate_specs:
            ledger.append(
                "falsifier_proposed",
                {
                    "spec_hash": spec.hash,
                    "id": spec.id,
                    "primitive": spec.primitive,
                    "persistent_reuse": spec.hash in persistent_falsifiers_reused,
                },
            )
        budget = BudgetLedger(request.budget_usd)
        provider_estimate = float(fixture["agent_cost"]) if "agent_cost" in fixture else self.provider.capabilities.estimated_max_cost_per_call
        if provider_estimate is None and self.provider.capabilities.known_zero_cost:
            provider_estimate = 0.0
        projected_agent_cost = request.budget_usd if provider_estimate is None and selected else float(provider_estimate or 0.0) * len(selected)
        market_budget = max(0.0, request.budget_usd - min(request.budget_usd, projected_agent_cost))
        max_tests = {"fast": 1, "normal": 3, "deep": 5}[request.depth]
        selected_specs, scores = FalsifierMarket().select(candidate_specs, budget_usd=market_budget, max_tests=max_tests, information_floor=0.05)
        ledger.append(
            "falsifier_market_scored", {"scores": [asdict(score) for score in scores], "budget_usd": market_budget, "hard_cap_usd": request.budget_usd, "max_tests": max_tests}
        )
        if candidate_specs and not selected_specs:
            ledger.append("budget_exhausted", {"reason": "no candidate fits budget/information threshold"})
        for spec in selected_specs:
            ledger.append("falsifier_selected", {"spec_hash": spec.hash, "primitive": spec.primitive, "persistent_reuse": spec.hash in persistent_falsifiers_reused})

        force_sparse = bool(fixture.get("force_sparse", False))
        hierarchical = bool(fixture.get("hierarchical", False) or any(token in request.task.lower() for token in ("decompose", "mixed evidence", "hierarchical")))
        plan = compile_morphology(
            task_hash=task_hash,
            selected_fingerprints=[member.fingerprint for member in selected],
            falsifier_hashes=[spec.hash for spec in selected_specs],
            complexity=profile.complexity,
            required_capabilities=profile.required_capabilities,
            max_concurrency=request.max_concurrency,
            learn=request.learn,
            force_sparse=force_sparse,
            hierarchical=hierarchical,
        )
        ledger.append("morphology_compiled", {"plan_hash": plan.plan_hash, "morphology": plan.name.value, "nodes": len(plan.nodes), "edges": len(plan.edges)})

        precompleted: dict[str, object] = {}
        value: dict[str, Any]
        for node in plan.nodes:
            if node.kind == NodeKind.PROFILE:
                node.status = "COMPLETED"
                node.output_hash = sha256_obj(profile.model_dump(mode="json"))
                precompleted[node.node_id] = profile.model_dump(mode="json")
            elif node.kind == NodeKind.MEMORY_RETRIEVE:
                node.status = "COMPLETED"
                value = {"memory_ids": [item.memory_id for item in retrieved_memory]}
                node.output_hash = sha256_obj(value)
                precompleted[node.node_id] = value
            elif node.kind == NodeKind.AUDITION:
                node.status = "COMPLETED"
                value = {"audited": [member.fingerprint for member in audited], "excluded": lineage_exclusions}
                node.output_hash = sha256_obj(value)
                precompleted[node.node_id] = value

        selected_by_fp = {member.fingerprint: member for member in selected}
        specs_by_hash = {spec.hash: spec for spec in selected_specs}
        base_evidence = fixture_evidence(fixture, domain=domain, scenario=scenario)
        base_evidence_rows = [evidence_row(item) for item in base_evidence]
        base_evidence_hashes = [str(row["evidence_hash"]) for row in base_evidence_rows]
        claims_by_fp: dict[str, Claim] = {}
        claim_trace_ids: dict[str, str | None] = {}
        provider_usages: list[dict[str, Any]] = []
        executions: list[FalsifierExecution] = []
        communications: list[dict[str, Any]] = []
        provider_call_count = 0
        communication_stagnated = False

        async def handle(node: DagNode) -> object:
            nonlocal provider_call_count, communication_stagnated
            ledger.append("dag_node_started", {"node_id": node.node_id, "kind": node.kind.value, "input_hash": node.input_hash})
            if node.kind == NodeKind.AGENT_TASK:
                if node.identity is None or node.identity not in selected_by_fp:
                    raise RuntimeError("agent DAG node missing selected identity")
                member = selected_by_fp[node.identity]
                estimated = float(fixture["agent_cost"]) if "agent_cost" in fixture else self.provider.capabilities.estimated_max_cost_per_call
                reservation = await budget.reserve("agent_generation", estimated, known_zero_cost=self.provider.capabilities.known_zero_cost)
                if reservation is None:
                    ledger.append("budget_exhausted", {"node_id": node.node_id, "kind": node.kind.value, "category": "agent_generation"})
                    return {"budget_exhausted": True}
                sealed_context_id = str(uuid5(NAMESPACE_URL, f"{run_id}:{member.fingerprint}:sealed"))
                provider_request = ProviderRequest(request.task, domain, member.name, sealed_context_id, fixture, tuple(injected_by_agent.get(member.fingerprint, [])))
                try:
                    response: ProviderResponse = await self.provider.generate_request_async(provider_request)
                except asyncio.CancelledError:
                    await budget.release(reservation, reason="agent task cancelled")
                    ledger.append("dag_node_cancelled", {"node_id": node.node_id, "kind": node.kind.value, "reservation_released": True})
                    raise
                except BaseException:
                    await budget.release(reservation, reason="agent task failed before provider result")
                    ledger.append("dag_node_failed", {"node_id": node.node_id, "kind": node.kind.value, "reservation_released": True})
                    raise
                reconciliation = await budget.reconcile(reservation, response.cost)
                provider_call_count += 1
                claim_with_evidence = response.claim.model_copy(update={"evidence_refs": sorted(set(response.claim.evidence_refs + base_evidence_hashes))})
                claims_by_fp[member.fingerprint] = claim_with_evidence
                claim_trace_ids[member.fingerprint] = response.trace_id
                provider_usages.append({"fingerprint": member.fingerprint, "trace_id": response.trace_id, "usage": response.usage, "budget": reconciliation})
                ledger.append(
                    "claim_proposed",
                    {
                        "claim_hash": claim_with_evidence.hash,
                        "fingerprint": member.fingerprint,
                        "sealed_context_id": sealed_context_id,
                        "probability": claim_with_evidence.probability,
                        "provider_trace_id": response.trace_id,
                        "verified_memory_ids": [item["memory_id"] for item in injected_by_agent.get(member.fingerprint, [])],
                    },
                )
                return {
                    "claim": claim_with_evidence.model_dump(mode="json"),
                    "trace_id": response.trace_id,
                    "cost": response.cost,
                    "latency_ms": response.latency_ms,
                    "usage": response.usage,
                }
            if node.kind == NodeKind.FALSIFIER:
                if node.identity is None or node.identity not in specs_by_hash:
                    raise RuntimeError("falsifier DAG node missing selected spec")
                spec = specs_by_hash[node.identity]
                if not self.services.sandbox.permits(spec.primitive):
                    raise RuntimeError(f"sandbox rejected primitive {spec.primitive}")
                reservation = await budget.reserve("falsifier", spec.estimated_cost, known_zero_cost=spec.estimated_cost == 0.0)
                if reservation is None:
                    ledger.append("budget_exhausted", {"node_id": node.node_id, "kind": node.kind.value, "category": "falsifier"})
                    return {"budget_exhausted": True}
                try:
                    execution = self.services.falsifiers.run(spec, fixture)
                except BaseException:
                    await budget.release(reservation, reason="falsifier failed")
                    raise
                await budget.reconcile(reservation, execution.cost)
                executions.append(execution)
                ledger.append("falsifier_executed", execution.model_dump(mode="json"))
                return execution.model_dump(mode="json")
            if node.kind == NodeKind.CHALLENGE:
                if len(claims_by_fp) < 2:
                    return {"opened": 0, "reason": "fewer than two live claims"}
                stagnation = 0
                previous_semantic_hash = sha256_obj({fp: claim.model_dump(mode="json") for fp, claim in sorted(claims_by_fp.items())})
                max_rounds = min(3, max(1, int(fixture.get("challenge_rounds", 3))))
                for round_no in range(1, max_rounds + 1):
                    fps = sorted(claims_by_fp)
                    candidates_for_edges: list[CommunicationCandidate] = []
                    for i, left_fp in enumerate(fps):
                        for right_fp in fps[i + 1 :]:
                            left, right = claims_by_fp[left_fp], claims_by_fp[right_fp]
                            disagreement = abs(left.probability - right.probability)
                            if bool(fixture.get("force_challenge", False)):
                                disagreement = max(0.35, disagreement)
                            left_member, right_member = selected_by_fp[left_fp], selected_by_fp[right_fp]
                            proximity = semantic_proximity(
                                SemanticSignature(left.statement, domain=left.domain, claim_type=left.claim_type, evidence_clusters=tuple(left.evidence_refs)),
                                SemanticSignature(right.statement, domain=right.domain, claim_type=right.claim_type, evidence_clusters=tuple(right.evidence_refs)),
                            )
                            candidates_for_edges.append(
                                CommunicationCandidate(
                                    challenger=left_fp,
                                    target=right_fp,
                                    residual_disagreement=disagreement,
                                    verified_reliability=self.calibration.direct_trust(left_fp, domain),
                                    task_relevance=1.0,
                                    capability_complementarity=1.0 if left_member.capabilities != right_member.capabilities else 0.4,
                                    correlation=correlation(left_member, right_member),
                                    semantic_proximity=proximity.score,
                                    expected_information_gain=max(0.2, disagreement),
                                    estimated_cost=float(fixture["challenge_cost"])
                                    if "challenge_cost" in fixture
                                    else float(self.provider.capabilities.estimated_max_cost_per_call or 0.0),
                                )
                            )
                    chosen = self.services.communication.select(candidates_for_edges, k=2)
                    if not chosen:
                        stagnation += 1
                    for edge in chosen:
                        target = claims_by_fp[edge.target]
                        challenge_request = ChallengeRequest(
                            challenger_fingerprint=edge.challenger,
                            target_fingerprint=edge.target,
                            target_claim_hash=target.hash,
                            target_statement_summary=target.statement[:500],
                            evidence_refs=list(target.evidence_refs),
                            falsifier_observations=[execution.model_dump(mode="json") for execution in executions],
                            challenge_reason=f"residual disagreement/information score={edge.score:.4f}",
                            round=round_no,
                        )
                        challenge_estimate = float(fixture["challenge_cost"]) if "challenge_cost" in fixture else self.provider.capabilities.estimated_max_cost_per_call
                        reservation = await budget.reserve("challenge", challenge_estimate, known_zero_cost=self.provider.capabilities.known_zero_cost)
                        if reservation is None:
                            ledger.append("budget_exhausted", {"node_id": node.node_id, "kind": node.kind.value, "category": "challenge", "round": round_no})
                            continue
                        try:
                            challenge_response = await self.provider.challenge_async(challenge_request)
                        except asyncio.CancelledError:
                            await budget.release(reservation, reason="challenge cancelled")
                            raise
                        except BaseException:
                            await budget.release(reservation, reason="challenge failed")
                            raise
                        await budget.reconcile(reservation, challenge_response.cost)
                        provider_call_count += 1
                        revised = target.model_copy(update={"probability": challenge_response.revised_probability, "status": challenge_response.revised_status})
                        claims_by_fp[edge.target] = revised
                        row = {
                            "round": round_no,
                            "source_fp": edge.challenger,
                            "target_fp": edge.target,
                            "reason": challenge_request.challenge_reason,
                            "score": edge.score,
                            "input_hash": challenge_request.hash,
                            "output_hash": challenge_response.hash,
                            "provider_call_id": challenge_response.provider_call_id,
                            "disposition": challenge_response.disposition,
                            "revised_probability": challenge_response.revised_probability,
                            "revised_status": challenge_response.revised_status.value,
                        }
                        communications.append(row)
                        ledger.append("communication_edge_opened", row)
                        ledger.append(
                            "challenge_completed",
                            {"input_hash": challenge_request.hash, "output_hash": challenge_response.hash, "provider_call_id": challenge_response.provider_call_id},
                        )
                    current_semantic_hash = sha256_obj({fp: claim.model_dump(mode="json") for fp, claim in sorted(claims_by_fp.items())})
                    if current_semantic_hash == previous_semantic_hash:
                        stagnation += 1
                    else:
                        stagnation = 0
                    previous_semantic_hash = current_semantic_hash
                    probabilities = [claim.probability for claim in claims_by_fp.values()]
                    if probabilities and max(probabilities) - min(probabilities) <= 0.05:
                        break
                    if stagnation >= 2:
                        communication_stagnated = True
                        progress.replan_reasons.append("sparse challenge stagnated for two checks")
                        break
                return {"opened": len(communications), "stagnated": communication_stagnated}
            if node.kind == NodeKind.JOIN:
                return {"claims": sorted(claims_by_fp), "falsifiers": sorted(execution.spec_hash for execution in executions), "communications": len(communications)}
            if node.kind == NodeKind.SYNTHESIS:
                return {"claim_count": len(claims_by_fp), "falsifier_count": len(executions)}
            if node.kind == NodeKind.LEARN:
                return {"eligible": request.learn}
            if node.kind == NodeKind.GERMINAL:
                return {"eligible": request.learn and bool(fixture.get("confirmed_evasion", False))}
            return {"kind": node.kind.value}

        executor = DagExecutor(request.max_concurrency)
        dag_execution: DagExecution = await executor.execute(plan, handle, precompleted=precompleted)
        ledger.append("dag_execution_completed", {"plan_hash": plan.plan_hash, "metrics": dag_execution.metrics.as_dict(), "schedule_hash": sha256_obj(dag_execution.schedule)})
        advance("EXECUTE_DAG", 0.22 if executions else 0.48)

        ordered_claims = [claims_by_fp[key] for key in sorted(claims_by_fp)]
        ordered_executions = sorted(executions, key=lambda row: row.spec_hash)
        if not ordered_claims:
            final_status = ClaimStatus.INCONCLUSIVE
        elif any(execution.verdict == Verdict.FAIL for execution in ordered_executions):
            final_status = ClaimStatus.FALSIFIED
        elif ordered_executions and all(execution.verdict == Verdict.PASS for execution in ordered_executions):
            final_status = ClaimStatus.SUPPORTED
        else:
            final_status = ClaimStatus.INCONCLUSIVE
        if communication_stagnated and not ordered_executions:
            final_status = ClaimStatus.INCONCLUSIVE
        for claim in ordered_claims:
            claim.status = final_status
            ledger.append("claim_updated", {"claim_id": claim.claim_id, "claim_hash": claim.hash, "status": claim.status.value})

        probabilities = [claim.probability for claim in ordered_claims]
        disagreement = max(probabilities) - min(probabilities) if len(probabilities) > 1 else 0.0
        ledger.append("consensus_stabilized", {"disagreement": disagreement, "challenge_edges": len(communications), "stagnation_count": progress.stagnation_count})

        if final_status == ClaimStatus.FALSIFIED:
            failed = next(execution for execution in ordered_executions if execution.verdict == Verdict.FAIL)
            failed_spec = next(spec for spec in selected_specs if spec.hash == failed.spec_hash)
            answer = f"Claim falsified by {failed_spec.primitive}."
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
        if request.learn and ordered_executions and ordered_claims:
            decisive = next((execution for execution in ordered_executions if execution.verdict in {Verdict.FAIL, Verdict.PASS}), None)
            if decisive is not None:
                owner = selected[0].fingerprint if selected else "system"
                candidate_memory = MemoryItem(
                    claim_hash=ordered_claims[0].hash,
                    content=f"Verified falsifier {decisive.spec_hash} produced {decisive.verdict.value} for scenario {scenario}",
                    owner_fingerprint=owner,
                    domain=domain,
                    origin_clusters=[decisive.execution_snapshot_hash],
                    authority=0.9,
                    deterministic_verification=True,
                    verified_clusters=[decisive.execution_snapshot_hash],
                )
                written = write_gate(candidate_memory)
                self.repository.save_memory_transition(written, reason="WRITE gate deterministic verification", from_status="candidate")
                ledger.append(
                    "memory_candidate_written", {"memory_id": written.memory_id, "claim_hash": written.claim_hash, "authority": written.authority, "status": written.status.value}
                )
                promoted_memory = promotion_gate(written)
                self.repository.save_memory_transition(promoted_memory, reason="PROMOTION gate", from_status=written.status.value)
                ledger.append("memory_promoted", {"memory_id": promoted_memory.memory_id, "status": promoted_memory.status.value, "authority": promoted_memory.authority})
                memory_changes.append(promoted_memory.model_dump(mode="json"))
        advance("LEARN_VERIFIED_ONLY", 0.09)

        germinal_changes: list[dict[str, Any]] = []
        if request.learn and bool(fixture.get("confirmed_evasion", False)):
            parent = next((spec for spec in selected_specs if spec.primitive == str(fixture.get("evasion_primitive", "numeric_invariant"))), None)
            if parent is None and "F1" in self.services.falsifiers.specs(domain):
                parent = self.services.falsifiers.specs(domain)["F1"]
            if parent is not None:
                parent_execution = self.services.falsifiers.run(parent, fixture)
                ground_truth_hash = str(fixture.get("ground_truth_hash") or sha256_obj({"expected": fixture.get("ground_truth_verdict", "FAIL"), "fixture": fixture}))
                evasion_hash = sha256_obj({"parent": parent.hash, "ground_truth": ground_truth_hash, "snapshot": parent_execution.execution_snapshot_hash})
                params = dict(parent.params)
                if parent.primitive == "numeric_invariant":
                    params["relative_tolerance"] = float(fixture.get("mutation_relative_tolerance", 0.02))
                candidate_probe = parent.model_copy(update={"version": f"2.0.{evasion_hash[:8]}", "params": params, "parent_hash": parent.hash})
                candidate_execution = self.services.falsifiers.run(candidate_probe, fixture)
                expected_fail = str(fixture.get("ground_truth_verdict", "FAIL")) == "FAIL"
                catches = candidate_execution.verdict == Verdict.FAIL if expected_fail else candidate_execution.verdict == Verdict.PASS
                mutation = mutate_params(
                    parent,
                    new_version=candidate_probe.version,
                    params=params,
                    triggering_snapshot_hash=parent_execution.execution_snapshot_hash,
                    catches_triggering_evasion=catches,
                )
                fossils = [fossil for fossil in seed_fossils() if fossil.primitive == parent.primitive]
                for fossil in fossils:
                    self.repository.seed_fossil(fossil.snapshot_hash, fossil.primitive, fossil.expected.value, asdict(fossil))
                decision = decide(parent, mutation, fossils)
                germinal_metrics = {
                    "reason": decision.reason,
                    "parent": asdict(decision.parent_metrics),
                    "candidate": asdict(decision.candidate_metrics),
                    "catches_triggering_evasion": catches,
                    "fossils_tested": decision.candidate_metrics.tested,
                }
                self.repository.persist_germinal_decision(
                    evasion_hash=evasion_hash,
                    parent_spec_hash=parent.hash,
                    ground_truth_hash=ground_truth_hash,
                    evasion_payload={"fixture_hash": sha256_obj(fixture), "parent_execution": parent_execution.model_dump(mode="json")},
                    candidate_hash=mutation.candidate.hash,
                    candidate_spec=mutation.candidate,
                    status=decision.status,
                    metrics=germinal_metrics,
                    domain=domain,
                )
                change = {
                    "evasion_hash": evasion_hash,
                    "parent_hash": parent.hash,
                    "candidate_hash": mutation.candidate.hash,
                    "status": decision.status,
                    "metrics": germinal_metrics,
                }
                germinal_changes.append(change)
                ledger.append("evasion_confirmed", {"evasion_hash": evasion_hash, "ground_truth_hash": ground_truth_hash, "parent_hash": parent.hash})
                ledger.append("mutation_candidate_written", {"candidate_hash": mutation.candidate.hash, "parent_hash": parent.hash, "state": "GERMINAL_QUARANTINE"})
                ledger.append("germinal_decision", change)
                if decision.status == "PROMOTE":
                    ledger.append("falsifier_promoted", {"spec_hash": mutation.candidate.hash, "version": mutation.candidate.version, "parent_hash": parent.hash})
        advance("GERMINAL", 0.05)

        task_ledger = TaskLedger(
            task=request.task,
            domain=domain,
            budget_usd=request.budget_usd,
            constraints={"max_agents": request.max_agents, "max_concurrency": request.max_concurrency, "depth": request.depth},
            plan=[node.kind.value for node in plan.nodes],
        )
        ledger.append(
            "run_completed",
            {
                "status": status,
                "task_ledger_hash": sha256_obj(task_ledger),
                "progress_ledger_hash": sha256_obj(progress),
                "plan_hash": plan.plan_hash,
                "execution_metrics_hash": sha256_obj(dag_execution.metrics.as_dict()),
            },
        )
        replay = verify_replay(ledger.events, ledger.head)

        falsifier_rows = [
            execution.model_dump(mode="json")
            | {
                "id": next(spec.id for spec in selected_specs if spec.hash == execution.spec_hash),
                "primitive": next(spec.primitive for spec in selected_specs if spec.hash == execution.spec_hash),
                "persistent_reuse": execution.spec_hash in persistent_falsifiers_reused,
            }
            for execution in ordered_executions
        ]
        final_claims = [claim.model_dump(mode="json") | {"claim_hash": claim.hash, "provider_trace_id": claim_trace_ids.get(fp)} for fp, claim in sorted(claims_by_fp.items())]
        metrics: dict[str, float | int] = dag_execution.metrics.as_dict()
        coalition = {
            "members": [member.fingerprint for member in selected],
            "names": [member.name for member in selected],
            "topology": plan.name.value,
            "morphology": plan.name.value,
            "rationale": rationale,
            "plan_hash": plan.plan_hash,
        }
        all_evidence_rows = base_evidence_rows + [evidence_row(execution_evidence(item)) for item in ordered_executions]
        budget_snapshot = budget.snapshot()
        budget_snapshot.update({"latency_ms": sum(execution.latency_ms for execution in ordered_executions), "max_tests": max_tests, "max_concurrency": request.max_concurrency})
        result = RunResult(
            run_id=run_id,
            status=status,
            answer=answer,
            confidence=confidence,
            final_claims=final_claims,
            disagreements=[] if disagreement <= 0.05 else [{"probability_span": disagreement}],
            falsifiers=falsifier_rows,
            evidence_provenance={
                "scenario": scenario,
                "fixture_hash": sha256_obj(fixture),
                "source_clusters": fixture.get("clusters", []),
                "pinned_registry_hash": fixture.get("registry_snapshot_hash"),
                "plan_hash": plan.plan_hash,
                "provider": self.provider.capabilities.__dict__,
                "provider_usages": provider_usages,
                "evidence_hashes": [row["evidence_hash"] for row in all_evidence_rows],
            },
            coalition=coalition,
            budget=budget_snapshot,
            ledger_head=ledger.head,
            memory_changes=memory_changes,
            germinal_changes=germinal_changes,
            replay_verified=bool(replay["verified"]),
            event_types=[event.event_type for event in ledger.events],
            plugin_hashes=self.plugin_hashes,
            plan_hash=plan.plan_hash,
            morphology=plan.name.value,
            provider_call_count=provider_call_count,
            challenge_edge_count=len(communications),
            concurrency_summary={
                "peak_concurrency": metrics["peak_concurrency"],
                "parallel_speedup_estimate": metrics["parallel_speedup_estimate"],
                "parallel_efficiency": metrics["parallel_efficiency"],
                "avoidable_serialization_count": metrics["avoidable_serialization_count"],
                "subtask_finish_rate": metrics["subtask_finish_rate"],
            },
            critical_path_summary={
                "work_steps": metrics["work_steps"],
                "critical_steps": metrics["critical_steps"],
                "critical_path_ms": metrics["critical_path_ms"],
                "observed_wall_ms": metrics["observed_wall_ms"],
                "serial_work_ms": metrics["serial_work_ms"],
            },
            persistent_memory_reused=sorted(persistent_memory_reused),
            persistent_falsifiers_reused=sorted(set(persistent_falsifiers_reused)),
            lineage_exclusions={key: sorted(value) for key, value in lineage_exclusions.items()},
        )
        self.repository.save_run_bundle(
            run_id=run_id,
            task_hash=task_hash,
            config_hash=config_hash,
            status=status,
            ledger_head=ledger.head,
            result=result.model_dump(mode="json"),
            events=ledger.events,
            task_ledger=task_ledger.model_dump(mode="json"),
            progress_rows=progress_rows,
            coalition=coalition,
            plan_hash=plan.plan_hash,
            plan=plan.as_dict(),
            communications=communications,
            claims=final_claims,
            evidence=all_evidence_rows,
            executions=ordered_executions,
        )
        return result

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        result = self.repository.get_run(run_id)
        if result is None:
            return None
        events = self.repository.get_events(run_id)
        replay = verify_replay(events, str(result["ledger_head"]))
        return result | {"replay_state": replay, "events": events, "persistent_state": self.repository.inspect_state(run_id)}
