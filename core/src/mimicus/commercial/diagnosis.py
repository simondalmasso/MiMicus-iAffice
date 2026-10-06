from __future__ import annotations

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from mimicus.canonical import sha256_obj
from mimicus.commercial.funnel import CommercialFunnelSnapshot


class CommercialBottleneck(StrEnum):
    DATA_QUALITY = "DATA_QUALITY"
    TERMINAL_STALL = "TERMINAL_STALL"
    LOW_WIN_RATE = "LOW_WIN_RATE"
    PROPOSAL_STALL = "PROPOSAL_STALL"
    QUALIFICATION_BACKLOG = "QUALIFICATION_BACKLOG"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    NO_OBSERVED_BOTTLENECK = "NO_OBSERVED_BOTTLENECK"


class CommercialDiagnosisPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = Field(default="commercial-diagnosis-v1", min_length=1)
    min_transition_samples: int = Field(default=3, ge=1)
    min_terminal_samples: int = Field(default=3, ge=1)
    min_transition_rate: float = Field(default=0.5, ge=0.0, le=1.0)
    min_terminal_win_rate: float = Field(default=0.34, ge=0.0, le=1.0)
    min_qualify_backlog: int = Field(default=3, ge=1)


class CommercialFunnelDiagnosis(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    snapshot_hash: str = Field(min_length=64, max_length=64)
    policy_hash: str = Field(min_length=64, max_length=64)
    bottleneck: CommercialBottleneck
    reasons: tuple[str, ...]
    focus: str = Field(min_length=1)
    supporting_metrics: Mapping[str, int | float | None]
    diagnosis_hash: str = Field(min_length=64, max_length=64)

    @field_validator("supporting_metrics")
    @classmethod
    def freeze_metrics(
        cls,
        value: Mapping[str, int | float | None],
    ) -> Mapping[str, int | float | None]:
        return MappingProxyType(dict(sorted(value.items())))

    @field_serializer("supporting_metrics")
    def serialize_metrics(
        self,
        value: Mapping[str, int | float | None],
    ) -> dict[str, int | float | None]:
        return dict(value)


def diagnose_commercial_funnel(
    snapshot: CommercialFunnelSnapshot,
    policy: CommercialDiagnosisPolicy,
) -> CommercialFunnelDiagnosis:
    metrics = snapshot.overall
    q2p = metrics.qualified_to_proposal
    p2t = metrics.proposal_to_terminal
    terminal_count = sum(metrics.terminal_outcome_counts.values())
    qualify_count = int(metrics.next_action_counts.get("QUALIFY", 0))
    invalid_order_count = q2p.invalid_order_count + p2t.invalid_order_count

    supporting: dict[str, int | float | None] = {
        "lead_count": metrics.lead_count,
        "qualify_count": qualify_count,
        "qualified_to_proposal_eligible": q2p.eligible_count,
        "qualified_to_proposal_advanced": q2p.advanced_count,
        "qualified_to_proposal_rate": q2p.rate,
        "proposal_to_terminal_eligible": p2t.eligible_count,
        "proposal_to_terminal_advanced": p2t.advanced_count,
        "proposal_to_terminal_rate": p2t.rate,
        "terminal_count": terminal_count,
        "terminal_win_rate": metrics.terminal_win_rate,
        "invalid_order_count": invalid_order_count,
    }

    if invalid_order_count > 0:
        bottleneck = CommercialBottleneck.DATA_QUALITY
        reasons = ("invalid_stage_order",)
        focus = "repair_stage_evidence"
    elif (
        p2t.eligible_count >= policy.min_transition_samples
        and p2t.rate is not None
        and p2t.rate < policy.min_transition_rate
    ):
        bottleneck = CommercialBottleneck.TERMINAL_STALL
        reasons = ("proposal_to_terminal_below_threshold",)
        focus = "advance_proposals_to_outcome"
    elif (
        terminal_count >= policy.min_terminal_samples
        and metrics.terminal_win_rate is not None
        and metrics.terminal_win_rate < policy.min_terminal_win_rate
    ):
        bottleneck = CommercialBottleneck.LOW_WIN_RATE
        reasons = ("terminal_win_rate_below_threshold",)
        focus = "improve_offer_and_closing"
    elif (
        q2p.eligible_count >= policy.min_transition_samples
        and q2p.rate is not None
        and q2p.rate < policy.min_transition_rate
    ):
        bottleneck = CommercialBottleneck.PROPOSAL_STALL
        reasons = ("qualified_to_proposal_below_threshold",)
        focus = "convert_qualified_to_proposal"
    elif qualify_count >= policy.min_qualify_backlog:
        bottleneck = CommercialBottleneck.QUALIFICATION_BACKLOG
        reasons = ("qualify_queue_above_threshold",)
        focus = "qualify_replied_leads"
    else:
        enough_full_funnel_evidence = (
            q2p.eligible_count >= policy.min_transition_samples
            and p2t.eligible_count >= policy.min_transition_samples
            and terminal_count >= policy.min_terminal_samples
        )
        if enough_full_funnel_evidence:
            bottleneck = CommercialBottleneck.NO_OBSERVED_BOTTLENECK
            reasons = ("configured_thresholds_met",)
            focus = "maintain_and_measure"
        else:
            bottleneck = CommercialBottleneck.INSUFFICIENT_DATA
            reasons = ("insufficient_stage_evidence",)
            focus = "collect_stage_evidence"

    policy_hash = sha256_obj(policy)
    semantic = {
        "snapshot_hash": snapshot.snapshot_hash,
        "policy_hash": policy_hash,
        "bottleneck": bottleneck.value,
        "reasons": list(reasons),
        "focus": focus,
        "supporting_metrics": dict(sorted(supporting.items())),
    }
    return CommercialFunnelDiagnosis(
        snapshot_hash=snapshot.snapshot_hash,
        policy_hash=policy_hash,
        bottleneck=bottleneck,
        reasons=reasons,
        focus=focus,
        supporting_metrics=supporting,
        diagnosis_hash=sha256_obj(semantic),
    )
