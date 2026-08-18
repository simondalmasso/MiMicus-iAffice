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
_SPEC_FOR = {"numeric": "F1", "freshness": "F2", "independence": "F3", "source": "F3", "entailment": "F4", "counterexample": "F5"}


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
    agent_nodes: list[DagNode] = []
    for index, member in enumerate(selected):
        subtask = subtasks[index % len(subtasks)] if subtasks else None
        group = f"subgroup-{index % 2}" if name == MorphologyName.HIERARCHICAL_FANOUT_FANIN else ("paired" if name == MorphologyName.PAIRED_VERIFY else "fanout")
        node = DagNode(
            _core_node_id(NodeKind.AGENT_TASK, index, member.fingerprint),
            NodeKind.AGENT_TASK,
            parent_ids,
            identity=member.fingerprint,
            input_hash=subtask.hash if subtask is not None else sha256_obj({"task": task_hash, "agent": member.fingerprint}),
            group=group,
        )
        if subtask is not None:
            assignment[node.node_id] = subtask
        nodes.append(node)
        agent_nodes.append(node)
        for parent in parent_ids:
            edges.append(DagEdge(parent, node.node_id, "subtask_fanout" if subtask else "worker_fanout", group))
    post_first_pass: list[str]
    subgroup_joins: list[DagNode] = []
    if name == MorphologyName.HIERARCHICAL_FANOUT_FANIN:
        for group_index in (0, 1):
            members = [node for index, node in enumerate(agent_nodes) if index % 2 == group_index]
            if not members:
                continue
            join = DagNode(
                _core_node_id(NodeKind.JOIN, group_index + 1, f"subgroup-{group_index}"),
                NodeKind.JOIN,
                tuple(node.node_id for node in members),
                input_hash=sha256_obj([node.input_hash for node in members]),
                group=f"subgroup-{group_index}-fanin",
            )
            nodes.append(join)
            subgroup_joins.append(join)
            for member_node in members:
                edges.append(DagEdge(member_node.node_id, join.node_id, "nested_subtask_fanin", join.group))
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
            "swarm_core": "ORDER-006",
            "selected_agents": count,
            "required_capabilities": list(caps),
            "subtask_hashes": [row.hash for row in subtasks],
            "subtask_assignments": {node_id: row.hash for node_id, row in assignment.items()},
            "claim_aware_market_after_first_pass": True,
            "max_concurrency": max_concurrency,
        },
    )
    plan.validate()
    return plan, assignment


def _blend_verified_authority(host: Any, fingerprint: str, domain: str, capability: str, canary_trust: float) -> float:
    verified = host.calibration.get_capability(fingerprint, domain, capability, f"{capability}_verified_task")
    if verified.attempts == 0:
        return canary_trust
    weight = min(0.75, verified.attempts / (verified.attempts + 3.0))
    return (1.0 - weight) * canary_trust + weight * verified.trust


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
    ledger.append("run_started", {"task_hash": task_hash, "config_hash": config_hash, "plugin_hashes": host.plugin_hashes, "swarm_core": "ORDER-006"})
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
    spec_keys = list(dict.fromkeys(_SPEC_FOR[cap] for cap in profile.required_capabilities if cap in _SPEC_FOR))
    base_specs = [builtins[key] for key in spec_keys]
    promoted = host.repository.promoted_falsifiers(domain)
    promoted_by_primitive = {spec.primitive: spec for spec in promoted}
    candidate_specs = [promoted_by_primitive.get(spec.primitive, spec) for spec in base_specs]
    persistent_falsifiers_reused = [spec.hash for spec in candidate_specs if spec.hash in {row.hash for row in promoted}]
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

    budget = BudgetLedger(request.budget_usd)
    provider_estimate = host.provider.capabilities.estimated_max_cost_per_call
    if provider_estimate is None and host.provider.capabilities.known_zero_cost:
        provider_estimate = 0.0
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
        affordable = int((request.budget_usd + 1e-12) // provider_estimate)
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
    claims_by_fp: dict[str, Claim] = {}
    claim_trace_ids: dict[str, str | None] = {}
    provider_usages: list[dict[str, Any]] = []
    executions: list[FalsifierExecution] = []
    communications: list[dict[str, Any]] = []
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

    async def ensure_market() -> list[ClaimFalsifierBid]:
        nonlocal market_selected, market_all
        async with market_lock:
            if market_selected is not None:
                return market_selected
            projected = float(provider_estimate or 0.0) * len(selected)
            market_budget = max(0.0, request.budget_usd - min(request.budget_usd, projected))
            market_selected, market_all = FalsifierMarket().select_for_claims(
                candidate_specs,
                [claims_by_fp[key] for key in sorted(claims_by_fp)],
                evidence=evidence_context,
                budget_usd=market_budget,
                max_tests={"fast": 1, "normal": 3, "deep": 5}[request.depth],
                evidence_quality=1.0 if evidence_bundle.items else 0.0,
            )
            ledger.append(
                "falsifier_market_scored",
                {
                    "phase": "after_sealed_first_pass",
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
            sealed = str(uuid5(NAMESPACE_URL, f"{run_id}:{member.fingerprint}:{node.input_hash}:sealed"))
            provider_request = ProviderRequest(
                task_payload,
                domain,
                member.name,
                sealed,
                fixture,
                tuple(injected_by_agent.get(member.fingerprint, [])),
                evidence_bundle.provider_payload(),
            )
            try:
                response = await host.provider.generate_request_async(provider_request)
            except BaseException:
                await budget.release(reservation, reason="provider failure/cancellation")
                raise
            reconciliation = await budget.reconcile(reservation, response.cost)
            provider_call_count += 1
            allowed_refs = set(evidence_bundle.hashes)
            claimed_refs = list(dict.fromkeys(response.claim.evidence_refs))
            validated_refs = [ref for ref in claimed_refs if ref in allowed_refs]
            rejected_refs = [ref for ref in claimed_refs if ref not in allowed_refs]
            claim = response.claim.model_copy(update={"evidence_refs": validated_refs})
            claims_by_fp[member.fingerprint] = claim
            claim_trace_ids[member.fingerprint] = response.trace_id
            provider_usages.append(
                {
                    "fingerprint": member.fingerprint,
                    "trace_id": response.trace_id,
                    "usage": dict(response.usage)
                    | {
                        "evidence_hashes_supplied": sorted(allowed_refs),
                        "evidence_refs_claimed": claimed_refs,
                        "evidence_refs_validated": validated_refs,
                        "evidence_refs_rejected": rejected_refs,
                        "subtask_hash": None if subtask is None else subtask.hash,
                    },
                    "budget": reconciliation,
                }
            )
            if rejected_refs:
                ledger.append(
                    "evidence_ref_rejected",
                    {"fingerprint": member.fingerprint, "rejected_refs": rejected_refs, "allowed_refs": sorted(allowed_refs)},
                )
            ledger.append(
                "claim_proposed",
                {
                    "claim_hash": claim.hash,
                    "fingerprint": member.fingerprint,
                    "probability": claim.probability,
                    "provider_trace_id": response.trace_id,
                    "evidence_refs": validated_refs,
                    "subtask_hash": None if subtask is None else subtask.hash,
                    "provider_task_hash": sha256_obj(task_payload),
                },
            )
            return {"claim": claim.model_dump(mode="json"), "subtask_hash": None if subtask is None else subtask.hash}
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
            reservation = await budget.reserve("falsifier", spec.estimated_cost, known_zero_cost=spec.estimated_cost == 0.0)
            if reservation is None:
                return {"budget_exhausted": True}
            raw = host.services.falsifiers.run(spec, evidence_context)
            reason = "; ".join(sorted({bid.selection_reason for bid in relevant}))
            execution = raw.model_copy(update={"target_claim_hashes": tuple(sorted({bid.target_claim_hash for bid in relevant})), "selection_reason": reason})
            await budget.reconcile(reservation, execution.cost)
            executions.append(execution)
            ledger.append("falsifier_selected", {"spec_hash": spec.hash, "target_claim_hashes": list(execution.target_claim_hashes), "why": reason})
            ledger.append("falsifier_executed", execution.model_dump(mode="json"))
            return execution.model_dump(mode="json")
        if node.kind == NodeKind.CHALLENGE:
            if len(claims_by_fp) < 2:
                return {"opened": 0}
            fps = sorted(claims_by_fp)
            edge_candidates: list[CommunicationCandidate] = []
            for index, left_fp in enumerate(fps):
                for right_fp in fps[index + 1 :]:
                    left, right = claims_by_fp[left_fp], claims_by_fp[right_fp]
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
                target = claims_by_fp[edge.target]
                request_row = ChallengeRequest(
                    challenger_fingerprint=edge.challenger,
                    target_fingerprint=edge.target,
                    target_claim_hash=target.hash,
                    target_statement_summary=target.statement[:500],
                    evidence_refs=list(target.evidence_refs),
                    falsifier_observations=[row.model_dump(mode="json") for row in executions if target.hash in row.target_claim_hashes],
                    challenge_reason=f"residual uncertainty score={edge.score:.4f}",
                    round=1,
                )
                reservation = await budget.reserve("challenge", provider_estimate, known_zero_cost=host.provider.capabilities.known_zero_cost)
                if reservation is None:
                    continue
                response = await host.provider.challenge_async(request_row)
                await budget.reconcile(reservation, response.cost)
                provider_call_count += 1
                claims_by_fp[edge.target] = target.model_copy(update={"probability": response.revised_probability, "status": response.revised_status})
                comm = {
                    "round": 1,
                    "source_fp": edge.challenger,
                    "target_fp": edge.target,
                    "target_claim_hash": target.hash,
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
            group_claims = {fp: claim.hash for fp, claim in claims_by_fp.items() if not node.group or not node.group.startswith("subgroup-") or selected_by_fp.get(fp) is not None}
            return {"claims": group_claims, "executions": [row.execution_snapshot_hash for row in executions], "communications": len(communications)}
        if node.kind == NodeKind.SYNTHESIS:
            claim_rows: list[tuple[str, Claim, float]] = []
            for fp, claim in sorted(claims_by_fp.items()):
                member = selected_by_fp[fp]
                relevant_caps = [cap for cap in profile.required_capabilities if cap in member.capabilities]
                authority = sum(member.capability_calibration_scores.get(cap, member.calibration_score) for cap in relevant_caps) / max(1, len(relevant_caps))
                claim_rows.append((fp, claim, authority))
            decision = synthesize_swarm(
                claim_rows,
                executions,
                communications,
                budget=budget.snapshot(),
                coverage_complete=not bool(rationale.get("uncovered_capabilities")) and bool(evidence_bundle.items),
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
    for fp, claim in sorted(claims_by_fp.items()):
        member = selected_by_fp[fp]
        relevant = [cap for cap in profile.required_capabilities if cap in member.capabilities]
        immutable_claim_hash = claim.hash
        persisted_status = selected_status if immutable_claim_hash in decision.selected_claim_hashes else claim.status
        final_claims.append(
            claim.model_dump(mode="json")
            | {
                "status": persisted_status.value,
                "claim_hash": immutable_claim_hash,
                "provider_trace_id": claim_trace_ids.get(fp),
                "contributor_fingerprint": fp,
                "contributor_capabilities": relevant,
                "contributor_test_families": [f"{cap}_verified_task" for cap in relevant],
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
        constraints={"max_agents": request.max_agents, "max_concurrency": request.max_concurrency, "depth": request.depth, "swarm_core": "ORDER-006"},
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
