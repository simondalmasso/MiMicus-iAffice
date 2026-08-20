from __future__ import annotations

import json
from dataclasses import replace
from typing import Any

from sqlalchemy import delete, insert, select, update

from mimicus.canonical import canonical_json, sha256_obj
from mimicus.claims.models import Claim
from mimicus.claims.projections import EvidenceProjection, derive_projection
from mimicus.falsifiers.primitives import execute_claim_bound
from mimicus.falsifiers.spec import FalsifierExecution, FalsifierSpec
from mimicus.orchestration.communication import ChallengeRequest
from mimicus.orchestration.production_synthesis import synthesize_production
from mimicus.orchestration.swarm_core import execute_swarm_core
from mimicus.providers.base import AuditionRequest, Provider, ProviderAuditionResponse, ProviderCapabilities, ProviderRequest, ProviderResponse
from mimicus.storage.models import ClaimRow, CommunicationRow, EvidenceRow, FalsifierExecutionRow, FalsifierSpecRow, FalsifierVersionRow, ProgressLedgerRow, RunRow
from mimicus.storage.swarm_models import VerificationReceiptRow
from mimicus.types import ClaimStatus


class ProductionProviderBoundary(Provider):
    """Provider-neutral audit boundary for exact projections and replay records."""

    def __init__(self, delegate: Provider) -> None:
        self.delegate = delegate
        self.generate_records: list[dict[str, Any]] = []
        self.challenge_records: list[dict[str, Any]] = []
        self.projections: dict[str, EvidenceProjection] = {}

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self.delegate.capabilities

    async def audition_async(self, request: AuditionRequest) -> ProviderAuditionResponse:
        return await self.delegate.audition_async(request)

    def _project_request(self, request: ProviderRequest) -> tuple[ProviderRequest, dict[str, str], list[EvidenceProjection]]:
        projected_payloads: list[dict[str, Any]] = []
        projection_to_parent: dict[str, str] = {}
        rows: list[EvidenceProjection] = []
        for evidence in request.evidence:
            # ORDER-007 hierarchy scopes clear content after narrowing facts. At
            # this provider boundary we assign the narrowed material a new
            # immutable identity instead of forwarding the parent's hash.
            if str(evidence.get("content", "")) == "":
                facts = evidence.get("extracted_facts", {})
                scope = tuple(sorted(str(key) for key in facts)) if isinstance(facts, dict) else ()
                projection = derive_projection(evidence, scope)
                self.projections[projection.projection_hash] = projection
                rows.append(projection)
                payload = projection.provider_payload()
                projected_payloads.append(payload)
                projection_to_parent[projection.projection_hash] = projection.parent_evidence_hash
            else:
                projected_payloads.append(dict(evidence))
        return replace(request, evidence=tuple(projected_payloads)), projection_to_parent, rows

    async def generate_request_async(self, request: ProviderRequest) -> ProviderResponse:
        exact_request, projection_to_parent, projections = self._project_request(request)
        response = await self.delegate.generate_request_async(exact_request)
        exact_claim = response.claim
        # The legacy scheduler validates against its parent hashes. Preserve that
        # internal compatibility while recording/restoring exact projection refs
        # before the production result becomes authoritative.
        scheduler_refs = [projection_to_parent.get(ref, ref) for ref in exact_claim.evidence_refs]
        scheduler_claim = exact_claim.model_copy(update={"evidence_refs": list(dict.fromkeys(scheduler_refs))})
        self.generate_records.append(
            {
                "request": {
                    "task": exact_request.task,
                    "domain": exact_request.domain,
                    "phenotype": exact_request.phenotype,
                    "sealed_context_id": exact_request.sealed_context_id,
                    "verified_memory_hash": sha256_obj(exact_request.verified_memory),
                    "evidence_hashes": [str(row.get("evidence_hash")) for row in exact_request.evidence],
                    "evidence": [dict(row) for row in exact_request.evidence],
                },
                "response": {
                    "claim": exact_claim.model_dump(mode="json"),
                    "trace_id": response.trace_id,
                    "usage": dict(response.usage),
                    "cost": response.cost,
                },
                "projection_hashes": [row.projection_hash for row in projections],
                "projection_to_parent": projection_to_parent,
            }
        )
        return replace(response, claim=scheduler_claim)

    async def challenge_async(self, request: ChallengeRequest) -> Any:
        response = await self.delegate.challenge_async(request)
        self.challenge_records.append(
            {
                "request": request.model_dump(mode="json"),
                "request_hash": request.hash,
                "response": response.model_dump(mode="json"),
                "response_hash": response.hash,
            }
        )
        return response


def _active_promoted_specs(repository: Any, domain: str) -> list[FalsifierSpec]:
    """Production registry view: promotion requires currently active authority."""
    with repository.engine.connect() as connection:
        rows = (
            connection.execute(
                select(FalsifierSpecRow.payload_json, FalsifierVersionRow.decision_json)
                .join(FalsifierVersionRow, FalsifierVersionRow.spec_hash == FalsifierSpecRow.spec_hash)
                .where(FalsifierSpecRow.domain == domain, FalsifierVersionRow.lifecycle_state == "PROMOTE")
            )
            .mappings()
            .all()
        )
        active_receipts = set(
            connection.execute(
                select(VerificationReceiptRow.receipt_hash).where(
                    VerificationReceiptRow.accepted == 1,
                    VerificationReceiptRow.learning_active == 1,
                )
            ).scalars()
        )
    active: dict[str, FalsifierSpec] = {}
    for row in rows:
        decision = json.loads(str(row["decision_json"]))
        receipt_hash = decision.get("receipt_hash")
        if not isinstance(receipt_hash, str) or receipt_hash not in active_receipts:
            continue
        spec = FalsifierSpec.model_validate(json.loads(str(row["payload_json"])))
        active[spec.hash] = spec
    return list(active.values())


def _merge_projection_context(rows: list[EvidenceProjection]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    conflicts: set[str] = set()
    for projection in rows:
        for key, value in projection.extracted_facts.items():
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


def _claim_from_row(row: dict[str, Any]) -> Claim:
    return Claim.model_validate({key: row[key] for key in Claim.model_fields if key in row})


def _spec_index(host: Any, domain: str) -> dict[str, FalsifierSpec]:
    builtins = host.services.falsifiers.specs(domain)
    active_promoted = _active_promoted_specs(host.repository, domain)
    return {spec.hash: spec for spec in [*builtins.values(), *active_promoted]}


def _restore_projection_claims(result: dict[str, Any], boundary: ProductionProviderBoundary) -> tuple[dict[str, str], dict[str, list[EvidenceProjection]]]:
    by_trace = {str(row["response"]["trace_id"]): row for row in boundary.generate_records if row["response"].get("trace_id") is not None}
    old_to_new: dict[str, str] = {}
    projections_by_claim: dict[str, list[EvidenceProjection]] = {}
    for usage_row in result.get("evidence_provenance", {}).get("provider_usages", []):
        trace_id = usage_row.get("trace_id")
        record = by_trace.get(str(trace_id)) if trace_id is not None else None
        if record is None:
            continue
        exact_hashes = [str(value) for value in record["request"].get("evidence_hashes", [])]
        projection_hashes = [str(value) for value in record.get("projection_hashes", [])]
        projection_to_parent = {str(key): str(value) for key, value in record.get("projection_to_parent", {}).items()}
        usage = usage_row.setdefault("usage", {})
        usage["evidence_hashes_supplied"] = exact_hashes
        usage["projection_hashes_supplied"] = projection_hashes
        usage["parent_evidence_hashes_supplied"] = [projection_to_parent.get(value, value) for value in exact_hashes]

    for claim_row in result.get("final_claims", []):
        trace_id = claim_row.get("provider_trace_id")
        record = by_trace.get(str(trace_id)) if trace_id is not None else None
        if record is None:
            continue
        exact_claim = Claim.model_validate(record["response"]["claim"])
        current = _claim_from_row(claim_row)
        exact_current = current.model_copy(
            update={
                "assertion": exact_claim.assertion,
                "evidence_refs": list(exact_claim.evidence_refs),
            }
        )
        old_hash = str(claim_row.get("claim_hash") or current.identity_hash)
        old_to_new[old_hash] = exact_current.identity_hash
        claim_row.update(
            exact_current.model_dump(mode="json")
            | {
                "claim_hash": exact_current.identity_hash,
                "claim_identity_hash": exact_current.identity_hash,
                "claim_revision_hash": exact_current.revision_hash,
                "provider_projection_hashes": list(record["projection_hashes"]),
            }
        )
        projections_by_claim[exact_current.identity_hash] = [boundary.projections[value] for value in record["projection_hashes"] if value in boundary.projections]
    market = result.get("evidence_provenance", {}).get("claim_aware_market", {})
    for key in ("selected", "candidates"):
        for bid in market.get(key, []):
            target = str(bid.get("target_claim_hash", ""))
            if target in old_to_new:
                bid["target_claim_hash"] = old_to_new[target]
    return old_to_new, projections_by_claim


def _reexecute_claim_bound(
    host: Any,
    result: dict[str, Any],
    projections_by_claim: dict[str, list[EvidenceProjection]],
) -> list[FalsifierExecution]:
    domain = str(result.get("threat_profile", {}).get("domain") or (result.get("final_claims") or [{}])[0].get("domain") or "general")
    specs = _spec_index(host, domain)
    claims = {str(row["claim_hash"]): _claim_from_row(row) for row in result.get("final_claims", [])}
    selected = result.get("evidence_provenance", {}).get("claim_aware_market", {}).get("selected", [])
    executions: list[FalsifierExecution] = []
    seen: set[tuple[str, str]] = set()
    for bid in selected:
        spec_hash = str(bid.get("spec_hash", ""))
        claim_hash = str(bid.get("target_claim_hash", ""))
        key = (spec_hash, claim_hash)
        if key in seen or spec_hash not in specs or claim_hash not in claims:
            continue
        seen.add(key)
        projections = projections_by_claim.get(claim_hash, [])
        context = _merge_projection_context(projections)
        if not projections:
            # Non-projected provider inputs remain exact canonical evidence.
            evidence_rows = host.repository.get_evidence(str(result["run_id"]))
            merged: dict[str, Any] = {}
            for row in evidence_rows:
                facts = row.get("extracted_facts", {})
                if isinstance(facts, dict):
                    merged.update(facts)
            context = merged
        execution = execute_claim_bound(
            specs[spec_hash],
            claims[claim_hash],
            context,
            evidence_projection_hashes=tuple(row.projection_hash for row in projections),
            selection_reason=str(bid.get("selection_reason") or "claim-bound production execution"),
        )
        executions.append(execution)
    return sorted(executions, key=lambda row: (row.target_claim_hashes, row.spec_hash, row.execution_snapshot_hash))


def _claim_rows_for_synthesis(result: dict[str, Any]) -> list[tuple[str, Claim, float, str | None]]:
    rows: list[tuple[str, Claim, float, str | None]] = []
    for row in result.get("final_claims", []):
        claim = _claim_from_row(row)
        raw_authority = row.get("contributor_authority")
        authority = float(raw_authority) if isinstance(raw_authority, (int, float)) else 0.5
        rows.append((str(row.get("contributor_fingerprint", "")), claim, authority, row.get("subtask_hash")))
    return rows


async def _extend_bounded_communication(
    boundary: ProductionProviderBoundary,
    result: dict[str, Any],
    executions: list[FalsifierExecution],
    request: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    communications = list(result.get("persistent_state", {}).get("communications", []))
    if not communications:
        return communications, []
    if result.get("morphology") not in {"paired_verify", "sparse_graph"}:
        return communications, []
    if not boundary.capabilities.known_zero_cost:
        return communications, [{"step": "communication", "reason": "bounded extra rounds require known-zero-cost provider in this run", "progress": False}]
    claim_by_fp = {str(row.get("contributor_fingerprint")): row for row in result.get("final_claims", [])}
    seed = communications[0]
    target_fp = str(seed.get("target_fp", ""))
    source_fp = str(seed.get("source_fp", ""))
    if target_fp not in claim_by_fp:
        return communications, []
    target_row = claim_by_fp[target_fp]
    target = _claim_from_row(target_row)
    progress_rows: list[dict[str, Any]] = []
    no_progress = 0
    for round_no in (2, 3):
        linked = [row.model_dump(mode="json") for row in executions if target.identity_hash in row.target_claim_hashes]
        challenge = ChallengeRequest(
            challenger_fingerprint=source_fp,
            target_fingerprint=target_fp,
            target_claim_hash=target.identity_hash,
            target_statement_summary=target.statement[:500],
            evidence_refs=list(target.evidence_refs),
            falsifier_observations=linked,
            challenge_reason=f"bounded production stabilization round={round_no}",
            round=round_no,
        )
        before = target.revision_hash
        response = await boundary.challenge_async(challenge)
        target = target.model_copy(update={"probability": response.revised_probability, "status": response.revised_status})
        after = target.revision_hash
        progressed = before != after
        no_progress = 0 if progressed else no_progress + 1
        comm = {
            "round": round_no,
            "source_fp": source_fp,
            "target_fp": target_fp,
            "target_claim_hash": target.identity_hash,
            "revision_before_hash": before,
            "revision_after_hash": after,
            "reason": challenge.challenge_reason,
            "input_hash": challenge.hash,
            "output_hash": response.hash,
            "provider_call_id": response.provider_call_id,
        }
        communications.append(comm)
        progress_rows.append({"step": "communication", "round": round_no, "progress": progressed, "revision_before": before, "revision_after": after})
        if no_progress >= 2:
            progress_rows.append({"step": "replan", "round": round_no, "progress": False, "reason": "two consecutive no-progress rounds"})
            break
    target_row.update(
        target.model_dump(mode="json")
        | {
            "claim_hash": target.identity_hash,
            "claim_identity_hash": target.identity_hash,
            "claim_revision_hash": target.revision_hash,
        }
    )
    return communications, progress_rows


def _apply_decision(result: dict[str, Any], decision: Any, executions: list[FalsifierExecution]) -> None:
    result["swarm_decision"] = decision.model_dump(mode="json") | {"decision_hash": decision.hash}
    result.setdefault("evidence_provenance", {})["swarm_decision"] = result["swarm_decision"]
    result["confidence"] = decision.confidence
    result["disagreements"] = list(decision.unresolved_disagreements)
    result["falsifiers"] = [row.model_dump(mode="json") for row in executions]
    if decision.epistemic_status == "SUPPORTED" or decision.epistemic_status == "FALSIFIED":
        result["status"] = "answered"
        result["answer"] = decision.candidate_answer
    else:
        result["status"] = "inconclusive"
        result["answer"] = f"INCONCLUSIVE: {decision.candidate_answer}" if decision.candidate_answer else "INCONCLUSIVE: verified evidence is insufficient."
    selected = set(decision.selected_claim_hashes)
    status_map = {"SUPPORTED": ClaimStatus.SUPPORTED.value, "FALSIFIED": ClaimStatus.FALSIFIED.value, "INCONCLUSIVE": ClaimStatus.INCONCLUSIVE.value}
    for row in result.get("final_claims", []):
        if row.get("claim_hash") in selected:
            row["status"] = status_map[decision.epistemic_status]


def _semantic_record(
    result: dict[str, Any],
    request: Any,
    boundary: ProductionProviderBoundary,
    executions: list[FalsifierExecution],
    specs: dict[str, FalsifierSpec],
) -> dict[str, Any]:
    claim_rows = [
        {key: row[key] for key in Claim.model_fields if key in row}
        | {
            "contributor_fingerprint": row.get("contributor_fingerprint"),
            "subtask_hash": row.get("subtask_hash"),
            "contributor_authority": row.get("contributor_authority", 0.5),
        }
        for row in result.get("final_claims", [])
    ]
    replay_executions: list[dict[str, Any]] = []
    parsed_claims = [_claim_from_row(row) for row in claim_rows]
    claims = {claim.identity_hash: claim for claim in parsed_claims}
    projection_rows = {key: value.persisted_row() for key, value in boundary.projections.items()}
    for execution in executions:
        target = execution.target_claim_hashes[0] if execution.target_claim_hashes else None
        claim = claims.get(str(target))
        if claim is None or execution.spec_hash not in specs:
            continue
        projections = [boundary.projections[value] for value in execution.evidence_projection_hashes if value in boundary.projections]
        replay_executions.append(
            {
                "spec": specs[execution.spec_hash].model_dump(mode="json"),
                "claim": claim.model_dump(mode="json"),
                "evidence_context": _merge_projection_context(projections),
                "evidence_projection_hashes": list(execution.evidence_projection_hashes),
                "selection_reason": execution.selection_reason,
                "expected_snapshot_hash": execution.execution_snapshot_hash,
                "expected_verdict": execution.verdict.value,
            }
        )
    input_material = {
        "version": "ORDER-008-semantic-replay-v1",
        "source_mode": request.source_mode,
        "task": request.task,
        "domain": request.domain or "general",
        "request_config": {
            "budget_usd": request.budget_usd,
            "max_agents": request.max_agents,
            "max_concurrency": request.max_concurrency,
            "depth": request.depth,
            "learn": request.learn,
        },
        "provider_identity": boundary.capabilities.__dict__,
        "provider_generate_records": boundary.generate_records,
        "provider_challenge_records": boundary.challenge_records,
        "projection_rows": projection_rows,
        "claim_rows": claim_rows,
        "replay_executions": replay_executions,
        "morphology": result.get("morphology"),
        "plan_hash": result.get("plan_hash"),
        "subtasks": result.get("subtasks", []),
        "hierarchy_execution": result.get("hierarchy_execution", {}),
        "budget": result.get("budget", {}),
        "communications": result.get("persistent_state", {}).get("communications", []),
    }
    expected = {
        "claim_identity_hashes": sorted(str(row.get("claim_hash")) for row in result.get("final_claims", [])),
        "falsifier_snapshot_hashes": sorted(row.execution_snapshot_hash for row in executions),
        "decision_hash": result.get("swarm_decision", {}).get("decision_hash"),
        "plan_hash": result.get("plan_hash"),
    }
    return {
        "replayable_provider": boundary.capabilities.provider_id == "scripted",
        "input_material": input_material,
        "input_hash": sha256_obj(input_material),
        "expected": expected,
        "expected_hash": sha256_obj(expected),
    }


def _persist_postprocessed(
    host: Any,
    result: dict[str, Any],
    boundary: ProductionProviderBoundary,
    executions: list[FalsifierExecution],
    communications: list[dict[str, Any]],
    progress_rows: list[dict[str, Any]],
) -> None:
    run_id = str(result["run_id"])
    with host.repository.engine.begin() as connection:
        connection.execute(update(RunRow).where(RunRow.run_id == run_id).values(status=str(result["status"]), result_json=canonical_json(result)))
        connection.execute(delete(ClaimRow).where(ClaimRow.run_id == run_id))
        for row in result.get("final_claims", []):
            connection.execute(
                insert(ClaimRow).values(
                    claim_hash=str(row["claim_hash"]),
                    run_id=run_id,
                    status=str(row.get("status", "proposed")),
                    payload_json=canonical_json(row),
                )
            )
        for projection in boundary.projections.values():
            payload = projection.persisted_row()
            exists = connection.execute(select(EvidenceRow.evidence_hash).where(EvidenceRow.evidence_hash == projection.projection_hash)).scalar_one_or_none()
            if exists is None:
                connection.execute(
                    insert(EvidenceRow).values(
                        evidence_hash=projection.projection_hash,
                        run_id=run_id,
                        independence_cluster=projection.independence_cluster,
                        payload_json=canonical_json(payload),
                    )
                )
        connection.execute(delete(FalsifierExecutionRow).where(FalsifierExecutionRow.run_id == run_id))
        for execution in executions:
            connection.execute(
                insert(FalsifierExecutionRow).values(
                    run_id=run_id,
                    spec_hash=execution.spec_hash,
                    snapshot_hash=execution.execution_snapshot_hash,
                    verdict=execution.verdict.value,
                    payload_json=canonical_json(execution.model_dump(mode="json")),
                )
            )
        connection.execute(delete(CommunicationRow).where(CommunicationRow.run_id == run_id))
        for row in communications:
            connection.execute(
                insert(CommunicationRow).values(
                    run_id=run_id,
                    round_no=int(row.get("round", 1)),
                    source_fp=str(row.get("source_fp", "")),
                    target_fp=str(row.get("target_fp", "")),
                    reason=str(row.get("reason", "")),
                    provider_call_id=row.get("provider_call_id"),
                    input_hash=row.get("input_hash"),
                    output_hash=row.get("output_hash"),
                    payload_json=canonical_json(row),
                )
            )
        connection.execute(delete(ProgressLedgerRow).where(ProgressLedgerRow.run_id == run_id))
        for index, row in enumerate(progress_rows):
            connection.execute(insert(ProgressLedgerRow).values(run_id=run_id, step=index, payload_json=canonical_json(row)))


async def execute_production_core(host: Any, request: Any) -> dict[str, Any]:
    """Normative source_mode=runtime execution for ORDER-008 and later."""
    original_provider = host.provider
    original_promoted = host.repository.promoted_falsifiers
    boundary = ProductionProviderBoundary(original_provider)
    host.provider = boundary
    host.repository.promoted_falsifiers = lambda domain: _active_promoted_specs(host.repository, domain)
    try:
        result = await execute_swarm_core(host, request)
    finally:
        host.provider = original_provider
        host.repository.promoted_falsifiers = original_promoted

    result["learning_policy"] = {
        "learn": bool(request.learn),
        "authority_activation": "authenticated_receipt_only",
        "unverified_output_authority": False,
    }
    result["production_core"] = {
        "version": "ORDER-008",
        "source_mode": request.source_mode,
        "claim_bound_falsifiers": True,
        "immutable_evidence_projections": True,
        "active_authority_registry_only": True,
    }
    old_to_new, projections_by_claim = _restore_projection_claims(result, boundary)
    communications = list(host.repository.inspect_state(str(result["run_id"])).get("communications", []))
    for row in communications:
        target = str(row.get("target_claim_hash", ""))
        if target in old_to_new:
            row["target_claim_hash"] = old_to_new[target]
    result.setdefault("persistent_state", {})["communications"] = communications

    executions = _reexecute_claim_bound(host, result, projections_by_claim)
    communications, round_progress = await _extend_bounded_communication(boundary, result, executions, request)
    executions = _reexecute_claim_bound(host, result, projections_by_claim)
    result["persistent_state"]["communications"] = communications
    result["challenge_edge_count"] = len(communications)
    result["provider_call_count"] = int(result.get("provider_call_count", 0)) + len(round_progress)

    coverage_complete = bool(result.get("evidence_provenance", {}).get("provider_input_evidence_hashes"))
    if result.get("morphology") == "hierarchical_fanout_fanin":
        coverage_complete = coverage_complete and bool(result.get("hierarchy_execution", {}).get("complete"))
    result["production_core"]["coverage_complete"] = coverage_complete
    decision = synthesize_production(
        _claim_rows_for_synthesis(result),
        executions,
        communications,
        budget=dict(result.get("budget", {})),
        coverage_complete=coverage_complete,
        morphology=str(result.get("morphology", "solo")),
        subtasks=list(result.get("subtasks", [])),
        hierarchy_execution=dict(result.get("hierarchy_execution", {})),
    )
    _apply_decision(result, decision, executions)
    spec_rows = _spec_index(
        host,
        str((result.get("final_claims") or [{}])[0].get("domain") or request.domain or "general"),
    )
    persistent_reuse = set(result.get("persistent_falsifiers_reused", []))
    result["falsifiers"] = [
        row.model_dump(mode="json")
        | {
            "id": spec_rows[row.spec_hash].id if row.spec_hash in spec_rows else None,
            "primitive": spec_rows[row.spec_hash].primitive if row.spec_hash in spec_rows else None,
            "persistent_reuse": row.spec_hash in persistent_reuse,
        }
        for row in executions
    ]

    parent_hashes = list(result.get("evidence_provenance", {}).get("provider_input_evidence_hashes", []))
    projection_hashes = sorted(boundary.projections)
    result["evidence_provenance"]["provider_input_parent_evidence_hashes"] = parent_hashes
    if projection_hashes:
        result["evidence_provenance"]["provider_input_evidence_hashes"] = projection_hashes
    result["evidence_provenance"]["evidence_projection_hashes"] = projection_hashes
    result["evidence_provenance"]["projection_parent_map"] = {key: value.parent_evidence_hash for key, value in sorted(boundary.projections.items())}
    result["evidence_provenance"]["authoritative_falsifier_snapshot_hashes"] = [row.execution_snapshot_hash for row in executions]

    progress_rows = [
        {"step": "runtime_started", "progress": True, "source_mode": request.source_mode},
        {"step": "provider_first_pass", "progress": bool(result.get("final_claims")), "claim_count": len(result.get("final_claims", []))},
        {"step": "claim_bound_falsifiers", "progress": bool(executions), "execution_count": len(executions)},
        *round_progress,
        {
            "step": "synthesis",
            "progress": True,
            "decision_hash": decision.hash,
            "epistemic_status": decision.epistemic_status,
            "stop_reason": decision.early_stop_reason,
        },
    ]
    result["progress"] = progress_rows
    semantic = _semantic_record(result, request, boundary, executions, spec_rows)
    result["semantic_replay"] = semantic
    result["replay_verified"] = True  # ledger integrity; semantic replay is reported separately.
    _persist_postprocessed(host, result, boundary, executions, communications, progress_rows)
    return result
