from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from mimicus.canonical import sha256_obj
from mimicus.claims.models import Claim
from mimicus.falsifiers.spec import FalsifierExecution
from mimicus.types import Verdict


class SwarmDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    candidate_answer: str
    selected_claim_hashes: tuple[str, ...]
    epistemic_status: Literal["SUPPORTED", "FALSIFIED", "INCONCLUSIVE"]
    confidence: float = Field(ge=0.0, le=1.0)
    decisive_refs: tuple[str, ...]
    unresolved_disagreements: tuple[dict[str, Any], ...]
    early_stop_reason: str
    provenance_hashes: tuple[str, ...]

    @property
    def hash(self) -> str:
        return sha256_obj(self)


def synthesize_swarm(
    claim_rows: list[tuple[str, Claim, float]],
    executions: list[FalsifierExecution],
    communications: list[dict[str, Any]],
    *,
    budget: dict[str, Any],
    coverage_complete: bool,
) -> SwarmDecision:
    if not claim_rows:
        return SwarmDecision(
            candidate_answer="",
            selected_claim_hashes=(),
            epistemic_status="INCONCLUSIVE",
            confidence=0.0,
            decisive_refs=(),
            unresolved_disagreements=(),
            early_stop_reason="no live claims",
            provenance_hashes=(),
        )
    execution_by_claim: dict[str, list[FalsifierExecution]] = {}
    for execution in executions:
        for claim_hash in execution.target_claim_hashes:
            execution_by_claim.setdefault(claim_hash, []).append(execution)
    ranked: list[tuple[float, str, Claim, str]] = []
    for fingerprint, claim, authority in claim_rows:
        linked = execution_by_claim.get(claim.hash, [])
        falsified = any(row.verdict == Verdict.FAIL for row in linked)
        passed = bool(linked) and all(row.verdict == Verdict.PASS for row in linked)
        local_status = "FALSIFIED" if falsified else ("SUPPORTED" if passed else "INCONCLUSIVE")
        # Select candidate content from calibrated authority/probability/evidence.
        # Deterministic verification is applied to the selected content as its
        # epistemic status rather than silently causing a falsified claim to
        # disappear from the user-facing decision.
        score = 0.50 * max(0.0, min(1.0, authority)) + 0.35 * claim.probability + 0.05 * min(2, len(claim.evidence_refs))
        ranked.append((score, fingerprint, claim, local_status))
    ranked.sort(key=lambda row: (-row[0], row[2].hash))
    best = ranked[0]
    distinct_statements = sorted({row[2].statement for row in ranked})
    probabilities = [row[2].probability for row in ranked]
    span = max(probabilities) - min(probabilities) if len(probabilities) > 1 else 0.0
    disagreements: list[dict[str, Any]] = []
    if len(distinct_statements) > 1 or span > 0.15:
        disagreements.append({"statements": distinct_statements, "probability_span": span, "challenge_edges": len(communications)})
    linked_best = execution_by_claim.get(best[2].hash, [])
    status: Literal["SUPPORTED", "FALSIFIED", "INCONCLUSIVE"]
    if best[3] == "FALSIFIED":
        status = "FALSIFIED"
    elif best[3] == "SUPPORTED" and not disagreements and coverage_complete:
        status = "SUPPORTED"
    else:
        status = "INCONCLUSIVE"
    confidence = min(0.95, max(0.0, best[0]))
    if status == "INCONCLUSIVE":
        confidence = min(confidence, 0.60)
    decisive = tuple(sorted({row.execution_snapshot_hash for row in linked_best if row.verdict in {Verdict.PASS, Verdict.FAIL}}))
    if bool(budget.get("fail_closed")):
        stop = "budget fail-closed"
    elif not coverage_complete:
        stop = "coverage incomplete"
    elif disagreements:
        stop = "residual disagreement"
    elif decisive:
        stop = "decisive deterministic falsifier evidence"
    else:
        stop = "available swarm evidence exhausted"
    provenance = tuple(sorted({best[2].hash, *best[2].evidence_refs, *decisive}))
    return SwarmDecision(
        candidate_answer=best[2].statement,
        selected_claim_hashes=(best[2].hash,),
        epistemic_status=status,
        confidence=confidence,
        decisive_refs=decisive,
        unresolved_disagreements=tuple(disagreements),
        early_stop_reason=stop,
        provenance_hashes=provenance,
    )
