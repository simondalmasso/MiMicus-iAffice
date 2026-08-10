from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


class EvidenceTag(str, Enum):
    LIVE_MAINNET = "LIVE_MAINNET"
    OFFICIAL_CODE = "OFFICIAL_CODE"
    OFFICIAL_DOC = "OFFICIAL_DOC"
    DERIVED = "DERIVED"
    SYNTHETIC_FIXTURE = "SYNTHETIC_FIXTURE"
    ASSUMPTION = "ASSUMPTION"
    UNKNOWN = "UNKNOWN"


class TopicClass(str, Enum):
    TRADING = "TRADING"
    NON_TRADING = "NON_TRADING"
    AMBIGUOUS = "AMBIGUOUS"
    UNKNOWN = "UNKNOWN"


class LifecycleState(str, Enum):
    CREATED = "CREATED"
    INACTIVE = "INACTIVE"
    ACTIVE = "ACTIVE"
    CHURNABLE = "CHURNABLE"
    WORKER_REQUEST = "WORKER_REQUEST"
    REPUTER_REQUEST = "REPUTER_REQUEST"
    REWARDABLE = "REWARDABLE"
    REWARD_DISTRIBUTED = "REWARD_DISTRIBUTED"


@dataclass(frozen=True)
class NetworkSpec:
    name: str
    chain_id: str
    deployed_version: str
    emissions_api: str
    rpc: str
    lcd: str
    grpc: str
    explorer: str


@dataclass
class Classification:
    classification: TopicClass
    reason: str
    evidence: list[str]
    confidence: str
    source_tag: EvidenceTag = EvidenceTag.DERIVED

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["classification"] = self.classification.value
        out["source_tag"] = self.source_tag.value
        return out


@dataclass
class TopicSnapshot:
    topic_id: int
    exists: bool
    active: bool | None
    metadata: str = ""
    creator: str = ""
    epoch_length: int | None = None
    ground_truth_lag: int | None = None
    worker_submission_window: int | None = None
    topic_type: str | None = None
    output_arity: str | None = None
    labels: list[str] = field(default_factory=list)
    worker_whitelist_enabled: bool | None = None
    reputer_whitelist_enabled: bool | None = None
    active_inferer_quantile: str | None = None
    active_forecaster_quantile: str | None = None
    active_reputer_quantile: str | None = None
    topic_stake: str | None = None
    delegated_stake: str | None = None
    fee_revenue: str | None = None
    effective_fee_revenue: str | None = None
    previous_weight: str | None = None
    weight: str | None = None
    worker_nonce: str | None = None
    reputer_nonce: str | None = None
    reward_nonce: str | None = None
    latest_network_inference: str | None = None
    latest_inference_block: int | None = None
    worker_count: int | None = None
    active_worker_count: int | None = None
    reputer_count: int | None = None
    forecaster_count: int | None = None
    next_churning_block: int | None = None
    worker_window_open: bool | None = None
    reputer_window_open: bool | None = None
    next_worker_window_start: int | None = None
    next_worker_window_end: int | None = None
    next_reputer_window_start: int | None = None
    next_reputer_window_end: int | None = None
    query_time_utc: str | None = None
    source_height: int | None = None
    source_tag: EvidenceTag = EvidenceTag.LIVE_MAINNET
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["source_tag"] = self.source_tag.value
        return out


@dataclass
class EligibilityDecision:
    topic_id: int
    eligible: bool
    checks: dict[str, bool | None]
    blockers: list[str]
    evidence: list[str]
    source_tag: EvidenceTag = EvidenceTag.DERIVED

    def to_dict(self) -> dict[str, Any]:
        out = asdict(self)
        out["source_tag"] = self.source_tag.value
        return out
