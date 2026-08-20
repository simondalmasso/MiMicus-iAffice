from __future__ import annotations

from typing import Any

from mimicus.claims.models import Claim
from mimicus.falsifiers.spec import FalsifierExecution
from mimicus.orchestration.synthesis import SwarmDecision, synthesize_swarm
from mimicus.types import Verdict


def _execution_index(executions: list[FalsifierExecution]) -> dict[str, list[FalsifierExecution]]:
    indexed: dict[str, list[FalsifierExecution]] = {}
    for execution in executions:
        for claim_hash in execution.target_claim_hashes:
            indexed.setdefault(claim_hash, []).append(execution)
    return indexed


def _local_status(executions: list[FalsifierExecution]) -> str:
    if any(row.verdict == Verdict.FAIL for row in executions):
        return "FALSIFIED"
    conclusive = [row for row in executions if row.verdict != Verdict.INCONCLUSIVE]
    if conclusive and all(row.verdict == Verdict.PASS for row in conclusive):
        return "SUPPORTED"
    return "INCONCLUSIVE"


def synthesize_production(
    claim_rows: list[tuple[str, Claim, float, str | None]],
    executions: list[FalsifierExecution],
    communications: list[dict[str, Any]],
    *,
    budget: dict[str, Any],
    coverage_complete: bool,
    morphology: str,
    subtasks: list[dict[str, Any]],
    hierarchy_execution: dict[str, Any],
) -> SwarmDecision:
    """Current production synthesis policy.

    Non-hierarchical runs preserve the accepted claim-level synthesis policy.
    Hierarchical runs compose complementary subtask propositions instead of
    treating every different statement as a contradiction.
    """
    plain_rows = [(fp, claim, authority) for fp, claim, authority, _ in claim_rows]
    if morphology != "hierarchical_fanout_fanin":
        return synthesize_swarm(
            plain_rows,
            executions,
            communications,
            budget=budget,
            coverage_complete=coverage_complete,
        )

    by_subtask: dict[str, list[tuple[str, Claim, float]]] = {}
    for fingerprint, claim, authority, subtask_hash in claim_rows:
        if subtask_hash:
            by_subtask.setdefault(subtask_hash, []).append((fingerprint, claim, authority))
    subtask_meta = {str(row.get("subtask_hash")): row for row in subtasks if row.get("subtask_hash")}
    required = [str(value) for value in hierarchy_execution.get("required_subtasks", [])]
    execution_by_claim = _execution_index(executions)
    selected: list[Claim] = []
    local_rows: list[dict[str, Any]] = []
    unresolved: list[str] = []
    falsified: list[str] = []
    group_conflicts: list[dict[str, Any]] = []

    for subtask_hash in required:
        candidates = by_subtask.get(subtask_hash, [])
        if not candidates:
            unresolved.append(subtask_hash)
            continue
        candidates.sort(key=lambda row: (-(0.60 * row[2] + 0.40 * row[1].probability), row[1].identity_hash))
        best = candidates[0][1]
        selected.append(best)
        linked = execution_by_claim.get(best.identity_hash, [])
        status = _local_status(linked)
        if status == "INCONCLUSIVE":
            unresolved.append(subtask_hash)
        elif status == "FALSIFIED":
            falsified.append(subtask_hash)
        statements = sorted({row[1].statement for row in candidates})
        if len(statements) > 1:
            group_conflicts.append(
                {
                    "kind": "same_subtask_conflict",
                    "subtask_hash": subtask_hash,
                    "dependency_group": subtask_meta.get(subtask_hash, {}).get("dependency_group"),
                    "statements": statements,
                }
            )
        local_rows.append(
            {
                "subtask_hash": subtask_hash,
                "dependency_group": subtask_meta.get(subtask_hash, {}).get("dependency_group"),
                "claim_hash": best.identity_hash,
                "status": status,
                "decisive_execution_hashes": sorted(row.execution_snapshot_hash for row in linked if row.verdict in {Verdict.PASS, Verdict.FAIL}),
            }
        )

    explicit_unresolved = {str(value) for value in hierarchy_execution.get("unresolved_subtasks", [])}
    unresolved = sorted(set(unresolved) | explicit_unresolved)
    if falsified:
        epistemic = "FALSIFIED"
    elif unresolved or group_conflicts or not coverage_complete:
        epistemic = "INCONCLUSIVE"
    else:
        epistemic = "SUPPORTED"

    ordered_selected = sorted(
        selected,
        key=lambda claim: (
            str(
                next(
                    (
                        meta.get("dependency_group")
                        for key, meta in subtask_meta.items()
                        if key in by_subtask and any(row[1].identity_hash == claim.identity_hash for row in by_subtask[key])
                    ),
                    "",
                )
            ),
            claim.identity_hash,
        ),
    )
    pieces = [claim.statement.strip() for claim in ordered_selected if claim.statement.strip()]
    composite = " | ".join(pieces)
    if len(composite) > 8000:
        composite = composite[:7997] + "..."
    decisive = tuple(
        sorted({row.execution_snapshot_hash for claim in selected for row in execution_by_claim.get(claim.identity_hash, []) if row.verdict in {Verdict.PASS, Verdict.FAIL}})
    )
    provenance = tuple(
        sorted(
            {
                *(claim.identity_hash for claim in selected),
                *(ref for claim in selected for ref in claim.evidence_refs),
                *decisive,
                *(str(row.get("subtask_hash")) for row in local_rows),
            }
        )
    )
    disagreements: list[dict[str, Any]] = [*group_conflicts]
    if unresolved:
        disagreements.append({"kind": "required_subtasks_unresolved", "subtask_hashes": unresolved})
    if falsified:
        disagreements.append({"kind": "required_subtasks_falsified", "subtask_hashes": sorted(falsified)})
    confidence_components = [claim.probability for claim in selected]
    confidence = min(confidence_components) if confidence_components else 0.0
    confidence = min(0.95, max(0.5, confidence)) if epistemic == "SUPPORTED" else min(0.6, confidence)
    if bool(budget.get("fail_closed")):
        stop = "budget fail-closed"
    elif falsified:
        stop = "required hierarchical predicate falsified"
    elif unresolved:
        stop = "required hierarchical predicate unresolved"
    elif group_conflicts:
        stop = "within-subtask contradiction"
    else:
        stop = "all required hierarchical predicates composed"
    return SwarmDecision(
        candidate_answer=composite,
        selected_claim_hashes=tuple(claim.identity_hash for claim in selected),
        epistemic_status=epistemic,  # type: ignore[arg-type]
        confidence=confidence,
        decisive_refs=decisive,
        unresolved_disagreements=tuple(disagreements),
        early_stop_reason=stop,
        provenance_hashes=provenance,
    )


def decision_hash_without_fingerprint(
    run: dict[str, Any],
    fingerprint: str | None,
) -> tuple[str, SwarmDecision]:
    """Deterministic decision counterfactual used by verified removal attribution."""
    from mimicus.claims.models import Claim
    from mimicus.falsifiers.spec import FalsifierExecution

    claims: list[tuple[str, Claim, float, str | None]] = []
    for row in run.get("final_claims", []):
        fp = str(row.get("contributor_fingerprint", ""))
        if fingerprint is not None and fp == fingerprint:
            continue
        material = {key: row[key] for key in Claim.model_fields if key in row}
        claim = Claim.model_validate(material)
        raw_authority = row.get("contributor_authority")
        authority = float(raw_authority) if isinstance(raw_authority, (int, float)) else float(row.get("probability", 0.5))
        claims.append((fp, claim, authority, row.get("subtask_hash")))
    executions = [
        FalsifierExecution.model_validate({key: row[key] for key in FalsifierExecution.model_fields if key in row}) for row in run.get("falsifiers", []) if isinstance(row, dict)
    ]
    allowed = {claim.identity_hash for _, claim, _, _ in claims}
    executions = [row for row in executions if any(target in allowed for target in row.target_claim_hashes)]
    decision = synthesize_production(
        claims,
        executions,
        list(run.get("persistent_state", {}).get("communications", [])),
        budget=dict(run.get("budget", {})),
        coverage_complete=bool(run.get("production_core", {}).get("coverage_complete", True)),
        morphology=str(run.get("morphology", "solo")),
        subtasks=list(run.get("subtasks", [])),
        hierarchy_execution=dict(run.get("hierarchy_execution", {})),
    )
    return decision.hash, decision
