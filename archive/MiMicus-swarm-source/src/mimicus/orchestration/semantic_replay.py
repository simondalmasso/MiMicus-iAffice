from __future__ import annotations

from typing import Any

from mimicus.canonical import sha256_obj
from mimicus.claims.models import Claim
from mimicus.claims.projections import EvidenceProjection
from mimicus.falsifiers.primitives import execute_claim_bound
from mimicus.falsifiers.spec import FalsifierExecution, FalsifierSpec
from mimicus.orchestration.causal_replay import verify_causal_execution
from mimicus.orchestration.production_synthesis import synthesize_production
from mimicus.orchestration.replay import verify_replay


def _claim(material: dict[str, Any]) -> Claim:
    return Claim.model_validate({key: material[key] for key in Claim.model_fields if key in material})


def semantic_replay(repository: Any, run_id: str) -> dict[str, Any]:
    run = repository.get_run(run_id)
    if run is None:
        return {
            "verified": False,
            "integrity_verified": False,
            "semantic_reexecution_verified": False,
            "status": "RUN_NOT_FOUND",
            "run_id": run_id,
        }
    integrity = verify_replay(repository.get_events(run_id), str(run.get("ledger_head", "")))
    semantic = run.get("semantic_replay")
    if not isinstance(semantic, dict) or not semantic:
        return {
            "verified": False,
            "integrity_verified": bool(integrity.get("verified")),
            "semantic_reexecution_verified": False,
            "status": "SEMANTIC_SNAPSHOT_NOT_AVAILABLE",
            "run_id": run_id,
            "ledger": integrity,
        }
    input_material = semantic.get("input_material")
    expected = semantic.get("expected")
    if not isinstance(input_material, dict) or not isinstance(expected, dict):
        return {
            "verified": False,
            "integrity_verified": bool(integrity.get("verified")),
            "semantic_reexecution_verified": False,
            "status": "SEMANTIC_SNAPSHOT_MALFORMED",
            "run_id": run_id,
            "ledger": integrity,
        }
    input_hash_ok = sha256_obj(input_material) == semantic.get("input_hash")
    expected_hash_ok = sha256_obj(expected) == semantic.get("expected_hash")
    snapshot_version = str(input_material.get("version", "ORDER-008-semantic-replay-v1"))
    causal_required = snapshot_version == "ORDER-008-semantic-replay-v2"
    causal_material = input_material.get("causal_execution")
    causal_available = isinstance(causal_material, dict) and bool(causal_material)
    causal_result = verify_causal_execution(causal_material) if causal_available else {"verified": not causal_required, "semantic_hash": None, "reason": "causal snapshot not available"}
    causal_hash_ok = (not causal_required and not causal_available) or (
        bool(causal_result.get("verified"))
        and causal_result.get("semantic_hash") == expected.get("causal_semantic_hash")
    )
    if not bool(semantic.get("replayable_provider")):
        return {
            "verified": bool(integrity.get("verified")) and input_hash_ok and expected_hash_ok and causal_hash_ok,
            "integrity_verified": bool(integrity.get("verified")),
            "semantic_reexecution_verified": False,
            "status": "INTEGRITY_VERIFIED_PROVIDER_NOT_SEMANTICALLY_REPLAYABLE",
            "run_id": run_id,
            "input_hash_verified": input_hash_ok,
            "expected_hash_verified": expected_hash_ok,
            "causal_contract_verified": causal_hash_ok if causal_required or causal_available else None,
            "causal_contract": causal_result,
            "ledger": integrity,
        }
    if not input_hash_ok or not expected_hash_ok:
        return {
            "verified": False,
            "integrity_verified": bool(integrity.get("verified")),
            "semantic_reexecution_verified": False,
            "status": "SEMANTIC_INPUT_TAMPERED",
            "run_id": run_id,
            "input_hash_verified": input_hash_ok,
            "expected_hash_verified": expected_hash_ok,
            "ledger": integrity,
        }

    projection_ok = True
    projection_rows = input_material.get("projection_rows", {})
    if isinstance(projection_rows, dict):
        for projection_hash, row in projection_rows.items():
            try:
                projection = EvidenceProjection.model_validate(
                    {
                        "projection_hash": row["projection_hash"],
                        "projection_snapshot_hash": row["projection_snapshot_hash"],
                        "parent_evidence_hash": row["projection_parent_hash"],
                        "parent_canonical_evidence_hash": row.get("canonical_evidence_hash"),
                        "declared_scope": tuple(row.get("projection_scope", [])),
                        "origin": row["origin"],
                        "source_class": row["source_class"],
                        "observed_at": row.get("observed_at"),
                        "as_of": row.get("as_of"),
                        "independence_cluster": row["independence_cluster"],
                        "content": row.get("content", ""),
                        "extracted_facts": row.get("extracted_facts", {}),
                        "extraction_method": row["extraction_method"],
                        "authority_class": row["authority_class"],
                        "units": row.get("units"),
                    }
                )
                projection_ok = projection_ok and projection.projection_hash == projection_hash
            except Exception:
                projection_ok = False

    replayed_executions: list[FalsifierExecution] = []
    execution_ok = True
    for row in input_material.get("replay_executions", []):
        try:
            spec = FalsifierSpec.model_validate(row["spec"])
            claim = Claim.model_validate(row["claim"])
            exact_context = dict(row.get("evidence_context", {}))
            context_hash_ok = sha256_obj(exact_context) == row.get("evidence_context_hash")
            execution = execute_claim_bound(
                spec,
                claim,
                exact_context,
                evidence_projection_hashes=tuple(row.get("evidence_projection_hashes", [])),
                selection_reason=row.get("selection_reason"),
            )
            replayed_executions.append(execution)
            execution_ok = (
                execution_ok
                and context_hash_ok
                and execution.execution_snapshot_hash == row.get("expected_snapshot_hash")
                and execution.verdict.value == row.get("expected_verdict")
            )
        except Exception:
            execution_ok = False

    claim_material = input_material.get("claim_rows", [])
    claim_rows: list[tuple[str, Claim, float, str | None]] = []
    for row in claim_material:
        claim = _claim(row)
        claim_rows.append(
            (
                str(row.get("contributor_fingerprint", "")),
                claim,
                float(row["contributor_authority"]) if isinstance(row.get("contributor_authority"), (int, float)) else 0.5,
                row.get("subtask_hash"),
            )
        )
    claim_hashes = sorted(claim.identity_hash for _, claim, _, _ in claim_rows)
    claim_ok = claim_hashes == sorted(expected.get("claim_identity_hashes", []))
    execution_hashes = sorted(row.execution_snapshot_hash for row in replayed_executions)
    execution_set_ok = execution_hashes == sorted(expected.get("falsifier_snapshot_hashes", []))
    coverage_complete = bool(run.get("production_core", {}).get("coverage_complete", True))
    decision = synthesize_production(
        claim_rows,
        replayed_executions,
        list(input_material.get("communications", [])),
        budget=dict(input_material.get("budget", {})),
        coverage_complete=coverage_complete,
        morphology=str(input_material.get("morphology", "solo")),
        subtasks=list(input_material.get("subtasks", [])),
        hierarchy_execution=dict(input_material.get("hierarchy_execution", {})),
    )
    decision_ok = decision.hash == expected.get("decision_hash")
    plan_ok = input_material.get("plan_hash") == expected.get("plan_hash") == run.get("plan_hash")
    semantic_ok = all((projection_ok, execution_ok, execution_set_ok, claim_ok, decision_ok, plan_ok, causal_hash_ok))
    overall = bool(integrity.get("verified")) and semantic_ok
    return {
        "verified": overall,
        "integrity_verified": bool(integrity.get("verified")),
        "semantic_reexecution_verified": semantic_ok,
        "status": "SEMANTIC_REEXECUTION_VERIFIED" if overall else "SEMANTIC_REEXECUTION_MISMATCH",
        "run_id": run_id,
        "input_hash_verified": input_hash_ok,
        "expected_hash_verified": expected_hash_ok,
        "projection_integrity_verified": projection_ok,
        "claim_identity_verified": claim_ok,
        "falsifier_reexecution_verified": execution_ok and execution_set_ok,
        "decision_reexecution_verified": decision_ok,
        "plan_contract_verified": plan_ok,
        "causal_contract_verified": causal_hash_ok if causal_required or causal_available else None,
        "causal_contract": causal_result,
        "replayed_decision_hash": decision.hash,
        "replayed_claim_hashes": claim_hashes,
        "replayed_falsifier_hashes": execution_hashes,
        "ledger": integrity,
    }
