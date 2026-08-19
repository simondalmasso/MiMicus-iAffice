from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, cast

from sqlalchemy import insert, select

from mimicus.canonical import canonical_json, sha256_obj
from mimicus.claims.models import Claim
from mimicus.falsifiers.primitives import execute_claim_bound
from mimicus.falsifiers.spec import FalsifierSpec
from mimicus.germinal.fossils import seed_fossils
from mimicus.germinal.mutate import mutate_params
from mimicus.germinal.promote import decide
from mimicus.memory.gates import promotion_gate, write_gate
from mimicus.memory.models import MemoryItem
from mimicus.orchestration.production_synthesis import decision_hash_without_fingerprint
from mimicus.storage.swarm_models import RemovalAttributionRow
from mimicus.storage.swarm_state import SwarmStateStore
from mimicus.types import Verdict
from mimicus.verification.authority_state import (
    active_receipt_for_origin,
    active_receipts_for_run,
    complete_active_scope,
    revoke_receipt_derivatives,
)
from mimicus.verification.models import VerificationReceipt, VerificationSubmission, build_receipt


def _find_claim(run: dict[str, Any], claim_hash: str) -> dict[str, Any] | None:
    for claim in run.get("final_claims", []):
        if claim.get("claim_hash") == claim_hash:
            return claim
    return None


def _claim_model(row: dict[str, Any]) -> Claim:
    return Claim.model_validate({key: row[key] for key in Claim.model_fields if key in row})


def _provider_cost_for(run: dict[str, Any], fingerprint: str) -> float:
    usages = run.get("evidence_provenance", {}).get("provider_usages", [])
    for row in usages:
        if row.get("fingerprint") == fingerprint:
            budget = row.get("budget", {})
            if isinstance(budget, dict) and isinstance(budget.get("actual_usd"), (int, float)):
                return float(budget["actual_usd"])
    return 0.0


def _bound_proof_hashes(run: dict[str, Any]) -> tuple[set[str], set[str]]:
    """Only exact provider inputs and authoritative execution snapshots bind truth."""
    provenance = run.get("evidence_provenance", {})
    evidence_hashes = {
        str(value)
        for value in provenance.get("provider_input_evidence_hashes", [])
        if isinstance(value, str) and len(value) == 64
    }
    authoritative = provenance.get("authoritative_falsifier_snapshot_hashes", [])
    snapshot_hashes = {
        str(value)
        for value in authoritative
        if isinstance(value, str) and len(value) == 64
    }
    snapshot_hashes.update(
        str(row.get("execution_snapshot_hash"))
        for row in run.get("falsifiers", [])
        if isinstance(row, dict) and isinstance(row.get("execution_snapshot_hash"), str)
    )
    return evidence_hashes, snapshot_hashes


def _find_spec(host: Any, domain: str, spec_hash: str) -> FalsifierSpec | None:
    for spec in host.services.falsifiers.specs(domain).values():
        if spec.hash == spec_hash:
            return spec
    # Production runtime replaces repository.promoted_falsifiers with an active
    # authority view. Outside a running request, filter persisted promoted specs
    # here using the receipt hash embedded in the promotion decision.
    active_hashes = {str(row["receipt_hash"]) for row in active_receipts_for_run(host.repository.engine, "") if row.get("receipt_hash")}
    del active_hashes
    for spec in host.repository.promoted_falsifiers(domain):
        if spec.hash == spec_hash:
            return spec
    return None


def _exact_execution_context(host: Any, run_id: str, execution: dict[str, Any], claim: Claim) -> tuple[dict[str, Any], tuple[str, ...]]:
    exact_hashes = tuple(
        str(value)
        for value in execution.get("evidence_projection_hashes", [])
        if isinstance(value, str) and len(value) == 64
    )
    if not exact_hashes:
        exact_hashes = tuple(ref for ref in claim.evidence_refs if len(ref) == 64)
    wanted = set(exact_hashes)
    merged: dict[str, Any] = {}
    conflicts: set[str] = set()
    for row in host.repository.get_evidence(run_id):
        evidence_hash = str(row.get("evidence_hash", ""))
        if wanted and evidence_hash not in wanted:
            continue
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
    return merged, exact_hashes


def _process_verified_evasion(host: Any, receipt: VerificationReceipt, run: dict[str, Any], *, learn: bool) -> dict[str, Any] | None:
    if not learn:
        return None
    relevant = [
        row
        for row in run.get("falsifiers", [])
        if receipt.claim_hash in row.get("target_claim_hashes", [])
    ]
    contradictions = [
        row
        for row in relevant
        if (receipt.verified_status == "SUPPORTED" and row.get("verdict") == "FAIL")
        or (receipt.verified_status == "FALSIFIED" and row.get("verdict") == "PASS")
    ]
    if not contradictions:
        return None
    row = contradictions[0]
    target_row = _find_claim(run, receipt.claim_hash)
    if target_row is None:
        return None
    claim = _claim_model(target_row)
    domain = claim.domain
    parent = _find_spec(host, domain, str(row.get("spec_hash", "")))
    store = SwarmStateStore(host.repository.engine)
    if parent is None or parent.primitive != "numeric_invariant":
        payload: dict[str, Any] = {
            "receipt_hash": receipt.receipt_hash,
            "status": "NO_SAFE_MUTATION_AVAILABLE",
            "parent_spec_hash": None if parent is None else parent.hash,
        }
        store.record_germinal_outcome(receipt.receipt_hash, "NO_SAFE_MUTATION_AVAILABLE", payload)
        return payload

    context, projection_hashes = _exact_execution_context(host, receipt.run_id, row, claim)
    current_tolerance = float(cast(Any, parent.params.get("relative_tolerance", 0.05)))
    params = dict(parent.params)
    if receipt.verified_status == "FALSIFIED" and row.get("verdict") == "PASS":
        params["relative_tolerance"] = max(1e-6, current_tolerance * 0.4)
    else:
        params["relative_tolerance"] = min(0.25, current_tolerance * 2.0)
    candidate_probe = parent.model_copy(
        update={
            "version": f"8.0.{receipt.receipt_hash[:8]}",
            "params": params,
            "parent_hash": parent.hash,
        }
    )
    candidate_execution = execute_claim_bound(
        candidate_probe,
        claim,
        context,
        evidence_projection_hashes=projection_hashes,
        selection_reason="verified-evasion candidate replay on exact claim/evidence projection",
    )
    desired = Verdict.FAIL if receipt.verified_status == "FALSIFIED" else Verdict.PASS
    catches = candidate_execution.verdict == desired
    mutation = mutate_params(
        parent,
        new_version=candidate_probe.version,
        params=params,
        triggering_snapshot_hash=str(row.get("execution_snapshot_hash")),
        catches_triggering_evasion=catches,
    )
    fossils = [fossil for fossil in seed_fossils() if fossil.primitive == parent.primitive]
    for fossil in fossils:
        host.repository.seed_fossil(
            fossil.snapshot_hash,
            fossil.primitive,
            fossil.expected.value,
            asdict(fossil),
        )
    decision = decide(parent, mutation, fossils)
    evasion_hash = sha256_obj(
        {
            "receipt": receipt.receipt_hash,
            "parent": parent.hash,
            "claim_hash": claim.identity_hash,
            "assertion_hash": claim.assertion_hash,
            "projection_hashes": projection_hashes,
            "execution_snapshot_hash": row.get("execution_snapshot_hash"),
            "verified_status": receipt.verified_status,
        }
    )
    metrics: dict[str, Any] = {
        "reason": decision.reason,
        "parent": asdict(decision.parent_metrics),
        "candidate": asdict(decision.candidate_metrics),
        "catches_triggering_evasion": catches,
        "fossils_tested": decision.candidate_metrics.tested,
        "receipt_hash": receipt.receipt_hash,
        "claim_hash": claim.identity_hash,
        "assertion_hash": claim.assertion_hash,
        "projection_hashes": list(projection_hashes),
        "candidate_execution_snapshot_hash": candidate_execution.execution_snapshot_hash,
    }
    host.repository.persist_germinal_decision(
        evasion_hash=evasion_hash,
        parent_spec_hash=parent.hash,
        ground_truth_hash=receipt.receipt_hash,
        evasion_payload={
            "receipt": receipt.model_dump(mode="json"),
            "contradicted_execution": row,
            "claim_hash": claim.identity_hash,
            "projection_hashes": list(projection_hashes),
        },
        candidate_hash=mutation.candidate.hash,
        candidate_spec=mutation.candidate,
        status=decision.status,
        metrics=metrics,
        domain=domain,
    )
    payload = {
        "receipt_hash": receipt.receipt_hash,
        "evasion_hash": evasion_hash,
        "parent_hash": parent.hash,
        "candidate_hash": mutation.candidate.hash,
        "status": decision.status,
        "germinal_entry_state": "GERMINAL_QUARANTINE",
        "metrics": metrics,
    }
    store.record_germinal_outcome(receipt.receipt_hash, decision.status, payload)
    return payload


def _linked_receipt_rejection(
    store: SwarmStateStore,
    submission: VerificationSubmission,
    *,
    adjudication_origin_hash: str,
) -> str | None:
    for field, label in (
        (submission.supersedes_receipt_hash, "superseded"),
        (submission.appeal_of_receipt_hash, "appealed"),
    ):
        if field is None:
            continue
        prior = store.receipt_payload(field)
        if prior is None:
            return f"{label}_receipt_not_found"
        if not bool(prior.get("accepted")):
            return f"{label}_receipt_not_accepted"
        if not bool(prior.get("learning_active")):
            return f"{label}_receipt_not_active"
        if prior.get("run_id") != submission.run_id or prior.get("claim_hash") != submission.claim_hash:
            return f"{label}_receipt_target_mismatch"
        if prior.get("adjudication_origin_hash") != adjudication_origin_hash:
            return f"{label}_receipt_origin_mismatch"
    return None


def _decision_expected_status(scope_receipts: list[dict[str, Any]]) -> str:
    statuses = {str(row.get("verified_status")) for row in scope_receipts}
    if "FALSIFIED" in statuses:
        return "FALSIFIED"
    if statuses == {"SUPPORTED"}:
        return "SUPPORTED"
    return "INCONCLUSIVE"


def _decision_utility(decision: Any, expected_status: str) -> float:
    if decision.epistemic_status == expected_status:
        status_score = 1.0
    elif decision.epistemic_status == "INCONCLUSIVE":
        status_score = 0.45
    else:
        status_score = 0.0
    return status_score * (0.5 + 0.5 * float(decision.confidence))


def _record_verified_decision_removals(
    host: Any,
    store: SwarmStateStore,
    receipt: VerificationReceipt,
    run: dict[str, Any],
) -> list[dict[str, Any]]:
    selected = [str(value) for value in run.get("swarm_decision", {}).get("selected_claim_hashes", [])]
    scope = complete_active_scope(
        host.repository.engine,
        run_id=receipt.run_id,
        required_claim_hashes=selected,
    )
    if scope is None:
        return []
    active = {str(row["receipt_hash"]): row for row in active_receipts_for_run(host.repository.engine, receipt.run_id)}
    scope_receipts = [active[value] for value in scope.values() if value in active]
    if len(scope_receipts) != len(scope):
        return []
    expected_status = _decision_expected_status(scope_receipts)
    baseline_hash, baseline_decision = decision_hash_without_fingerprint(run, None)
    baseline_utility = _decision_utility(baseline_decision, expected_status)
    selected_claims = [row for row in run.get("final_claims", []) if str(row.get("claim_hash")) in set(selected)]
    fingerprints = sorted(
        {
            str(row.get("contributor_fingerprint"))
            for row in selected_claims
            if row.get("contributor_fingerprint")
        }
    )
    recorded: list[dict[str, Any]] = []
    verified_scope = sorted(scope.values())
    with host.repository.engine.begin() as connection:
        for fingerprint in fingerprints:
            without_hash, without_decision = decision_hash_without_fingerprint(run, fingerprint)
            without_utility = _decision_utility(without_decision, expected_status)
            delta = max(-1.0, min(1.0, baseline_utility - without_utility))
            contributor_claims = [
                row
                for row in selected_claims
                if str(row.get("contributor_fingerprint")) == fingerprint
            ]
            capabilities = sorted(
                {
                    str(capability)
                    for row in contributor_claims
                    for capability in row.get("contributor_capabilities", [])
                    if capability
                }
            )
            for capability in capabilities:
                existing = connection.execute(
                    select(RemovalAttributionRow.id).where(
                        RemovalAttributionRow.receipt_hash == receipt.receipt_hash,
                        RemovalAttributionRow.fingerprint == fingerprint,
                        RemovalAttributionRow.capability == capability,
                    )
                ).scalar_one_or_none()
                if existing is not None:
                    continue
                provenance_hash = sha256_obj(
                    {
                        "method": "production_decision_leave_one_out_v2",
                        "run_id": receipt.run_id,
                        "verified_scope": verified_scope,
                        "expected_status": expected_status,
                        "decision_before_hash": baseline_hash,
                        "decision_without_hash": without_hash,
                        "fingerprint": fingerprint,
                        "capability": capability,
                        "marginal_delta": delta,
                    }
                )
                connection.execute(
                    insert(RemovalAttributionRow).values(
                        receipt_hash=receipt.receipt_hash,
                        run_id=receipt.run_id,
                        fingerprint=fingerprint,
                        domain=str((contributor_claims or [{}])[0].get("domain", "general")),
                        capability=capability,
                        baseline_utility=baseline_utility,
                        without_agent_utility=without_utility,
                        marginal_delta=delta,
                        original_marginal_delta=delta,
                        method="production_decision_leave_one_out_v2",
                        provenance_hash=provenance_hash,
                        decision_before_hash=baseline_hash,
                        decision_without_hash=without_hash,
                        verified_scope_json=canonical_json(verified_scope),
                        active=1,
                    )
                )
                recorded.append(
                    {
                        "fingerprint": fingerprint,
                        "capability": capability,
                        "baseline_utility": baseline_utility,
                        "without_agent_utility": without_utility,
                        "marginal_delta": delta,
                        "decision_before_hash": baseline_hash,
                        "decision_without_hash": without_hash,
                        "verified_scope": verified_scope,
                        "method": "production_decision_leave_one_out_v2",
                        "provenance_hash": provenance_hash,
                    }
                )
    return recorded


def _write_verified_memory(host: Any, receipt: VerificationReceipt, claim: dict[str, Any]) -> list[dict[str, Any]]:
    if receipt.verified_status != "SUPPORTED":
        return []
    fingerprint = str(claim.get("contributor_fingerprint") or "")
    if not fingerprint:
        return []
    deterministic = receipt.authority_class == "deterministic_oracle"
    memory = MemoryItem(
        memory_id=sha256_obj({"verified_memory_receipt": receipt.receipt_hash, "claim_hash": receipt.claim_hash}),
        claim_hash=receipt.claim_hash,
        content=str(claim.get("statement", "")),
        owner_fingerprint=fingerprint,
        domain=str(claim.get("domain", "general")),
        origin_clusters=[receipt.source_independence_cluster],
        authority=1.0 if deterministic else 0.8,
        deterministic_verification=deterministic,
        verified_clusters=[receipt.source_independence_cluster],
        derived_from=[receipt.receipt_hash],
    )
    written = write_gate(memory)
    host.repository.save_memory_transition(
        written,
        reason="authenticated verification receipt write",
        from_status=memory.status.value,
    )
    promoted = promotion_gate(written)
    if promoted.status != written.status:
        host.repository.save_memory_transition(
            promoted,
            reason="verified memory promotion gate",
            from_status=written.status.value,
        )
    return [
        {
            "memory_id": written.memory_id,
            "from": memory.status.value,
            "to": written.status.value,
            "receipt_hash": receipt.receipt_hash,
        },
        *(
            [
                {
                    "memory_id": promoted.memory_id,
                    "from": written.status.value,
                    "to": promoted.status.value,
                    "receipt_hash": receipt.receipt_hash,
                }
            ]
            if promoted.status != written.status
            else []
        ),
    ]


def submit_verification(host: Any, submission: VerificationSubmission) -> dict[str, Any]:
    store = SwarmStateStore(host.repository.engine)
    duplicate = store.receipt_by_origin(submission.origin_key_hash)
    if duplicate is not None:
        return {
            "accepted": bool(duplicate.get("accepted")),
            "duplicate": True,
            "receipt": duplicate,
            "attributions": [],
            "removal_attributions": [],
            "memory_changes": [],
            "revocation": {},
            "germinal": None,
        }

    run = host.repository.get_run(submission.run_id)
    claim = None if run is None else _find_claim(run, submission.claim_hash)
    rejection: str | None = None
    policy: dict[str, Any] | None = None
    adjudication_origin_hash = submission.adjudication_origin_hash
    if run is None:
        rejection = "run_not_found"
    elif claim is None:
        rejection = "claim_hash_not_bound_to_run"
    else:
        authenticated, auth_reason, policy = store.authenticate_verifier(
            verifier_id=submission.verifier_id,
            authority_class=submission.authority_class,
            source_cluster=submission.source_independence_cluster,
            auth_token=submission.auth_token,
        )
        if not authenticated:
            rejection = auth_reason or "verifier_authentication_failed"
        elif submission.verifier_id.lower().startswith(("llm:", "model:")):
            rejection = "llm_self_rating_not_ground_truth"
        else:
            assert policy is not None
            adjudication_origin_hash = submission.policy_adjudication_origin_hash(str(policy["policy_hash"]))
            evidence_allowed, snapshots_allowed = _bound_proof_hashes(run)
            if not submission.evidence_hashes and not submission.snapshot_hashes:
                rejection = "verification_proof_missing"
            elif any(value not in evidence_allowed for value in submission.evidence_hashes):
                rejection = "evidence_hash_not_bound_to_run"
            elif any(value not in snapshots_allowed for value in submission.snapshot_hashes):
                rejection = "snapshot_hash_not_bound_to_run"
            else:
                rejection = _linked_receipt_rejection(
                    store,
                    submission,
                    adjudication_origin_hash=adjudication_origin_hash,
                )
                if rejection is None:
                    active_same_origin = active_receipt_for_origin(
                        host.repository.engine,
                        run_id=submission.run_id,
                        claim_hash=submission.claim_hash,
                        adjudication_origin_hash=adjudication_origin_hash,
                    )
                    if active_same_origin is not None:
                        linked = {
                            submission.supersedes_receipt_hash,
                            submission.appeal_of_receipt_hash,
                        }
                        if str(active_same_origin["receipt_hash"]) not in linked:
                            rejection = "active_adjudication_requires_supersession"

    receipt = build_receipt(
        submission,
        accepted=rejection is None,
        rejection_reason=rejection,
        verifier_policy_hash=None if policy is None else str(policy["policy_hash"]),
        verification_method=None if policy is None else str(policy["verification_method"]),
        adjudication_origin_hash=adjudication_origin_hash,
    )
    if rejection is not None or run is None or claim is None:
        return {
            "accepted": False,
            "duplicate": False,
            "receipt": receipt.model_dump(mode="json"),
            "attributions": [],
            "removal_attributions": [],
            "memory_changes": [],
            "revocation": {},
            "germinal": None,
        }

    inserted = store.persist_receipt(receipt)
    if not inserted:
        duplicate = store.receipt_by_origin(submission.origin_key_hash)
        return {
            "accepted": bool((duplicate or {}).get("accepted")),
            "duplicate": True,
            "receipt": duplicate,
            "attributions": [],
            "removal_attributions": [],
            "memory_changes": [],
            "revocation": {},
            "germinal": None,
        }

    revocation = {"removals": 0, "memory": 0, "evasions": 0, "mutations": 0, "germinal": 0}
    for prior_hash in (submission.supersedes_receipt_hash, submission.appeal_of_receipt_hash):
        if prior_hash is not None and store.deactivate_receipt(prior_hash, receipt.receipt_hash):
            cascade = revoke_receipt_derivatives(
                host.repository.engine,
                prior_hash,
                receipt.receipt_hash,
            )
            for key, value in cascade.items():
                revocation[key] = revocation.get(key, 0) + value

    learn = bool(run.get("learning_policy", {}).get("learn", False))
    fingerprint = str(claim.get("contributor_fingerprint") or "")
    capabilities = tuple(str(value) for value in claim.get("contributor_capabilities", []))
    outcome = receipt.verified_status == "SUPPORTED"
    attributions: list[dict[str, Any]] = []
    memory_changes: list[dict[str, Any]] = []
    if learn and fingerprint and capabilities:
        decisive = int(
            any(
                receipt.claim_hash in row.get("target_claim_hashes", [])
                for row in run.get("falsifiers", [])
            )
        )
        cost = _provider_cost_for(run, fingerprint)
        for capability in capabilities:
            family = f"{capability}_verified_task"
            if store.record_attribution(
                receipt=receipt,
                fingerprint=fingerprint,
                domain=str(claim.get("domain", "general")),
                capability=capability,
                test_family=family,
                outcome=outcome,
                predicted_probability=float(claim.get("probability", 0.5)),
                cost_contribution=cost,
                decisive_test_contribution=decisive,
            ):
                attributions.append(
                    {
                        "fingerprint": fingerprint,
                        "capability": capability,
                        "test_family": family,
                        "outcome": outcome,
                        "receipt_hash": receipt.receipt_hash,
                    }
                )
        memory_changes = _write_verified_memory(host, receipt, claim)

    removals = (
        _record_verified_decision_removals(host, store, receipt, run)
        if learn
        else []
    )
    learning_rebuild = store.rebuild_learning()
    germinal = _process_verified_evasion(host, receipt, run, learn=learn)
    return {
        "accepted": True,
        "duplicate": False,
        "receipt": receipt.model_dump(mode="json"),
        "learning_enabled_for_run": learn,
        "attributions": attributions,
        "removal_attributions": removals,
        "memory_changes": memory_changes,
        "revocation": revocation,
        "learning_rebuild": learning_rebuild,
        "germinal": germinal,
        "learned_state": store.learned_state(str(claim.get("domain", "general"))),
    }
