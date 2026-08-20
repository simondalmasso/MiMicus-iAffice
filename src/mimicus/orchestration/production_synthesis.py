from __future__ import annotations

from typing import Any, Literal

from mimicus.claims.models import Claim
from mimicus.falsifiers.spec import FalsifierExecution
from mimicus.orchestration.synthesis import ClaimDecision, HierarchicalFanIn, SubtaskDecision, SwarmDecision, synthesize_swarm
from mimicus.types import Verdict


def _execution_index(executions: list[FalsifierExecution]) -> dict[str, list[FalsifierExecution]]:
    indexed: dict[str, list[FalsifierExecution]] = {}
    for execution in executions:
        for claim_hash in execution.target_claim_hashes:
            indexed.setdefault(claim_hash, []).append(execution)
    return indexed


def _local_status(executions: list[FalsifierExecution]) -> Literal["SUPPORTED", "FALSIFIED", "INCONCLUSIVE"]:
    if any(row.verdict == Verdict.FAIL for row in executions):
        return "FALSIFIED"
    conclusive = [row for row in executions if row.verdict != Verdict.INCONCLUSIVE]
    if conclusive and len(conclusive) == len(executions) and all(row.verdict == Verdict.PASS for row in conclusive):
        return "SUPPORTED"
    return "INCONCLUSIVE"


def _claims_compete(candidates: list[tuple[str, Claim, float]], statuses: dict[str, str]) -> bool:
    """Detect contradiction only inside one proposition/subtask.

    Different wording is not itself a contradiction. Typed assertions for the
    same predicate kind that bind different values compete, as do verified
    SUPPORTED/FALSIFIED outcomes for claims in this same subtask.
    """
    observed = {statuses.get(claim.identity_hash, "INCONCLUSIVE") for _, claim, _ in candidates}
    if "SUPPORTED" in observed and "FALSIFIED" in observed:
        return True
    by_kind: dict[str, set[str]] = {}
    for _, claim, _ in candidates:
        assertion = claim.assertion
        if assertion is None:
            continue
        kind = str(assertion.kind)
        by_kind.setdefault(kind, set()).add(assertion.hash)
    return any(len(hashes) > 1 for hashes in by_kind.values())


def _bounded_subtask_content(claims: tuple[ClaimDecision, ...]) -> str:
    statements = list(dict.fromkeys(row.statement.strip() for row in claims if row.statement.strip()))
    if not statements:
        return "(no bounded claim content)"
    per_claim = max(120, 960 // max(1, len(statements)))
    pieces = [value if len(value) <= per_claim else value[: per_claim - 3] + "..." for value in statements]
    return " || ".join(pieces)


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
    """Production synthesis with proposition-scoped hierarchical fan-in."""
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
    required = tuple(str(value) for value in hierarchy_execution.get("required_subtasks", []))
    execution_by_claim = _execution_index(executions)
    explicit_unresolved = {str(value) for value in hierarchy_execution.get("unresolved_subtasks", [])}

    subtask_decisions: list[SubtaskDecision] = []
    unresolved: set[str] = set(explicit_unresolved)
    falsified: set[str] = set()
    conflict_subtasks: set[str] = set()
    all_selected_claims: list[str] = []
    all_decisive: set[str] = set()
    all_provenance: set[str] = set()
    confidence_components: list[float] = []

    for subtask_hash in required:
        candidates = sorted(by_subtask.get(subtask_hash, []), key=lambda row: row[1].identity_hash)
        dependency_group = subtask_meta.get(subtask_hash, {}).get("dependency_group")
        if not candidates:
            unresolved.add(subtask_hash)
            subtask_decisions.append(
                SubtaskDecision(
                    subtask_hash=subtask_hash,
                    dependency_group=None if dependency_group is None else str(dependency_group),
                    status="INCONCLUSIVE",
                    claims=(),
                    disagreement=False,
                    provenance_hashes=(subtask_hash,),
                )
            )
            all_provenance.add(subtask_hash)
            continue

        statuses: dict[str, str] = {}
        claim_decisions: list[ClaimDecision] = []
        subtask_provenance: set[str] = {subtask_hash}
        for _, claim, authority in candidates:
            linked = execution_by_claim.get(claim.identity_hash, [])
            local_status = _local_status(linked)
            statuses[claim.identity_hash] = local_status
            decisive = tuple(sorted(row.execution_snapshot_hash for row in linked if row.verdict in {Verdict.PASS, Verdict.FAIL}))
            provenance = tuple(sorted({claim.identity_hash, *claim.evidence_refs, *decisive}))
            claim_decisions.append(
                ClaimDecision(
                    claim_hash=claim.identity_hash,
                    statement=claim.statement,
                    status=local_status,
                    authority=max(0.0, min(1.0, authority)),
                    probability=claim.probability,
                    decisive_falsifier_hashes=decisive,
                    provenance_hashes=provenance,
                )
            )
            all_selected_claims.append(claim.identity_hash)
            all_decisive.update(decisive)
            subtask_provenance.update(provenance)
            confidence_components.append(0.55 * max(0.0, min(1.0, authority)) + 0.45 * claim.probability)

        disagreement = _claims_compete(candidates, statuses)
        observed = set(statuses.values())
        if disagreement:
            subtask_status: Literal["SUPPORTED", "FALSIFIED", "INCONCLUSIVE"] = "INCONCLUSIVE"
            conflict_subtasks.add(subtask_hash)
            unresolved.add(subtask_hash)
        elif "INCONCLUSIVE" in observed:
            subtask_status = "INCONCLUSIVE"
            unresolved.add(subtask_hash)
        elif "FALSIFIED" in observed:
            subtask_status = "FALSIFIED"
            falsified.add(subtask_hash)
        else:
            subtask_status = "SUPPORTED"

        decision = SubtaskDecision(
            subtask_hash=subtask_hash,
            dependency_group=None if dependency_group is None else str(dependency_group),
            status=subtask_status,
            claims=tuple(claim_decisions),
            disagreement=disagreement,
            provenance_hashes=tuple(sorted(subtask_provenance)),
        )
        subtask_decisions.append(decision)
        all_provenance.update(subtask_provenance)

    if unresolved or not coverage_complete or bool(budget.get("fail_closed")):
        epistemic: Literal["SUPPORTED", "FALSIFIED", "INCONCLUSIVE"] = "INCONCLUSIVE"
    elif falsified:
        epistemic = "FALSIFIED"
    else:
        epistemic = "SUPPORTED"

    ordered_decisions = tuple(subtask_decisions)
    fan_in = HierarchicalFanIn(
        required_subtasks=required,
        subtask_decisions=ordered_decisions,
        status=epistemic,
        provenance_identities=tuple(sorted(set(all_selected_claims))),
        falsifier_snapshot_hashes=tuple(sorted(all_decisive)),
        unresolved_subtasks=tuple(sorted(unresolved)),
        falsified_subtasks=tuple(sorted(falsified)),
        disagreement_subtasks=tuple(sorted(conflict_subtasks)),
    )

    pieces = [f"[{row.subtask_hash[:12]}:{row.status}] {_bounded_subtask_content(row.claims)}" for row in ordered_decisions]
    composite = " | ".join(pieces)
    if len(composite) > 8000:
        # Keep at least a bounded slice from every required subtask rather than
        # truncating the tail and silently discarding later fan-in content.
        per_subtask = max(160, 7800 // max(1, len(pieces)))
        composite = " | ".join(piece if len(piece) <= per_subtask else piece[: per_subtask - 3] + "..." for piece in pieces)

    disagreements: list[dict[str, Any]] = []
    for row in ordered_decisions:
        if row.disagreement:
            disagreements.append(
                {
                    "kind": "same_subtask_conflict",
                    "subtask_hash": row.subtask_hash,
                    "dependency_group": row.dependency_group,
                    "claim_hashes": [claim.claim_hash for claim in row.claims],
                }
            )
    if unresolved:
        disagreements.append({"kind": "required_subtasks_unresolved", "subtask_hashes": sorted(unresolved)})
    if falsified:
        disagreements.append({"kind": "required_subtasks_falsified", "subtask_hashes": sorted(falsified)})

    confidence = min(confidence_components) if confidence_components else 0.0
    confidence = min(0.95, max(0.5, confidence)) if epistemic == "SUPPORTED" else min(0.6, confidence)

    if bool(budget.get("fail_closed")):
        stop = "budget fail-closed"
    elif unresolved:
        stop = "required hierarchical predicate unresolved"
    elif falsified:
        stop = "required hierarchical predicate falsified"
    else:
        stop = "all required hierarchical predicates composed"

    return SwarmDecision(
        candidate_answer=composite,
        selected_claim_hashes=tuple(all_selected_claims),
        epistemic_status=epistemic,
        confidence=confidence,
        decisive_refs=tuple(sorted(all_decisive)),
        unresolved_disagreements=tuple(disagreements),
        early_stop_reason=stop,
        provenance_hashes=tuple(sorted(all_provenance)),
        hierarchical_fan_in=fan_in,
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
