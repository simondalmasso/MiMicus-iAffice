from __future__ import annotations

from dataclasses import asdict
from typing import Any, cast

from mimicus.canonical import sha256_obj
from mimicus.falsifiers.spec import FalsifierSpec
from mimicus.germinal.fossils import seed_fossils
from mimicus.germinal.mutate import mutate_params
from mimicus.germinal.promote import decide
from mimicus.storage.swarm_state import SwarmStateStore
from mimicus.types import Verdict
from mimicus.verification.models import VerificationReceipt, VerificationSubmission, build_receipt


def _find_claim(run: dict[str, Any], claim_hash: str) -> dict[str, Any] | None:
    for claim in run.get("final_claims", []):
        if claim.get("claim_hash") == claim_hash:
            return claim
    return None


def _provider_cost_for(run: dict[str, Any], fingerprint: str) -> float:
    usages = run.get("evidence_provenance", {}).get("provider_usages", [])
    for row in usages:
        if row.get("fingerprint") == fingerprint:
            budget = row.get("budget", {})
            if isinstance(budget, dict) and isinstance(budget.get("actual_usd"), (int, float)):
                return float(budget["actual_usd"])
    return 0.0


def _bound_proof_hashes(run: dict[str, Any]) -> tuple[set[str], set[str]]:
    provenance = run.get("evidence_provenance", {})
    evidence_hashes = {
        str(value)
        for key in ("provider_input_evidence_hashes", "falsifier_execution_evidence_hashes", "evidence_hashes")
        for value in provenance.get(key, [])
        if isinstance(value, str) and len(value) == 64
    }
    snapshot_hashes = {
        str(row.get("execution_snapshot_hash")) for row in run.get("falsifiers", []) if isinstance(row, dict) and isinstance(row.get("execution_snapshot_hash"), str)
    }
    return evidence_hashes, snapshot_hashes


def _verification_utility(claims: list[dict[str, Any]], verified_status: str, anchor_statement: str) -> float:
    if not claims:
        return 0.0
    weights = [max(0.01, float(row.get("probability", 0.5))) for row in claims]
    total = sum(weights)
    aligned = sum(weight for row, weight in zip(claims, weights, strict=True) if str(row.get("statement", "")) == anchor_statement)
    support_ratio = aligned / max(1e-9, total)
    return support_ratio if verified_status == "SUPPORTED" else 1.0 - support_ratio


def _record_removal_attributions(
    store: SwarmStateStore,
    receipt: VerificationReceipt,
    run: dict[str, Any],
    target_claim: dict[str, Any],
) -> list[dict[str, Any]]:
    all_claims = [row for row in run.get("final_claims", []) if isinstance(row, dict)]
    # Evaluate counterfactual utility with the verified target statement first so
    # the leave-one-out metric measures contribution to the adjudicated outcome.
    target_first = [target_claim] + [row for row in all_claims if row.get("claim_hash") != target_claim.get("claim_hash")]
    anchor_statement = str(target_claim.get("statement", ""))
    baseline = _verification_utility(target_first, receipt.verified_status, anchor_statement)
    fingerprints = sorted({str(row.get("contributor_fingerprint")) for row in all_claims if row.get("contributor_fingerprint")})
    recorded: list[dict[str, Any]] = []
    for fingerprint in fingerprints:
        without = [row for row in target_first if str(row.get("contributor_fingerprint")) != fingerprint]
        without_utility = _verification_utility(without, receipt.verified_status, anchor_statement)
        delta = max(-1.0, min(1.0, baseline - without_utility))
        contributor_claims = [row for row in all_claims if str(row.get("contributor_fingerprint")) == fingerprint]
        capabilities = sorted({str(capability) for row in contributor_claims for capability in row.get("contributor_capabilities", []) if capability})
        for capability in capabilities:
            provenance_hash = sha256_obj(
                {
                    "method": "leave_one_out_semantic_decision_v1",
                    "receipt_hash": receipt.receipt_hash,
                    "run_id": receipt.run_id,
                    "target_claim_hash": receipt.claim_hash,
                    "fingerprint": fingerprint,
                    "capability": capability,
                    "baseline_utility": baseline,
                    "without_agent_utility": without_utility,
                    "claim_hashes": sorted(str(row.get("claim_hash")) for row in all_claims),
                }
            )
            if store.record_removal_attribution(
                receipt=receipt,
                fingerprint=fingerprint,
                domain=str(target_claim.get("domain", "general")),
                capability=capability,
                baseline_utility=baseline,
                without_agent_utility=without_utility,
                marginal_delta=delta,
                provenance_hash=provenance_hash,
            ):
                recorded.append(
                    {
                        "fingerprint": fingerprint,
                        "capability": capability,
                        "baseline_utility": baseline,
                        "without_agent_utility": without_utility,
                        "marginal_delta": delta,
                        "method": "leave_one_out_semantic_decision_v1",
                        "provenance_hash": provenance_hash,
                    }
                )
    return recorded


def _falsifier_context(host: Any, run_id: str) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    conflicts: set[str] = set()
    for row in host.repository.get_evidence(run_id):
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
    return merged


def _find_spec(host: Any, domain: str, spec_hash: str) -> FalsifierSpec | None:
    for spec in host.services.falsifiers.specs(domain).values():
        if spec.hash == spec_hash:
            return spec
    for spec in host.repository.promoted_falsifiers(domain):
        if spec.hash == spec_hash:
            return spec
    return None


def _process_verified_evasion(host: Any, receipt: VerificationReceipt, run: dict[str, Any]) -> dict[str, Any] | None:
    relevant = [row for row in run.get("falsifiers", []) if receipt.claim_hash in row.get("target_claim_hashes", [])]
    contradictions = [
        row
        for row in relevant
        if (receipt.verified_status == "SUPPORTED" and row.get("verdict") == "FAIL") or (receipt.verified_status == "FALSIFIED" and row.get("verdict") == "PASS")
    ]
    if not contradictions:
        return None
    row = contradictions[0]
    domain = str((_find_claim(run, receipt.claim_hash) or {}).get("domain", "general"))
    parent = _find_spec(host, domain, str(row.get("spec_hash", "")))
    store = SwarmStateStore(host.repository.engine)
    if parent is None or parent.primitive != "numeric_invariant":
        no_safe_payload: dict[str, Any] = {
            "receipt_hash": receipt.receipt_hash,
            "status": "NO_SAFE_MUTATION_AVAILABLE",
            "parent_spec_hash": None if parent is None else parent.hash,
        }
        store.record_germinal_outcome(receipt.receipt_hash, "NO_SAFE_MUTATION_AVAILABLE", no_safe_payload)
        return no_safe_payload
    context = _falsifier_context(host, receipt.run_id)
    current_tolerance = float(cast(Any, parent.params.get("relative_tolerance", 0.05)))
    params = dict(parent.params)
    if receipt.verified_status == "FALSIFIED" and row.get("verdict") == "PASS":
        params["relative_tolerance"] = max(1e-6, current_tolerance * 0.4)
    else:
        params["relative_tolerance"] = min(0.50, current_tolerance * 2.0)
    candidate_probe = parent.model_copy(update={"version": f"3.1.{receipt.receipt_hash[:8]}", "params": params, "parent_hash": parent.hash})
    candidate_execution = host.services.falsifiers.run(candidate_probe, context)
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
        host.repository.seed_fossil(fossil.snapshot_hash, fossil.primitive, fossil.expected.value, asdict(fossil))
    decision = decide(parent, mutation, fossils)
    evasion_hash = sha256_obj(
        {
            "receipt": receipt.receipt_hash,
            "parent": parent.hash,
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
    }
    host.repository.persist_germinal_decision(
        evasion_hash=evasion_hash,
        parent_spec_hash=parent.hash,
        ground_truth_hash=receipt.receipt_hash,
        evasion_payload={"receipt": receipt.model_dump(mode="json"), "contradicted_execution": row},
        candidate_hash=mutation.candidate.hash,
        candidate_spec=mutation.candidate,
        status=decision.status,
        metrics=metrics,
        domain=domain,
    )
    germinal_payload: dict[str, Any] = {
        "receipt_hash": receipt.receipt_hash,
        "evasion_hash": evasion_hash,
        "parent_hash": parent.hash,
        "candidate_hash": mutation.candidate.hash,
        "status": decision.status,
        "germinal_entry_state": "GERMINAL_QUARANTINE",
        "metrics": metrics,
    }
    store.record_germinal_outcome(receipt.receipt_hash, decision.status, germinal_payload)
    return germinal_payload


def _linked_receipt_rejection(store: SwarmStateStore, submission: VerificationSubmission) -> str | None:
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
    return None


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
            "germinal": None,
        }

    run = host.repository.get_run(submission.run_id)
    claim = None if run is None else _find_claim(run, submission.claim_hash)
    rejection: str | None = None
    policy: dict[str, Any] | None = None
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
            evidence_allowed, snapshots_allowed = _bound_proof_hashes(run)
            if not submission.evidence_hashes and not submission.snapshot_hashes:
                rejection = "verification_proof_missing"
            elif any(value not in evidence_allowed for value in submission.evidence_hashes):
                rejection = "evidence_hash_not_bound_to_run"
            elif any(value not in snapshots_allowed for value in submission.snapshot_hashes):
                rejection = "snapshot_hash_not_bound_to_run"
            else:
                rejection = _linked_receipt_rejection(store, submission)

    receipt = build_receipt(
        submission,
        accepted=rejection is None,
        rejection_reason=rejection,
        verifier_policy_hash=None if policy is None else str(policy["policy_hash"]),
        verification_method=None if policy is None else str(policy["verification_method"]),
    )
    if rejection is not None or run is None or claim is None:
        # Reject fail-closed without polluting immutable accepted-origin indexes;
        # callers may correct credentials/proof and resubmit.
        return {
            "accepted": False,
            "duplicate": False,
            "receipt": receipt.model_dump(mode="json"),
            "attributions": [],
            "removal_attributions": [],
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
            "germinal": None,
        }

    for prior_hash in (submission.supersedes_receipt_hash, submission.appeal_of_receipt_hash):
        if prior_hash is not None:
            store.deactivate_receipt(prior_hash, receipt.receipt_hash)

    fingerprint = str(claim.get("contributor_fingerprint") or "")
    capabilities = tuple(str(value) for value in claim.get("contributor_capabilities", []))
    outcome = receipt.verified_status == "SUPPORTED"
    attributions: list[dict[str, Any]] = []
    if fingerprint and capabilities:
        decisive = int(any(receipt.claim_hash in row.get("target_claim_hashes", []) for row in run.get("falsifiers", [])))
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
                    }
                )

    removals = _record_removal_attributions(store, receipt, run, claim)
    learning_rebuild = store.rebuild_learning()
    germinal = _process_verified_evasion(host, receipt, run)
    return {
        "accepted": True,
        "duplicate": False,
        "receipt": receipt.model_dump(mode="json"),
        "attributions": attributions,
        "removal_attributions": removals,
        "learning_rebuild": learning_rebuild,
        "germinal": germinal,
        "learned_state": store.learned_state(str(claim.get("domain", "general"))),
    }
