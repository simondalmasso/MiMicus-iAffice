from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from mimicus.canonical import sha256_obj
from mimicus.commercial.diagnosis import (
    CommercialBottleneck,
    CommercialDiagnosisPolicy,
    CommercialFunnelDiagnosis,
)


class CommercialInterventionCode(StrEnum):
    REPAIR_STAGE_EVIDENCE = "REPAIR_STAGE_EVIDENCE"
    QUALIFY_BACKLOG = "QUALIFY_BACKLOG"
    ADVANCE_QUALIFIED_TO_PROPOSAL = "ADVANCE_QUALIFIED_TO_PROPOSAL"
    RESOLVE_PROPOSALS = "RESOLVE_PROPOSALS"
    IMPROVE_TERMINAL_WIN_RATE = "IMPROVE_TERMINAL_WIN_RATE"
    COLLECT_FULL_FUNNEL_EVIDENCE = "COLLECT_FULL_FUNNEL_EVIDENCE"
    MAINTAIN_BASELINE = "MAINTAIN_BASELINE"


class CommercialMetricCriterion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    metric: str = Field(min_length=1)
    comparator: Literal["eq", "lt", "lte", "gte"]
    target: int | float
    baseline: int | float | None = None


class CommercialInterventionPlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    snapshot_hash: str = Field(min_length=64, max_length=64)
    diagnosis_hash: str = Field(min_length=64, max_length=64)
    policy_hash: str = Field(min_length=64, max_length=64)
    bottleneck: CommercialBottleneck
    code: CommercialInterventionCode
    focus: str = Field(min_length=1)
    criteria: tuple[CommercialMetricCriterion, ...]
    intervention_hash: str = Field(min_length=64, max_length=64)

    @field_validator("criteria")
    @classmethod
    def canonicalize_criteria(
        cls,
        value: tuple[CommercialMetricCriterion, ...],
    ) -> tuple[CommercialMetricCriterion, ...]:
        return tuple(sorted(value, key=lambda row: row.metric))


def _criterion(
    diagnosis: CommercialFunnelDiagnosis,
    metric: str,
    comparator: Literal["eq", "lt", "lte", "gte"],
    target: int | float,
) -> CommercialMetricCriterion:
    baseline = diagnosis.supporting_metrics.get(metric)
    return CommercialMetricCriterion(
        metric=metric,
        comparator=comparator,
        target=target,
        baseline=baseline,
    )


def plan_commercial_intervention(
    diagnosis: CommercialFunnelDiagnosis,
    policy: CommercialDiagnosisPolicy,
) -> CommercialInterventionPlan:
    policy_hash = sha256_obj(policy)
    if policy_hash != diagnosis.policy_hash:
        raise ValueError("diagnosis policy hash does not match intervention policy")

    bottleneck = diagnosis.bottleneck

    if bottleneck == CommercialBottleneck.DATA_QUALITY:
        code = CommercialInterventionCode.REPAIR_STAGE_EVIDENCE
        criteria = (
            _criterion(diagnosis, "invalid_order_count", "eq", 0),
        )
    elif bottleneck == CommercialBottleneck.TERMINAL_STALL:
        code = CommercialInterventionCode.RESOLVE_PROPOSALS
        criteria = (
            _criterion(
                diagnosis,
                "proposal_to_terminal_rate",
                "gte",
                policy.min_transition_rate,
            ),
        )
    elif bottleneck == CommercialBottleneck.LOW_WIN_RATE:
        code = CommercialInterventionCode.IMPROVE_TERMINAL_WIN_RATE
        criteria = (
            _criterion(
                diagnosis,
                "terminal_win_rate",
                "gte",
                policy.min_terminal_win_rate,
            ),
        )
    elif bottleneck == CommercialBottleneck.PROPOSAL_STALL:
        code = CommercialInterventionCode.ADVANCE_QUALIFIED_TO_PROPOSAL
        criteria = (
            _criterion(
                diagnosis,
                "qualified_to_proposal_rate",
                "gte",
                policy.min_transition_rate,
            ),
        )
    elif bottleneck == CommercialBottleneck.QUALIFICATION_BACKLOG:
        code = CommercialInterventionCode.QUALIFY_BACKLOG
        criteria = (
            _criterion(
                diagnosis,
                "qualify_count",
                "lt",
                policy.min_qualify_backlog,
            ),
        )
    elif bottleneck == CommercialBottleneck.INSUFFICIENT_DATA:
        code = CommercialInterventionCode.COLLECT_FULL_FUNNEL_EVIDENCE
        criteria = (
            _criterion(
                diagnosis,
                "qualified_to_proposal_eligible",
                "gte",
                policy.min_transition_samples,
            ),
            _criterion(
                diagnosis,
                "proposal_to_terminal_eligible",
                "gte",
                policy.min_transition_samples,
            ),
            _criterion(
                diagnosis,
                "terminal_count",
                "gte",
                policy.min_terminal_samples,
            ),
        )
    elif bottleneck == CommercialBottleneck.NO_OBSERVED_BOTTLENECK:
        code = CommercialInterventionCode.MAINTAIN_BASELINE
        criteria = (
            _criterion(
                diagnosis,
                "qualified_to_proposal_eligible",
                "gte",
                policy.min_transition_samples,
            ),
            _criterion(
                diagnosis,
                "proposal_to_terminal_eligible",
                "gte",
                policy.min_transition_samples,
            ),
            _criterion(
                diagnosis,
                "terminal_count",
                "gte",
                policy.min_terminal_samples,
            ),
            _criterion(
                diagnosis,
                "qualified_to_proposal_rate",
                "gte",
                policy.min_transition_rate,
            ),
            _criterion(
                diagnosis,
                "proposal_to_terminal_rate",
                "gte",
                policy.min_transition_rate,
            ),
            _criterion(
                diagnosis,
                "terminal_win_rate",
                "gte",
                policy.min_terminal_win_rate,
            ),
        )
    else:  # pragma: no cover - exhaustive over current enum
        raise ValueError(f"unsupported commercial bottleneck: {bottleneck}")

    canonical_criteria = tuple(sorted(criteria, key=lambda row: row.metric))
    semantic = {
        "snapshot_hash": diagnosis.snapshot_hash,
        "diagnosis_hash": diagnosis.diagnosis_hash,
        "policy_hash": policy_hash,
        "bottleneck": bottleneck.value,
        "code": code.value,
        "focus": diagnosis.focus,
        "criteria": [row.model_dump(mode="json") for row in canonical_criteria],
    }
    return CommercialInterventionPlan(
        snapshot_hash=diagnosis.snapshot_hash,
        diagnosis_hash=diagnosis.diagnosis_hash,
        policy_hash=policy_hash,
        bottleneck=bottleneck,
        code=code,
        focus=diagnosis.focus,
        criteria=canonical_criteria,
        intervention_hash=sha256_obj(semantic),
    )
