from __future__ import annotations

import asyncio
from dataclasses import asdict, replace
from typing import Any, Literal
from uuid import NAMESPACE_URL, uuid4, uuid5

from mimicus.agents.auditions import CANARY_BANK, audition
from mimicus.agents.bankruptcy import evaluate_bankruptcy
from mimicus.agents.calibration import capability_scope
from mimicus.canonical import sha256_obj
from mimicus.claims.evidence import evidence_row, execution_evidence
from mimicus.claims.evidence_bundle import explicit_fixture_bundle, runtime_evidence_bundle
from mimicus.claims.models import Claim
from mimicus.coalition.selector import AgentCandidate
from mimicus.coalition.threat_profile import ThreatProfile, profile_task
from mimicus.events.ledger import EventLedger
from mimicus.falsifiers.market import ClaimFalsifierBid, FalsifierMarket
from mimicus.falsifiers.primitives import execute_claim_bound
from mimicus.falsifiers.spec import FalsifierExecution, FalsifierSpec
from mimicus.orchestration.budget import BudgetLedger
from mimicus.orchestration.communication import ChallengeRequest, CommunicationCandidate
from mimicus.orchestration.dag_executor import DagExecution, DagExecutor
from mimicus.orchestration.decomposition import Subtask, decompose_task
from mimicus.orchestration.morphology import DagEdge, DagNode, MorphologyName, MorphologyPlan, NodeKind
from mimicus.orchestration.proximity import SemanticSignature, semantic_proximity
from mimicus.orchestration.replay import verify_replay
from mimicus.orchestration.synthesis import SwarmDecision, synthesize_swarm
from mimicus.orchestration.task_ledger import TaskLedger
from mimicus.providers.base import AuditionRequest, ProviderRequest
from mimicus.storage.swarm_state import SwarmStateStore
from mimicus.types import BankruptcyState, ClaimStatus

_CANARY_FOR = {
    "numeric": "parameter_trap",
    "freshness": "temporal_decoy",
    "independence": "semantic_decoy",
    "entailment": "granularity_trap",
    "counterexample": "prerequisite_blindness",
    "synthesize": "capability_mirage",
    "source": "semantic_decoy",
    "critic": "capability_mirage",
}


def _core_node_id(kind: NodeKind, index: int, identity: str | None = None) -> str:
    return f"core-{kind.value.lower()}-{index:02d}-{sha256_obj({'kind': kind.value, 'index': index, 'identity': identity})[:10]}"


def _compile_core_plan(
    *,
    task_hash: str,
    selected: list[AgentCandidate],
    candidate_specs: list[FalsifierSpec],
    profile: ThreatProfile,
    subtasks: list[Subtask],
    max_concurrency: int,
) -> tuple[MorphologyPlan, dict[str, Subtask]]:
    count = len(selected)
    caps = profile.required_capabilities
    if count <= 1:
        name = MorphologyName.SOLO
    elif caps == ("synthesize",) or set(caps) == {"synthesize"}:
        name = MorphologyName.PAIRED_VERIFY
    elif len(caps) >= 5 and count >= 3:
        name = MorphologyName.HIERARCHICAL_FANOUT_FANIN
    elif len(caps) >= 3 and count >= 3:
        name = MorphologyName.SPARSE_GRAPH
    else:
        name = MorphologyName.PARALLEL_FANOUT
    profile_node = DagNode(_core_node_id(NodeKind.PROFILE, 0), NodeKind.PROFILE, input_hash=task_hash)
    memory = DagNode(_core_node_id(NodeKind.MEMORY_RETRIEVE, 0), NodeKind.MEMORY_RETRIEVE, (profile_node.node_id,), input_hash=task_hash)
    audition_node = DagNode(_core_node_id(NodeKind.AUDITION, 0), NodeKind.AUDITION, (profile_node.node_id,), input_hash=task_hash)
    nodes = [profile_node, memory, audition_node]
    edges = [DagEdge(profile_node.node_id, memory.node_id), DagEdge(profile_node.node_id, audition_node.node_id)]
    parent_ids: tuple[str, ...] = (memory.node_id, audition_node.node_id)
    if name == MorphologyName.HIERARCHICAL_FANOUT_FANIN:
        decompose = DagNode(_core_node_id(NodeKind.DECOMPOSE, 0, task_hash), NodeKind.DECOMPOSE, parent_ids, input_hash=task_hash, group="hierarchy-root")
        nodes.append(decompose)
        edges.extend([DagEdge(memory.node_id, decompose.node_id, "decomposition"), DagEdge(audition_node.node_id, decompose.node_id, "decomposition")])
        parent_ids = (decompose.node_id,)
    assignment: dict[str, Subtask] = {}
    assignment_agents: dict[str, str] = {}
    unresolved: list[str] = []
    agent_nodes: list[DagNode] = []
    if name == MorphologyName.HIERARCHICAL_FANOUT_FANIN:
        loads = {member.fingerprint: 0 for member in selected}
        for index, subtask in enumerate(subtasks):
            qualified = [
                member
                for member in selected
                if set(subtask.required_capabilities).issubset(member.capabilities)
                and all(member.capability_states.get(capability, "ACTIVE") == "ACTIVE" for capability in subtask.required_capabilities)
            ]
            if not qualified:
                unresolved.append(subtask.hash)
                continue
            member = min(qualified, key=lambda row: (loads[row.fingerprint], row.fingerprint))
            loads[member.fingerprint] += 1
            node = DagNode(
                _core_node_id(NodeKind.AGENT_TASK, index, f"{member.fingerprint}:{subtask.hash}"),
                NodeKind.AGENT_TASK,
                parent_ids,
                identity=member.fingerprint,
                input_hash=subtask.hash,
                group=subtask.dependency_group,
            )
            assignment[node.node_id] = subtask
            assignment_agents[node.node_id] = member.fingerprint
            nodes.append(node)
            agent_nodes.append(node)
            for parent in parent_ids:
                edges.append(DagEdge(parent, node.node_id, "subtask_fanout", subtask.dependency_group))
    else:
        for index, member in enumerate(selected):
            group = "paired" if name == MorphologyName.PAIRED_VERIFY else "fanout"
            node = DagNode(
                _core_node_id(NodeKind.AGENT_TASK, index, member.fingerprint),
                NodeKind.AGENT_TASK,
                parent_ids,
                identity=member.fingerprint,
                input_hash=sha256_obj({"task": task_hash, "agent": member.fingerprint}),
                group=group,
            )
            nodes.append(node)
            agent_nodes.append(node)
            for parent in parent_ids:
                edges.append(DagEdge(parent, node.node_id, "worker_fanout", group))
    post_first_pass: list[str]
    subgroup_joins: list[DagNode] = []
    if name == MorphologyName.HIERARCHICAL_FANOUT_FANIN:
        groups = sorted({str(node.group) for node in agent_nodes if node.group})
        for group_index, group in enumerate(groups, start=1):
            members = [node for node in agent_nodes if node.group == group]
            join = DagNode(
                _core_node_id(NodeKind.JOIN, group_index, group),
                NodeKind.JOIN,
                tuple(node.node_id for node in members),
                input_hash=sha256_obj([node.input_hash for node in members]),
                group=f"subgroup:{group}",
            )
            nodes.append(join)
            subgroup_joins.append(join)
            for member_node in members:
                edges.append(DagEdge(member_node.node_id, join.node_id, "nested_subtask_fanin", group))
        post_first_pass = [node.node_id for node in subgroup_joins]
    else:
        post_first_pass = [node.node_id for node in agent_nodes]
    falsifier_nodes: list[DagNode] = []
    for index, spec in enumerate(candidate_specs):
        node = DagNode(
            _core_node_id(NodeKind.FALSIFIER, index, spec.hash),
            NodeKind.FALSIFIER,
            tuple(post_first_pass),
            identity=spec.hash,
            input_hash=sha256_obj({"task": task_hash, "spec": spec.hash, "phase": "post-first-pass"}),
            group="claim-aware-market",
        )
        nodes.append(node)
        falsifier_nodes.append(node)
        for parent in post_first_pass:
            edges.append(DagEdge(parent, node.node_id, "claim_aware_falsifier_after_first_pass", "claim-aware-market"))
    upstream = list(post_first_pass) + [node.node_id for node in falsifier_nodes]
    if name in {MorphologyName.PAIRED_VERIFY, MorphologyName.SPARSE_GRAPH} and len(agent_nodes) >= 2:
        semantics = "explicit_peer_verification" if name == MorphologyName.PAIRED_VERIFY else "selective_sparse_communication"
        challenge = DagNode(
            _core_node_id(NodeKind.CHALLENGE, 0, name.value),
            NodeKind.CHALLENGE,
            tuple([node.node_id for node in agent_nodes] + [node.node_id for node in falsifier_nodes]),
            input_hash=task_hash,
            group=semantics,
        )
        nodes.append(challenge)
        for parent in challenge.prerequisites:
            edges.append(DagEdge(parent, challenge.node_id, semantics, semantics))
        upstream.append(challenge.node_id)
    final_join = DagNode(_core_node_id(NodeKind.JOIN, 0, name.value), NodeKind.JOIN, tuple(sorted(set(upstream))), input_hash=task_hash, group="final-fanin")
    synthesis = DagNode(_core_node_id(NodeKind.SYNTHESIS, 0), NodeKind.SYNTHESIS, (final_join.node_id,), input_hash=task_hash)
    nodes.extend([final_join, synthesis])
    for parent in final_join.prerequisites:
        edges.append(DagEdge(parent, final_join.node_id, "final_fanin"))
    edges.append(DagEdge(final_join.node_id, synthesis.node_id, "synthesize_actual_swarm_outputs"))
    plan = MorphologyPlan(
        name=name,
        nodes=nodes,
        edges=edges,
        compiler_rationale={
            "swarm_core": "ORDER-007",
            "selected_agents": count,
            "required_capabilities": list(caps),
            "subtask_hashes": [row.hash for row in subtasks],
            "subtask_assignments": {node_id: row.hash for node_id, row in assignment.items()},
            "subtask_assignment_agents": assignment_agents,
            "unresolved_subtasks": unresolved,
            "claim_aware_market_after_first_pass": True,
            "max_concurrency": max_concurrency,
        },
    )
    plan.validate()
    return plan, assignment


def _blend_verified_authority(host: Any, fingerprint: str, domain: str, capability: str, canary_trust: float) -> float:
    verified = SwarmStateStore(host.repository.engine).verified_authority(fingerprint, domain, capability)
    attempts = int(verified["attempts"])
    if attempts == 0:
        return canary_trust
    weight = min(0.75, attempts / (attempts + 3.0))
    return (1.0 - weight) * canary_trust + weight * float(verified["trust"])


async def execute_swarm_core(host: Any, request: Any) -> dict[str, Any]:
    run_id = str(uuid4())
    domain = request.domain or "general"
    scenario = request.scenario or ("benchmark" if request.source_mode == "benchmark" else "runtime")
    fixture = dict(request.fixture)
    if request.source_mode == "runtime":
        evidence_bundle = runtime_evidence_bundle(run_id, request.evidence)
    else:
        evidence_bundle = explicit_fixture_bundle(run_id, fixture, domain=domain, scenario=scenario, benchmark=request.source_mode == "benchmark")
    evidence_context = evidence_bundle.falsifier_context()
    ledger = EventLedger(run_id)
    task_hash = sha256_obj({"task": request.task, "domain": domain, "source_mode": request.source_mode, "evidence_hashes": evidence_bundle.hashes})
    config_hash = sha256_obj(
        {
            "budget_usd": request.budget_usd,
            "max_agents": request.max_agents,
            "max_concurrency": request.max_concurrency,
            "depth": request.depth,
            "learn": request.learn,
            "core": "ORDER-006",
        }
    )
    ledger.append("run_started", {"task_hash": task_hash, "config_hash": config_hash, "plugin_hashes": host.plugin_hashes, "swarm_core": "ORDER-007"})
    ledger.append("evidence_bundle_prepared", {"source_mode": request.source_mode, "evidence_hashes": list(evidence_bundle.hashes), "count": len(evidence_bundle.items)})
    retrieved_memory = host.services.memory.retrieve(domain)
    base_candidates = host.services.agent_factory.candidates()
    available_caps = tuple(sorted({cap for candidate in base_candidates for cap in candidate.capabilities}))
    store = SwarmStateStore(host.repository.engine)
    profile = profile_task(
        request.task,
        domain,
        scenario,
        evidence_facts=evidence_context,
        verified_memory_coverage=tuple(sorted({"synthesize" for _ in retrieved_memory})),
        prior_verified_failure_modes=store.prior_failure_modes(domain),
        available_capabilities=available_caps,
        budget_usd=request.budget_usd,
        max_concurrency=request.max_concurrency,
    )
    ledger.append("threat_profiled", profile.model_dump(mode="json"))

    budget = BudgetLedger(request.budget_usd)
    provider_estimate = host.provider.capabilities.estimated_max_cost_per_call
    if provider_estimate is None and host.provider.capabilities.known_zero_cost:
        provider_estimate = 0.0

    audited: list[AgentCandidate] = []
    lineage_exclusions: dict[str, list[str]] = {"bankrupt": [], "probation": []}
    audition_records: list[dict[str, Any]] = []
    for candidate in base_candidates:
        identity = host.services.agent_factory.identity_for(candidate)
        host.repository.register_identity(identity)
        candidate = replace(candidate, lineage_id=identity.lineage_id)
        relevant_caps = [cap for cap in profile.required_capabilities if cap in candidate.capabilities]
        if not relevant_caps:
            audition_records.append({"fingerprint": candidate.fingerprint, "capability": None, "applicability": "NOT_APPLICABLE", "passed": None})
            audited.append(replace(candidate, audition_score=0.5, calibration_score=0.5))
            continue
        scores: dict[str, float] = {}
        calibrations: dict[str, float] = {}
        states: dict[str, str] = {}
        for capability in relevant_caps:
            category = _CANARY_FOR.get(capability, "semantic_decoy")
            family = f"{capability}_canary"
            canary_prompt = CANARY_BANK[category][0]
            sealed = str(uuid5(NAMESPACE_URL, f"{run_id}:{candidate.fingerprint}:{capability}:audition"))
            if not host.provider.capabilities.supports_auditions:
                state_key = capability_scope(domain, capability, family)
                current_state = host.repository.bankruptcy_state(candidate.fingerprint, state_key)
                scores[capability] = 0.5
                calibrations[capability] = _blend_verified_authority(host, candidate.fingerprint, domain, capability, 0.5)
                states[capability] = current_state
                audition_row = {
                    "fingerprint": candidate.fingerprint,
                    "phenotype": candidate.name,
                    "capability": capability,
                    "category": category,
                    "test_family": family,
                    "prompt_hash": sha256_obj(canary_prompt),
                    "provider_trace_id": None,
                    "provider_executed": False,
                    "applicability": "PROVIDER_UNSUPPORTED",
                    "passed": None,
                    "score": 0.5,
                    "routing_state": current_state,
                }
                audition_records.append(audition_row)
                ledger.append("agent_audition_unsupported", audition_row)
                continue
            audition_reservation = await budget.reserve(
                "audition",
                provider_estimate,
                known_zero_cost=host.provider.capabilities.known_zero_cost,
            )
            if audition_reservation is None:
                state_key = capability_scope(domain, capability, family)
                current_state = host.repository.bankruptcy_state(candidate.fingerprint, state_key)
                scores[capability] = 0.5
                calibrations[capability] = _blend_verified_authority(host, candidate.fingerprint, domain, capability, 0.5)
                states[capability] = current_state
                audition_row = {
                    "fingerprint": candidate.fingerprint,
                    "phenotype": candidate.name,
                    "capability": capability,
                    "category": category,
                    "test_family": family,
                    "prompt_hash": sha256_obj(canary_prompt),
                    "provider_trace_id": None,
                    "provider_executed": False,
                    "applicability": "BUDGET_BLOCKED",
                    "passed": None,
                    "score": 0.5,
                    "routing_state": current_state,
                }
                audition_records.append(audition_row)
                ledger.append("agent_audition_budget_blocked", audition_row)
                continue
            try:
                provider_result = await host.provider.audition_async(
                    AuditionRequest(
                        fingerprint=candidate.fingerprint,
                        domain=domain,
                        phenotype=candidate.name,
                        capability=capability,
                        test_family=family,
                        category=category,
                        prompt=canary_prompt,
                        sealed_context_id=sealed,
                    )
                )
            except BaseException:
                await budget.release(audition_reservation, reason="audition failure/cancellation")
                raise
            await budget.reconcile(audition_reservation, provider_result.cost)
            scored = audition(
                candidate.fingerprint,
                domain,
                category,
                provider_result.answer,
                capability=capability,
                test_family=family,
                supported=provider_result.supported,
            )
            state_key = capability_scope(domain, capability, family)
            current_state = host.repository.bankruptcy_state(candidate.fingerprint, state_key)
            if scored.affects_trust:
                assert scored.passed is not None
                calibration = host.calibration.record_capability_verified(
                    candidate.fingerprint,
                    domain,
                    capability,
                    family,
                    predicted_probability=0.8,
                    outcome=scored.passed,
                    canary=True,
                )
                evaluated = evaluate_bankruptcy(calibration)
                if evaluated.state == BankruptcyState.BANKRUPT:
                    host.repository.set_bankruptcy_state(candidate.fingerprint, state_key, "BANKRUPT", evaluated.reason or "real hidden canary bankruptcy")
                    current_state = "BANKRUPT"
                canary_trust = calibration.trust
                calibrations[capability] = _blend_verified_authority(host, candidate.fingerprint, domain, capability, canary_trust)
            else:
                calibrations[capability] = _blend_verified_authority(host, candidate.fingerprint, domain, capability, 0.5)
            scores[capability] = scored.score
            states[capability] = current_state
            if current_state == "BANKRUPT":
                lineage_exclusions["bankrupt"].append(candidate.fingerprint)
            audition_row = {
                "fingerprint": candidate.fingerprint,
                "phenotype": candidate.name,
                "capability": capability,
                "category": category,
                "test_family": family,
                "prompt_hash": sha256_obj(canary_prompt),
                "provider_trace_id": provider_result.trace_id,
                "provider_executed": provider_result.supported,
                "applicability": scored.applicability,
                "passed": scored.passed,
                "score": scored.score,
                "routing_state": current_state,
            }
            audition_records.append(audition_row)
            ledger.append("agent_auditioned", audition_row)
        audited.append(
            replace(
                candidate,
                audition_score=sum(scores.values()) / len(scores),
                calibration_score=sum(calibrations.values()) / len(calibrations),
                bankrupt=bool(states) and all(value == "BANKRUPT" for value in states.values()),
                capability_audition_scores=scores,
                capability_calibration_scores=calibrations,
                capability_states=states,
            )
        )

    fingerprints = [candidate.fingerprint for candidate in audited]
    pair_signals, marginal_signals = store.signals(fingerprints, domain, profile.required_capabilities)
    audited = [
        replace(candidate, historical_cofailure=pair_signals.get(candidate.fingerprint, {}), historical_marginal_value=marginal_signals.get(candidate.fingerprint, {}))
        for candidate in audited
    ]
    selected, rationale = host.services.coalition.select(profile, audited, request.max_agents)
    required = set(profile.required_capabilities)
    if len(selected) == 1 and len(selected) < request.max_agents:
        overlap_candidates = [
            candidate
            for candidate in audited
            if candidate not in selected and any(cap in required and candidate.capability_states.get(cap, "ACTIVE") == "ACTIVE" for cap in candidate.capabilities)
        ]
        if (profile.required_capabilities == ("synthesize",) or len(required) >= 2) and overlap_candidates:
            secondary = min(
                overlap_candidates,
                key=lambda row: (
                    max((row.historical_cofailure.get(member.fingerprint, 0.0) for member in selected), default=0.0),
                    row.fingerprint,
                ),
            )
            selected.append(secondary)
            rationale["secondary_verifier"] = secondary.fingerprint
            rationale["secondary_reason"] = "bounded redundancy for unresolved structural authority"
    ledger.append("coalition_selected", {"members": [row.fingerprint for row in selected], "rationale": rationale})

    injected_by_agent: dict[str, list[dict[str, Any]]] = {}
    persistent_memory_reused: set[str] = set()
    for member in selected:
        injected: list[dict[str, Any]] = []
        for item in retrieved_memory:
            if host.services.memory.injectable(item, member.fingerprint, domain):
                injected.append(item.model_dump(mode="json"))
                persistent_memory_reused.add(item.memory_id)
        injected_by_agent[member.fingerprint] = injected

    builtins = host.services.falsifiers.specs(domain)
    promoted = host.repository.promoted_falsifiers(domain)
    registry_by_hash = {spec.hash: spec for spec in [*builtins.values(), *promoted]}
    superseded_hashes = {spec.parent_hash for spec in promoted if spec.parent_hash}
    candidate_specs = sorted(
        (spec for spec in registry_by_hash.values() if spec.hash not in superseded_hashes),
        key=lambda spec: spec.hash,
    )
    promoted_hashes = {row.hash for row in promoted}
    persistent_falsifiers_reused = [spec.hash for spec in candidate_specs if spec.hash in promoted_hashes]
    if superseded_hashes:
        ledger.append(
            "falsifier_registry_lineage_superseded",
            {"suppressed_ancestor_hashes": sorted(superseded_hashes), "active_registry_hashes": [spec.hash for spec in candidate_specs]},
        )
    if candidate_specs and not evidence_bundle.items:
        ledger.append(
            "evidence_missing",
            {
                "reason": "evidence_required_falsifier_has_no_structured_evidence",
                "source_mode": request.source_mode,
                "falsifier_primitives": [spec.primitive for spec in candidate_specs],
            },
        )
    subtasks = decompose_task(task_hash, profile, evidence_context)
    plan, subtask_assignment = _compile_core_plan(
        task_hash=task_hash,
        selected=selected,
        candidate_specs=candidate_specs,
        profile=profile,
        subtasks=subtasks,
        max_concurrency=request.max_concurrency,
    )
    ledger.append(
        "morphology_compiled",
        {"plan_hash": plan.plan_hash, "morphology": plan.name.value, "structural_signature": plan.structural_signature, "subtask_hashes": [row.hash for row in subtasks]},
    )

    planned_members = [row.fingerprint for row in selected]
    pricing_preflight: dict[str, Any] = {
        "status": "READY",
        "planned_paid_calls": len(selected),
        "estimated_max_cost_per_call": provider_estimate,
        "configured_budget_usd": request.budget_usd,
        "planned_members": planned_members,
    }
    if selected and not host.provider.capabilities.known_zero_cost and provider_estimate is None and len(selected) > 1:
        selected = []
        pricing_preflight.update({"status": "PRICING_PREFLIGHT_REQUIRED", "reason": "pricing_preflight_required", "executed_members": []})
        rationale["pricing_preflight"] = pricing_preflight
        ledger.append("pricing_preflight_required", pricing_preflight)
    elif provider_estimate is not None and provider_estimate > 0.0:
        affordable = int((budget.remaining_usd + 1e-12) // provider_estimate)
        if affordable < len(selected):
            selected = selected[: max(0, affordable)]
            pricing_preflight.update(
                {
                    "status": "DEGRADED_BEFORE_EXECUTION" if selected else "INSUFFICIENT_BUDGET",
                    "reason": "insufficient_preflight_budget",
                    "executed_members": [row.fingerprint for row in selected],
                }
            )
            rationale["pricing_preflight"] = pricing_preflight
            ledger.append("pricing_preflight_degraded", pricing_preflight)
    pricing_preflight.setdefault("executed_members", [row.fingerprint for row in selected])
    selected_by_fp = {row.fingerprint: row for row in selected}
    spec_by_hash = {row.hash: row for row in candidate_specs}
    claims_by_node: dict[str, Claim] = {}
    claim_owner_by_node: dict[str, str] = {}
    claim_trace_ids: dict[str, str | None] = {}
    claim_context_by_identity: dict[str, dict[str, Any]] = {}
    provider_usages: list[dict[str, Any]] = []
    executions: list[FalsifierExecution] = []
    communications: list[dict[str, Any]] = []
    subgroup_results: dict[str, dict[str, Any]] = {}
    executed_subtask_hashes: set[str] = set()
    provider_call_count = 0
    market_lock = asyncio.Lock()
    market_selected: list[ClaimFalsifierBid] | None = None
    market_all: list[ClaimFalsifierBid] = []
    decision: SwarmDecision | None = None
    selected_market_specs: set[str] = set()

    precompleted: dict[str, object] = {}
    for node in plan.nodes:
        if node.kind == NodeKind.PROFILE:
            node.status = "COMPLETED"
            payload = profile.model_dump(mode="json")
            node.output_hash = sha256_obj(payload)
            precompleted[node.node_id] = payload
        elif node.kind == NodeKind.MEMORY_RETRIEVE:
            node.status = "COMPLETED"
            payload = {"memory_ids": [item.memory_id for item in retrieved_memory]}
            node.output_hash = sha256_obj(payload)
            precompleted[node.node_id] = payload
        elif node.kind == NodeKind.AUDITION:
            node.status = "COMPLETED"
            payload = {"auditions": audition_records}
            node.output_hash = sha256_obj(payload)
            precompleted[node.node_id] = payload

    def scoped_evidence_payload(subtask: Subtask | None) -> tuple[dict[str, Any], ...]:
        if subtask is None:
            return evidence_bundle.provider_payload()
        scope = set(subtask.evidence_scope)
        scoped: list[dict[str, Any]] = []
        for item in evidence_bundle.items:
            facts = {key: value for key, value in item.extracted_facts.items() if key in scope}
            if not facts:
                continue
            payload = item.provider_payload()
            payload["extracted_facts"] = facts
            payload["content"] = ""
            scoped.append(payload)
        return tuple(scoped)

    def scoped_context(payload: tuple[dict[str, Any], ...]) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        conflicts: set[str] = set()
        for row in payload:
            facts = row.get("extracted_facts", {})
            if not isinstance(facts, dict):
                continue
            for key, value in facts.items():
                if key in conflicts:
                    continue
                if key in merged and sha256_obj(merged[key]) != sha256_obj(value):
                    merged.pop(key, None)
                    conflicts.add(key)
                else:
                    merged[key] = value
        if conflicts:
            merged["evidence_conflicts"] = sorted(conflicts)
        return merged

    async def ensure_market() -> list[ClaimFalsifierBid]:
        nonlocal market_selected, market_all
        async with market_lock:
            if market_selected is not None:
                return market_selected
            projected = float(provider_estimate or 0.0) * len(selected)
            market_budget = max(0.0, request.budget_usd - min(request.budget_usd, projected))
            market_selected, market_all = FalsifierMarket().select_for_claims(
                candidate_specs,
                [claims_by_node[key] for key in sorted(claims_by_node)],
                evidence=evidence_context,
                budget_usd=market_budget,
                max_tests={"fast": 1, "normal": 3, "deep": 5}[request.depth],
                evidence_quality=1.0 if evidence_bundle.items else 0.0,
            )
            ledger.append(
                "falsifier_market_scored",
                {
                    "phase": "after_sealed_first_pass",
                    "registry_scope": "full_safe_registry_plus_promoted",
                    "selected": [asdict(row) for row in market_selected],
                    "candidates": [asdict(row) for row in market_all],
                },
            )
            return market_selected

    async def handle(node: DagNode) -> object:
        nonlocal provider_call_count, decision
        ledger.append("dag_node_started", {"node_id": node.node_id, "kind": node.kind.value, "input_hash": node.input_hash})
        if node.kind == NodeKind.DECOMPOSE:
            payload = {"subtasks": [row.model_dump(mode="json") | {"subtask_hash": row.hash} for row in subtasks]}
            ledger.append("task_decomposed", payload)
            return payload
        if node.kind == NodeKind.AGENT_TASK:
            if node.identity is None or node.identity not in selected_by_fp:
                return {"skipped": True, "reason": "member removed by preflight"}
            member = selected_by_fp[node.identity]
            reservation = await budget.reserve("agent_generation", provider_estimate, known_zero_cost=host.provider.capabilities.known_zero_cost)
            if reservation is None:
                return {"budget_exhausted": True}
            subtask = subtask_assignment.get(node.node_id)
            task_payload = subtask.objective if subtask is not None else request.task
            runtime_payload = scoped_evidence_payload(subtask)
            allowed_refs = {str(row["evidence_hash"]) for row in runtime_payload}
            sealed = str(uuid5(NAMESPACE_URL, f"{run_id}:{member.fingerprint}:{node.input_hash}:sealed"))
            provider_request = ProviderRequest(
                task_payload,
                domain,
                member.name,
                sealed,
                fixture if request.source_mode != "runtime" else {},
                tuple(injected_by_agent.get(member.fingerprint, [])),
                runtime_payload,
            )
            try:
                response = await host.provider.generate_request_async(provider_request)
            except BaseException:
                await budget.release(reservation, reason="provider failure/cancellation")
                raise
            reconciliation = await budget.reconcile(reservation, response.cost)
            provider_call_count += 1
            claimed_refs = list(dict.fromkeys(response.claim.evidence_refs))
            validated_refs = [ref for ref in claimed_refs if ref in allowed_refs]
            rejected_refs = [ref for ref in claimed_refs if ref not in allowed_refs]
            claim = response.claim.model_copy(update={"evidence_refs": validated_refs})
            claims_by_node[node.node_id] = claim
            claim_context_by_identity[claim.identity_hash] = scoped_context(runtime_payload)
            claim_owner_by_node[node.node_id] = member.fingerprint
            claim_trace_ids[node.node_id] = response.trace_id
            if subtask is not None:
                executed_subtask_hashes.add(subtask.hash)
            provider_usages.append(
                {
                    "fingerprint": member.fingerprint,
                    "node_id": node.node_id,
                    "trace_id": response.trace_id,
                    "usage": dict(response.usage)
                    | {
                        "evidence_hashes_supplied": sorted(allowed_refs),
                        "evidence_refs_claimed": claimed_refs,
                        "evidence_refs_validated": validated_refs,
                        "evidence_refs_rejected": rejected_refs,
                        "subtask_hash": None if subtask is None else subtask.hash,
                        "evidence_scope": [] if subtask is None else list(subtask.evidence_scope),
                    },
                    "budget": reconciliation,
                }
            )
            if rejected_refs:
                ledger.append(
                    "evidence_ref_rejected",
                    {"fingerprint": member.fingerprint, "node_id": node.node_id, "rejected_refs": rejected_refs, "allowed_refs": sorted(allowed_refs)},
                )
            ledger.append(
                "claim_proposed",
                {
                    "claim_hash": claim.hash,
                    "claim_identity_hash": claim.identity_hash,
                    "claim_revision_hash": claim.revision_hash,
                    "fingerprint": member.fingerprint,
                    "node_id": node.node_id,
                    "probability": claim.probability,
                    "provider_trace_id": response.trace_id,
                    "evidence_refs": validated_refs,
                    "subtask_hash": None if subtask is None else subtask.hash,
                    "provider_task_hash": sha256_obj(task_payload),
                },
            )
            return {"claim": claim.model_dump(mode="json"), "claim_identity_hash": claim.identity_hash, "subtask_hash": None if subtask is None else subtask.hash}
        if node.kind == NodeKind.FALSIFIER:
            if node.identity is None or node.identity not in spec_by_hash:
                return {"skipped": True}
            bids = await ensure_market()
            relevant = [bid for bid in bids if bid.spec_hash == node.identity]
            if not relevant:
                return {"selected": False, "reason": "market did not retain spec for any claim"}
            spec = spec_by_hash[node.identity]
            selected_market_specs.add(spec.hash)
            if not host.services.sandbox.permits(spec.primitive):
                raise RuntimeError(f"sandbox rejected primitive {spec.primitive}")
            claim_by_identity = {claim.identity_hash: claim for claim in claims_by_node.values()}
            node_executions: list[dict[str, Any]] = []
            for bid in sorted(relevant, key=lambda row: (row.target_claim_hash, row.selection_reason)):
                claim = claim_by_identity.get(bid.target_claim_hash)
                if claim is None:
                    continue
                reservation = await budget.reserve(
                    "falsifier",
                    spec.estimated_cost,
                    known_zero_cost=spec.estimated_cost == 0.0,
                )
                if reservation is None:
                    continue
                execution = execute_claim_bound(
                    spec,
                    claim,
                    claim_context_by_identity.get(claim.identity_hash, {}),
                    evidence_projection_hashes=tuple(claim.evidence_refs),
                    selection_reason=bid.selection_reason,
                )
                await budget.reconcile(reservation, execution.cost)
                executions.append(execution)
                node_executions.append(execution.model_dump(mode="json"))
                ledger.append(
                    "falsifier_selected",
                    {
                        "spec_hash": spec.hash,
                        "target_claim_hashes": list(execution.target_claim_hashes),
                        "why": bid.selection_reason,
                    },
                )
                ledger.append("falsifier_executed", execution.model_dump(mode="json"))
            if not node_executions:
                return {"budget_exhausted": True}
            return {"executions": node_executions}
        if node.kind == NodeKind.CHALLENGE:
            owner_to_node = {owner: node_id for node_id, owner in claim_owner_by_node.items()}
            if len(owner_to_node) < 2:
                return {"opened": 0}
            fps = sorted(owner_to_node)
            edge_candidates: list[CommunicationCandidate] = []
            for index, left_fp in enumerate(fps):
                for right_fp in fps[index + 1 :]:
                    left = claims_by_node[owner_to_node[left_fp]]
                    right = claims_by_node[owner_to_node[right_fp]]
                    disagreement = abs(left.probability - right.probability) + (0.25 if left.statement != right.statement else 0.0)
                    if disagreement < 0.10 and plan.name == MorphologyName.SPARSE_GRAPH:
                        continue
                    proximity = semantic_proximity(
                        SemanticSignature(left.statement, domain=left.domain, claim_type=left.claim_type, evidence_clusters=tuple(left.evidence_refs)),
                        SemanticSignature(right.statement, domain=right.domain, claim_type=right.claim_type, evidence_clusters=tuple(right.evidence_refs)),
                    )
                    edge_candidates.append(
                        CommunicationCandidate(
                            challenger=left_fp,
                            target=right_fp,
                            residual_disagreement=disagreement,
                            verified_reliability=0.5,
                            task_relevance=1.0,
                            capability_complementarity=1.0,
                            correlation=0.0,
                            semantic_proximity=proximity.score,
                            expected_information_gain=max(0.2, disagreement),
                            estimated_cost=float(provider_estimate or 0.0),
                        )
                    )
            chosen = host.services.communication.select(edge_candidates, k=1 if plan.name == MorphologyName.PAIRED_VERIFY else 2)
            for edge in chosen:
                target_node = owner_to_node[edge.target]
                target = claims_by_node[target_node]
                identity_before = target.identity_hash
                revision_before = target.revision_hash
                request_row = ChallengeRequest(
                    challenger_fingerprint=edge.challenger,
                    target_fingerprint=edge.target,
                    target_claim_hash=target.identity_hash,
                    target_statement_summary=target.statement[:500],
                    evidence_refs=list(target.evidence_refs),
                    falsifier_observations=[row.model_dump(mode="json") for row in executions if target.identity_hash in row.target_claim_hashes],
                    challenge_reason=f"residual uncertainty score={edge.score:.4f}",
                    round=1,
                )
                reservation = await budget.reserve("challenge", provider_estimate, known_zero_cost=host.provider.capabilities.known_zero_cost)
                if reservation is None:
                    continue
                response = await host.provider.challenge_async(request_row)
                await budget.reconcile(reservation, response.cost)
                provider_call_count += 1
                revised = target.model_copy(update={"probability": response.revised_probability, "status": response.revised_status})
                assert revised.identity_hash == identity_before
                claims_by_node[target_node] = revised
                comm = {
                    "round": 1,
                    "source_fp": edge.challenger,
                    "target_fp": edge.target,
                    "target_node_id": target_node,
                    "target_claim_hash": identity_before,
                    "revision_before_hash": revision_before,
                    "revision_after_hash": revised.revision_hash,
                    "reason": request_row.challenge_reason,
                    "score": edge.score,
                    "input_hash": request_row.hash,
                    "output_hash": response.hash,
                    "provider_call_id": response.provider_call_id,
                }
                communications.append(comm)
                ledger.append("communication_edge_opened", comm)
            return {"opened": len(communications)}
        if node.kind == NodeKind.JOIN:
            if node.group and node.group.startswith("subgroup:"):
                visible = {parent: claims_by_node[parent].identity_hash for parent in node.prerequisites if parent in claims_by_node}
                subgroup_payload: dict[str, Any] = {
                    "claims": visible,
                    "subtask_hashes": [subtask_assignment[parent].hash for parent in node.prerequisites if parent in subtask_assignment],
                }
                subgroup_results[node.group] = subgroup_payload
                return subgroup_payload
            return {
                "claims": {key: claim.identity_hash for key, claim in claims_by_node.items()},
                "executions": [row.execution_snapshot_hash for row in executions],
                "communications": len(communications),
            }
        if node.kind == NodeKind.SYNTHESIS:
            claim_rows: list[tuple[str, Claim, float]] = []
            for node_id, claim in sorted(claims_by_node.items()):
                fp = claim_owner_by_node[node_id]
                member = selected_by_fp[fp]
                subtask = subtask_assignment.get(node_id)
                relevant_caps = list(subtask.required_capabilities) if subtask is not None else [cap for cap in profile.required_capabilities if cap in member.capabilities]
                authority = sum(member.capability_calibration_scores.get(cap, member.calibration_score) for cap in relevant_caps) / max(1, len(relevant_caps))
                claim_rows.append((fp, claim, authority))
            required_hashes = {row.hash for row in subtasks} if plan.name == MorphologyName.HIERARCHICAL_FANOUT_FANIN else set()
            hierarchy_complete = plan.name != MorphologyName.HIERARCHICAL_FANOUT_FANIN or (
                required_hashes <= executed_subtask_hashes and not plan.compiler_rationale.get("unresolved_subtasks")
            )
            decision = synthesize_swarm(
                claim_rows,
                executions,
                communications,
                budget=budget.snapshot(),
                coverage_complete=not bool(rationale.get("uncovered_capabilities")) and bool(evidence_bundle.items) and hierarchy_complete,
            )
            ledger.append("swarm_decision_synthesized", decision.model_dump(mode="json") | {"decision_hash": decision.hash})
            return decision.model_dump(mode="json")
        return {"kind": node.kind.value}

    executor = DagExecutor(request.max_concurrency)
    dag_execution: DagExecution = await executor.execute(plan, handle, precompleted=precompleted)
    if decision is None:
        decision = synthesize_swarm([], executions, communications, budget=budget.snapshot(), coverage_complete=False)
    ordered_executions = sorted(executions, key=lambda row: (row.spec_hash, row.execution_snapshot_hash))
    execution_evidence_rows = [evidence_row(execution_evidence(row), run_id=run_id) for row in ordered_executions]
    decision = decision.model_copy(update={"decisive_refs": tuple(sorted(set(decision.decisive_refs) | {str(row["evidence_hash"]) for row in execution_evidence_rows}))})
    if decision.epistemic_status == "SUPPORTED":
        status: Literal["answered", "inconclusive", "failed"] = "answered"
        answer = decision.candidate_answer
    elif decision.epistemic_status == "FALSIFIED":
        status = "answered"
        answer = decision.candidate_answer
    else:
        status = "inconclusive"
        answer = f"INCONCLUSIVE: {decision.candidate_answer}" if decision.candidate_answer else "INCONCLUSIVE: verified evidence is insufficient."
    selected_status = {
        "SUPPORTED": ClaimStatus.SUPPORTED,
        "FALSIFIED": ClaimStatus.FALSIFIED,
        "INCONCLUSIVE": ClaimStatus.INCONCLUSIVE,
    }[decision.epistemic_status]
    final_claims: list[dict[str, Any]] = []
    for node_id, claim in sorted(claims_by_node.items()):
        fp = claim_owner_by_node[node_id]
        member = selected_by_fp[fp]
        subtask = subtask_assignment.get(node_id)
        relevant = list(subtask.required_capabilities) if subtask is not None else [cap for cap in profile.required_capabilities if cap in member.capabilities]
        immutable_claim_hash = claim.identity_hash
        persisted_status = selected_status if immutable_claim_hash in decision.selected_claim_hashes else claim.status
        final_claims.append(
            claim.model_dump(mode="json")
            | {
                "status": persisted_status.value,
                "claim_hash": immutable_claim_hash,
                "claim_identity_hash": immutable_claim_hash,
                "claim_revision_hash": claim.revision_hash,
                "provider_trace_id": claim_trace_ids.get(node_id),
                "contributor_node_id": node_id,
                "contributor_fingerprint": fp,
                "contributor_capabilities": relevant,
                "contributor_test_families": [f"{cap}_verified_task" for cap in relevant],
                "subtask_hash": None if subtask is None else subtask.hash,
            }
        )
    falsifier_rows = []
    for execution in ordered_executions:
        spec = spec_by_hash[execution.spec_hash]
        falsifier_rows.append(execution.model_dump(mode="json") | {"id": spec.id, "primitive": spec.primitive, "persistent_reuse": spec.hash in persistent_falsifiers_reused})
    ledger.append("final_verified", {"status": decision.epistemic_status, "decision_hash": decision.hash, "confidence": decision.confidence})
    task_ledger = TaskLedger(
        task=request.task,
        domain=domain,
        budget_usd=request.budget_usd,
        constraints={"max_agents": request.max_agents, "max_concurrency": request.max_concurrency, "depth": request.depth, "swarm_core": "ORDER-007"},
        plan=[node.kind.value for node in plan.nodes],
    )
    ledger.append("run_completed", {"status": status, "plan_hash": plan.plan_hash, "decision_hash": decision.hash})
    replay = verify_replay(ledger.events, ledger.head)
    metrics = dag_execution.metrics.as_dict()
    coalition = {
        "members": [member.fingerprint for member in selected],
        "names": [member.name for member in selected],
        "topology": plan.name.value,
        "morphology": plan.name.value,
        "rationale": rationale,
        "plan_hash": plan.plan_hash,
        "subtask_assignments": plan.compiler_rationale.get("subtask_assignments", {}),
    }
    required_subtask_hashes = {row.hash for row in subtasks} if plan.name == MorphologyName.HIERARCHICAL_FANOUT_FANIN else set()
    unresolved_subtask_hashes = sorted(required_subtask_hashes - executed_subtask_hashes | set(plan.compiler_rationale.get("unresolved_subtasks", [])))
    hierarchy_execution = {
        "required_subtasks": sorted(required_subtask_hashes),
        "assigned_subtasks": sorted(set(plan.compiler_rationale.get("subtask_assignments", {}).values())),
        "executed_subtasks": sorted(executed_subtask_hashes),
        "unresolved_subtasks": unresolved_subtask_hashes,
        "subgroup_results": subgroup_results,
        "complete": not unresolved_subtask_hashes if plan.name == MorphologyName.HIERARCHICAL_FANOUT_FANIN else True,
    }
    all_evidence_rows = evidence_bundle.persisted_rows() + execution_evidence_rows
    result = {
        "run_id": run_id,
        "status": status,
        "answer": answer,
        "confidence": decision.confidence,
        "final_claims": final_claims,
        "disagreements": list(decision.unresolved_disagreements),
        "falsifiers": falsifier_rows,
        "evidence_provenance": {
            "scenario": scenario,
            "source_mode": request.source_mode,
            "provider_input_evidence_hashes": sorted(evidence_bundle.hashes),
            "falsifier_execution_evidence_hashes": sorted(str(row["evidence_hash"]) for row in execution_evidence_rows),
            "provider": host.provider.capabilities.__dict__,
            "provider_usages": provider_usages,
            "pricing_preflight": pricing_preflight,
            "claim_aware_market": {"selected": [asdict(row) for row in market_selected or []], "candidates": [asdict(row) for row in market_all]},
            "auditions": audition_records,
            "swarm_decision": decision.model_dump(mode="json") | {"decision_hash": decision.hash},
            "evidence_hashes": [row["evidence_hash"] for row in all_evidence_rows],
        },
        "coalition": coalition,
        "budget": budget.snapshot(),
        "ledger_head": ledger.head,
        "memory_changes": [],
        "germinal_changes": [],
        "replay_verified": bool(replay["verified"]),
        "event_types": [event.event_type for event in ledger.events],
        "plugin_hashes": host.plugin_hashes,
        "plan_hash": plan.plan_hash,
        "morphology": plan.name.value,
        "provider_call_count": provider_call_count,
        "challenge_edge_count": len(communications),
        "concurrency_summary": {
            "peak_concurrency": metrics["peak_concurrency"],
            "parallel_speedup_estimate": metrics["parallel_speedup_estimate"],
            "parallel_efficiency": metrics["parallel_efficiency"],
            "avoidable_serialization_count": metrics["avoidable_serialization_count"],
            "subtask_finish_rate": metrics["subtask_finish_rate"],
        },
        "critical_path_summary": {
            "work_steps": metrics["work_steps"],
            "critical_steps": metrics["critical_steps"],
            "critical_path_ms": metrics["critical_path_ms"],
            "observed_wall_ms": metrics["observed_wall_ms"],
            "serial_work_ms": metrics["serial_work_ms"],
        },
        "persistent_memory_reused": sorted(persistent_memory_reused),
        "persistent_falsifiers_reused": sorted(set(persistent_falsifiers_reused)),
        "lineage_exclusions": {key: sorted(set(value)) for key, value in lineage_exclusions.items()},
        "swarm_decision": decision.model_dump(mode="json") | {"decision_hash": decision.hash},
        "subtasks": [row.model_dump(mode="json") | {"subtask_hash": row.hash} for row in subtasks],
        "threat_profile": profile.model_dump(mode="json"),
        "hierarchy_execution": hierarchy_execution,
    }
    host.repository.save_run_bundle(
        run_id=run_id,
        task_hash=task_hash,
        config_hash=config_hash,
        status=status,
        ledger_head=ledger.head,
        result=result,
        events=ledger.events,
        task_ledger=task_ledger.model_dump(mode="json"),
        coalition=coalition,
        plan_hash=plan.plan_hash,
        plan=plan.as_dict(),
        communications=communications,
        claims=final_claims,
        evidence=all_evidence_rows,
        executions=ordered_executions,
    )
    return result
