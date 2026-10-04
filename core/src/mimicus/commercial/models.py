from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator


class LeadDisposition(StrEnum):
    WORK_NOW = "WORK_NOW"
    HOLD = "HOLD"
    REPAIR_DATA = "REPAIR_DATA"
    REJECT = "REJECT"


class LeadStage(StrEnum):
    REPLIED = "replied"
    PREPARED = "prepared"
    CONTACTED_DUE = "contacted_due"
    CONTACTED_WAITING = "contacted_waiting"
    TERMINAL = "terminal"
    UNKNOWN = "unknown"


class LeadCandidate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    prospect_id: str = Field(min_length=1)
    source_name: str = Field(min_length=1)
    lane: Literal["facebook", "reddit"]
    buyer: str | None = None
    title: str = Field(min_length=1)
    active: bool
    argentina_eligible: bool | None
    worker_fee: bool | None
    scam_risk: Literal["low", "medium", "high"]
    setter_score: float = Field(ge=0.0, le=100.0)
    outreach_status: str = Field(min_length=1)
    outreach_channel: str | None = None
    published_at: datetime
    verified_at: datetime
    contacted_at: datetime | None = None
    source_url: str | None = None
    direct_url: str | None = None

    @field_validator("published_at", "verified_at", "contacted_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("datetime must include timezone information")
        return value


class LeadDecisionPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = Field(default="lead-policy-v1", min_length=1)
    max_work_per_lane: int = Field(default=3, ge=1)
    prepared_min_score: float = Field(default=0.0, ge=0.0, le=100.0)
    follow_up_after_hours: Mapping[str, int]
    stage_precedence: tuple[LeadStage, ...] = (
        LeadStage.REPLIED,
        LeadStage.PREPARED,
        LeadStage.CONTACTED_DUE,
        LeadStage.CONTACTED_WAITING,
    )
    reject_high_scam: bool = True
    reject_worker_fee: bool = True
    require_argentina_eligible: bool = True

    @field_validator("follow_up_after_hours")
    @classmethod
    def validate_follow_up_hours(cls, value: Mapping[str, int]) -> Mapping[str, int]:
        normalized = {str(channel): int(hours) for channel, hours in value.items()}
        if any(not channel.strip() for channel in normalized):
            raise ValueError("follow-up channel must be non-empty")
        if any(hours < 0 for hours in normalized.values()):
            raise ValueError("follow-up hours must be non-negative")
        return MappingProxyType(dict(sorted(normalized.items())))

    @field_serializer("follow_up_after_hours")
    def serialize_follow_up_hours(self, value: Mapping[str, int]) -> dict[str, int]:
        return dict(value)


class LeadDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    prospect_id: str = Field(min_length=1)
    lane: Literal["facebook", "reddit"]
    disposition: LeadDisposition
    stage: LeadStage
    rank_position: int | None = Field(default=None, ge=1)
    reasons: tuple[str, ...] = ()
    data_quality_issues: tuple[str, ...] = ()
    input_hash: str = Field(min_length=64, max_length=64)
    policy_hash: str = Field(min_length=64, max_length=64)
    decision_hash: str = Field(min_length=64, max_length=64)


class LeadDecisionBatch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    input_ids: tuple[str, ...]
    decisions: tuple[LeadDecision, ...]
    selected_by_lane: Mapping[str, tuple[str, ...]]
    held_ids: tuple[str, ...]
    rejected_ids: tuple[str, ...]
    repair_data_ids: tuple[str, ...]
    policy_hash: str = Field(min_length=64, max_length=64)
    batch_hash: str = Field(min_length=64, max_length=64)

    @field_validator("selected_by_lane")
    @classmethod
    def freeze_selected_by_lane(
        cls,
        value: Mapping[str, tuple[str, ...]],
    ) -> Mapping[str, tuple[str, ...]]:
        return MappingProxyType(dict(sorted(value.items())))

    @field_serializer("selected_by_lane")
    def serialize_selected_by_lane(
        self,
        value: Mapping[str, tuple[str, ...]],
    ) -> dict[str, tuple[str, ...]]:
        return dict(value)


class CommercialTraceEvent(BaseModel):
    """Sanitized observable event; never carries hidden chain-of-thought."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    sequence: int = Field(ge=1)
    event: Literal["lead_ingested", "laya_reading", "decision_emitted"]
    as_of: datetime
    prospect_id: str = Field(min_length=1)
    lane: Literal["facebook", "reddit"]
    source_name: str | None = None
    outreach_status: str | None = None
    setter_score: float | None = Field(default=None, ge=0.0, le=100.0)
    scam_risk: Literal["low", "medium", "high"] | None = None
    active: bool | None = None
    policy_version: str | None = None
    disposition: LeadDisposition | None = None
    stage: LeadStage | None = None
    rank_position: int | None = Field(default=None, ge=1)
    reasons: tuple[str, ...] = ()
    data_quality_issues: tuple[str, ...] = ()

    @field_validator("as_of")
    @classmethod
    def require_trace_timezone(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("trace as_of must include timezone information")
        return value
