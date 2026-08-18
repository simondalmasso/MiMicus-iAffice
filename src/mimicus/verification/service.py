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
from mimicus.verification.models import ACCEPTED_AUTHORITY_CLASSES, VerificationReceipt, VerificationSubmission, build_receipt


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
        payload = {"receipt_hash": receipt.receipt_hash, "status": "NO_SAFE_MUTATION_AVAILABLE", "parent_spec_hash": None if parent is None else parent.hash}
        store.record_germinal_outcome(receipt.receipt_hash, "NO_SAFE_MUTATION_AVAILABLE", payload)
        return payload
    context = _falsifier_context(host, receipt.run_id)
    current_tolerance = float(cast(Any, parent.params.get("relative_tolerance", 0.05)))
    params = dict(parent.params)
    if receipt.verified_status == "FALSIFIED" and row.get("verdict") == "PASS":
        params["relative_tolerance"] = max(1e-6, current_tolerance * 0.4)
    else:
        params["relative_tolerance"] = min(0.50, current_tolerance * 2.0)
    candidate_probe = parent.model_copy(update={"version": f"3.0.{receipt.receipt_hash[:8]}", "params": params, "parent_hash": parent.hash})
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
    payload: dict[str, Any] = {
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


def submit_verification(host: Any, submission: VerificationSubmission) -> dict[str, Any]:
    store = SwarmStateStore(host.repository.engine)
    duplicate = store.receipt_by_origin(submission.origin_key_hash)
    if duplicate is not None:
        return {"accepted": bool(duplicate.get("accepted")), "duplicate": True, "receipt": duplicate, "attributions": [], "germinal": None}
    run = host.repository.get_run(submission.run_id)
    rejection: str | None = None
    claim = None if run is None else _find_claim(run, submission.claim_hash)
    if run is None:
        rejection = "run_not_found"
    elif claim is None:
        rejection = "claim_hash_not_bound_to_run"
    elif submission.authority_class not in ACCEPTED_AUTHORITY_CLASSES:
        rejection = "authority_class_not_accepted"
    elif submission.verifier_id.lower().startswith(("llm:", "model:")):
        rejection = "llm_self_rating_not_ground_truth"
    elif submission.supersedes_receipt_hash and not store.receipt_exists(submission.supersedes_receipt_hash):
        rejection = "superseded_receipt_not_found"
    elif submission.appeal_of_receipt_hash and not store.receipt_exists(submission.appeal_of_receipt_hash):
        rejection = "appealed_receipt_not_found"
    receipt = build_receipt(submission, accepted=rejection is None, rejection_reason=rejection)
    inserted = store.persist_receipt(receipt)
    if not inserted:
        duplicate = store.receipt_by_origin(submission.origin_key_hash)
        return {"accepted": bool((duplicate or {}).get("accepted")), "duplicate": True, "receipt": duplicate, "attributions": [], "germinal": None}
    if not receipt.accepted or claim is None or run is None:
        return {"accepted": False, "duplicate": False, "receipt": receipt.model_dump(mode="json"), "attributions": [], "germinal": None}

    fingerprint = str(claim.get("contributor_fingerprint") or "")
    capabilities = tuple(str(value) for value in claim.get("contributor_capabilities", []))
    outcome = receipt.verified_status == "SUPPORTED"
    attributions: list[dict[str, Any]] = []
    if fingerprint and capabilities:
        for capability in capabilities:
            family = f"{capability}_verified_task"
            host.calibration.record_capability_verified(
                fingerprint,
                str(claim.get("domain", "general")),
                capability,
                family,
                predicted_probability=float(claim.get("probability", 0.5)),
                outcome=outcome,
                canary=False,
            )
            decisive = int(any(receipt.claim_hash in row.get("target_claim_hashes", []) for row in run.get("falsifiers", [])))
            cost = _provider_cost_for(run, fingerprint)
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
                attributions.append({"fingerprint": fingerprint, "capability": capability, "test_family": family, "outcome": outcome})
        store.update_pair_learning_for_run(receipt.run_id)
    germinal = _process_verified_evasion(host, receipt, run)
    return {
        "accepted": True,
        "duplicate": False,
        "receipt": receipt.model_dump(mode="json"),
        "attributions": attributions,
        "germinal": germinal,
        "learned_state": store.learned_state(str(claim.get("domain", "general"))),
    }
