from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from datetime import datetime
from statistics import median
from types import MappingProxyType
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from mimicus.canonical import sha256_obj
from mimicus.commercial.models import (
    CommercialStage,
    LeadCandidate,
    LeadDecision,
    LeadDecisionBatch,
    LeadDisposition,
    LeadNextAction,
    LeadStage,
)


class FunnelTransitionStats(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    eligible_count: int = Field(ge=0)
    advanced_count: int = Field(ge=0)
    rate: float | None = Field(default=None, ge=0.0, le=1.0)
    median_hours: float | None = Field(default=None, ge=0.0)
    invalid_order_count: int = Field(default=0, ge=0)


class CommercialCalibrationRow(BaseModel):
    """Sanitized commercial row suitable for deterministic offline evaluation."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    prospect_id: str = Field(min_length=1)
    lane: Literal["facebook", "reddit"]
    setter_score: float = Field(ge=0.0, le=100.0)
    scam_risk: Literal["low", "medium", "high"]
    outreach_status: str = Field(min_length=1)
    stage: LeadStage
    commercial_stage: CommercialStage
    disposition: LeadDisposition
    next_action: LeadNextAction
    qualified_at: datetime | None = None
    proposal_at: datetime | None = None
    terminal_at: datetime | None = None
    terminal_outcome: Literal["won", "lost"] | None = None

    @field_validator("qualified_at", "proposal_at", "terminal_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("commercial funnel timestamps must include timezone information")
        return value


class FunnelMetrics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    lead_count: int = Field(ge=0)
    disposition_counts: Mapping[str, int]
    next_action_counts: Mapping[str, int]
    current_commercial_stage_counts: Mapping[str, int]
    terminal_outcome_counts: Mapping[str, int]
    terminal_win_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    qualified_to_proposal: FunnelTransitionStats
    proposal_to_terminal: FunnelTransitionStats

    @field_validator(
        "disposition_counts",
        "next_action_counts",
        "current_commercial_stage_counts",
        "terminal_outcome_counts",
    )
    @classmethod
    def freeze_counts(cls, value: Mapping[str, int]) -> Mapping[str, int]:
        normalized = {str(key): int(count) for key, count in value.items()}
        if any(count < 0 for count in normalized.values()):
            raise ValueError("funnel counts must be non-negative")
        return MappingProxyType(dict(sorted(normalized.items())))

    @field_serializer(
        "disposition_counts",
        "next_action_counts",
        "current_commercial_stage_counts",
        "terminal_outcome_counts",
    )
    def serialize_counts(self, value: Mapping[str, int]) -> dict[str, int]:
        return dict(value)


class CommercialFunnelSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    as_of: datetime
    policy_hash: str = Field(min_length=64, max_length=64)
    batch_hash: str = Field(min_length=64, max_length=64)
    overall: FunnelMetrics
    by_lane: Mapping[str, FunnelMetrics]
    calibration_rows: tuple[CommercialCalibrationRow, ...]
    snapshot_hash: str = Field(min_length=64, max_length=64)

    @field_validator("as_of")
    @classmethod
    def require_as_of_timezone(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("as_of must include timezone information")
        return value

    @field_validator("by_lane")
    @classmethod
    def freeze_lanes(cls, value: Mapping[str, FunnelMetrics]) -> Mapping[str, FunnelMetrics]:
        return MappingProxyType(dict(sorted(value.items())))

    @field_serializer("by_lane")
    def serialize_lanes(self, value: Mapping[str, FunnelMetrics]) -> dict[str, FunnelMetrics]:
        return dict(value)


def _first_stage_time(
    candidate: LeadCandidate,
    stage: CommercialStage,
    *,
    as_of: datetime,
) -> datetime | None:
    observed = sorted(
        evidence.observed_at
        for evidence in candidate.commercial.evidence
        if evidence.stage == stage and evidence.observed_at <= as_of
    )
    return observed[0] if observed else None


def _calibration_row(
    candidate: LeadCandidate,
    decision: LeadDecision,
    *,
    as_of: datetime,
) -> CommercialCalibrationRow:
    qualified_at = _first_stage_time(candidate, CommercialStage.QUALIFIED, as_of=as_of)
    proposal_at = _first_stage_time(candidate, CommercialStage.PROPOSAL, as_of=as_of)

    terminal_outcome: Literal["won", "lost"] | None = None
    terminal_at: datetime | None = None
    if decision.commercial_stage == CommercialStage.WON:
        terminal_outcome = "won"
        terminal_at = _first_stage_time(candidate, CommercialStage.WON, as_of=as_of)
    elif decision.commercial_stage == CommercialStage.LOST:
        terminal_outcome = "lost"
        terminal_at = _first_stage_time(candidate, CommercialStage.LOST, as_of=as_of)

    return CommercialCalibrationRow(
        prospect_id=candidate.prospect_id,
        lane=candidate.lane,
        setter_score=candidate.setter_score,
        scam_risk=candidate.scam_risk,
        outreach_status=candidate.outreach_status,
        stage=decision.stage,
        commercial_stage=decision.commercial_stage,
        disposition=decision.disposition,
        next_action=decision.next_action,
        qualified_at=qualified_at,
        proposal_at=proposal_at,
        terminal_at=terminal_at,
        terminal_outcome=terminal_outcome,
    )


def _transition(
    rows: list[CommercialCalibrationRow],
    *,
    source_field: Literal["qualified_at", "proposal_at"],
    destination_field: Literal["proposal_at", "terminal_at"],
) -> FunnelTransitionStats:
    eligible = [row for row in rows if getattr(row, source_field) is not None]
    elapsed: list[float] = []
    invalid = 0

    for row in eligible:
        source = getattr(row, source_field)
        destination = getattr(row, destination_field)
        assert isinstance(source, datetime)
        if destination is None:
            continue
        if destination < source:
            invalid += 1
            continue
        elapsed.append((destination - source).total_seconds() / 3600.0)

    advanced = len(elapsed)
    rate = None if not eligible else advanced / len(eligible)
    median_hours = None if not elapsed else float(median(elapsed))
    return FunnelTransitionStats(
        eligible_count=len(eligible),
        advanced_count=advanced,
        rate=rate,
        median_hours=median_hours,
        invalid_order_count=invalid,
    )


def _metrics(rows: list[CommercialCalibrationRow]) -> FunnelMetrics:
    dispositions = Counter(row.disposition.value for row in rows)
    next_actions = Counter(row.next_action.value for row in rows)
    stages = Counter(row.commercial_stage.value for row in rows)
    terminal = Counter(
        row.terminal_outcome
        for row in rows
        if row.terminal_outcome is not None and row.terminal_at is not None
    )
    terminal_total = terminal.get("won", 0) + terminal.get("lost", 0)
    win_rate = None if terminal_total == 0 else terminal.get("won", 0) / terminal_total

    return FunnelMetrics(
        lead_count=len(rows),
        disposition_counts=dict(dispositions),
        next_action_counts=dict(next_actions),
        current_commercial_stage_counts=dict(stages),
        terminal_outcome_counts={str(key): int(value) for key, value in terminal.items()},
        terminal_win_rate=win_rate,
        qualified_to_proposal=_transition(
            rows,
            source_field="qualified_at",
            destination_field="proposal_at",
        ),
        proposal_to_terminal=_transition(
            rows,
            source_field="proposal_at",
            destination_field="terminal_at",
        ),
    )


def build_commercial_funnel(
    candidates: list[LeadCandidate],
    batch: LeadDecisionBatch,
    *,
    as_of: datetime,
) -> CommercialFunnelSnapshot:
    if as_of.utcoffset() is None:
        raise ValueError("as_of must include timezone information")

    candidate_ids = [candidate.prospect_id for candidate in candidates]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("candidate IDs contain duplicates")
    decision_ids = [decision.prospect_id for decision in batch.decisions]
    if len(decision_ids) != len(set(decision_ids)):
        raise ValueError("decision batch contains duplicate prospect IDs")
    if set(candidate_ids) != set(batch.input_ids) or set(candidate_ids) != set(decision_ids):
        raise ValueError("candidate IDs do not match authoritative decision batch")

    decision_by_id = {decision.prospect_id: decision for decision in batch.decisions}
    rows = tuple(
        sorted(
            (
                _calibration_row(
                    candidate,
                    decision_by_id[candidate.prospect_id],
                    as_of=as_of,
                )
                for candidate in candidates
            ),
            key=lambda row: (row.lane, row.prospect_id),
        )
    )

    by_lane = {
        lane: _metrics([row for row in rows if row.lane == lane])
        for lane in ("facebook", "reddit")
    }
    overall = _metrics(list(rows))
    semantic = {
        "as_of": as_of.isoformat(),
        "policy_hash": batch.policy_hash,
        "batch_hash": batch.batch_hash,
        "overall": overall.model_dump(mode="json"),
        "by_lane": {
            lane: metrics.model_dump(mode="json")
            for lane, metrics in sorted(by_lane.items())
        },
        "calibration_rows": [row.model_dump(mode="json") for row in rows],
    }

    return CommercialFunnelSnapshot(
        as_of=as_of,
        policy_hash=batch.policy_hash,
        batch_hash=batch.batch_hash,
        overall=overall,
        by_lane=by_lane,
        calibration_rows=rows,
        snapshot_hash=sha256_obj(semantic),
    )
