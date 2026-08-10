from __future__ import annotations

from datetime import datetime, timezone
import time
from typing import Any

from .config import NETWORKS
from .http import HttpResult, ReadOnlyHttpClient
from .models import EvidenceTag, NetworkSpec, TopicSnapshot


class SchemaMismatch(RuntimeError):
    pass


class VersionAwareAlloraClient:
    def __init__(self, network: str = "mainnet", http: ReadOnlyHttpClient | None = None):
        if network not in NETWORKS:
            raise ValueError(f"unknown network: {network}")
        self.spec: NetworkSpec = NETWORKS[network]
        self.http = http or ReadOnlyHttpClient()

    @property
    def api_root(self) -> str:
        return f"{self.spec.lcd}/emissions/{self.spec.emissions_api}"

    def _get(self, path: str) -> HttpResult:
        return self.http.get(f"{self.api_root}/{path.lstrip('/')}")

    def status(self) -> dict[str, Any]:
        # Public RPC can sit behind intermediary caches; a read-only cache-buster prevents stale status reuse.
        return self.http.get(f"{self.spec.rpc}/status?order001_ts={time.time_ns()}").data

    def verify_network(self) -> dict[str, Any]:
        status = self.status()
        result = status.get("result") or {}
        node = result.get("node_info") or {}
        sync = result.get("sync_info") or {}
        actual = node.get("network")
        if actual != self.spec.chain_id:
            raise SchemaMismatch(f"chain id mismatch: expected {self.spec.chain_id}, got {actual}")
        return {
            "network": self.spec.name,
            "chain_id": actual,
            "deployed_version_expected": self.spec.deployed_version,
            "emissions_api": self.spec.emissions_api,
            "cometbft_version": node.get("version"),
            "latest_block_height": _int_or_none(sync.get("latest_block_height")),
            "latest_block_time": sync.get("latest_block_time"),
            "earliest_block_height": _int_or_none(sync.get("earliest_block_height")),
            "earliest_block_time": sync.get("earliest_block_time"),
            "catching_up": sync.get("catching_up"),
        }

    def params(self) -> dict[str, Any]:
        data = self._get("params").data
        if not isinstance(data.get("params"), dict):
            raise SchemaMismatch("params missing")
        return data["params"]

    def next_topic_id(self) -> int:
        data = self._get("next_topic_id").data
        try:
            return int(data["next_topic_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise SchemaMismatch("next_topic_id missing or malformed") from exc

    def topic_exists(self, topic_id: int) -> bool:
        data = self._get(f"topic_exists/{topic_id}").data
        return bool(data.get("exists", data.get("topic_exists", False)))

    def is_topic_active(self, topic_id: int) -> bool:
        data = self._get(f"is_topic_active/{topic_id}").data
        return bool(data.get("is_active", False))

    def topic(self, topic_id: int) -> dict[str, Any]:
        data = self._get(f"topics/{topic_id}").data
        if not isinstance(data.get("topic"), dict):
            raise SchemaMismatch(f"topic {topic_id} malformed")
        return data

    def worker_whitelist_enabled(self, topic_id: int) -> bool | None:
        data = self._get(f"is_topic_worker_whitelist_enabled/{topic_id}").data
        value = data.get("is_topic_worker_whitelist_enabled")
        return value if isinstance(value, bool) else None

    def reputer_whitelist_enabled(self, topic_id: int) -> bool | None:
        data = self._get(f"is_topic_reputer_whitelist_enabled/{topic_id}").data
        value = data.get("is_topic_reputer_whitelist_enabled")
        return value if isinstance(value, bool) else None

    def fee_revenue(self, topic_id: int) -> str | None:
        data = self._get(f"topic_fee_revenue/{topic_id}").data
        for key in ("fee_revenue", "topic_fee_revenue"):
            if key in data:
                return str(data[key])
        return None

    def previous_weight(self, topic_id: int) -> str | None:
        data = self._get(f"previous_topic_weight/{topic_id}").data
        for key in ("weight", "previous_topic_weight"):
            if key in data:
                return str(data[key])
        return None

    def reward_nonce(self, topic_id: int) -> str | None:
        data = self._get(f"topic_reward_nonce/{topic_id}").data
        value = data.get("nonce")
        return None if value is None else str(value)

    def next_churning_block(self, topic_id: int) -> int | None:
        data = self._get(f"next_churning_block_by_topic_id/{topic_id}").data
        for key in ("block_height", "next_churning_block"):
            if key in data:
                return _int_or_none(data[key])
        return None

    def worker_window_status(self, topic_id: int) -> dict[str, Any]:
        return self._get(f"worker_submission_window_status/{topic_id}").data

    def reputer_window_status(self, topic_id: int) -> dict[str, Any]:
        return self._get(f"reputer_submission_window_status/{topic_id}").data

    def latest_network_inferences(self, topic_id: int) -> dict[str, Any]:
        return self._get(f"latest_network_inferences/{topic_id}").data

    def active_topics_at_block(self, block_height: int) -> dict[str, Any]:
        return self._get(f"active_topics_at_block/{block_height}").data

    def lowest_scores(self, topic_id: int) -> dict[str, str | None]:
        out: dict[str, str | None] = {}
        for role, route in (
            ("inferer", "current_lowest_inferer_score"),
            ("forecaster", "current_lowest_forecaster_score"),
            ("reputer", "current_lowest_reputer_score"),
        ):
            data = self._get(f"{route}/{topic_id}").data
            value = data.get("score")
            if isinstance(value, dict):
                value = value.get("score") or value.get("value")
            out[role] = None if value is None else str(value)
        return out

    def census_topic(self, topic_id: int, source_height: int | None = None) -> TopicSnapshot:
        if not self.topic_exists(topic_id):
            return TopicSnapshot(
                topic_id=topic_id, exists=False, active=False, query_time_utc=datetime.now(timezone.utc).isoformat(),
                source_height=source_height, source_tag=EvidenceTag.LIVE_MAINNET if self.spec.name == "mainnet" else EvidenceTag.OFFICIAL_DOC,
            )
        envelope = self.topic(topic_id)
        topic = envelope["topic"]
        active = self.is_topic_active(topic_id)
        worker_wl = self._optional(lambda: self.worker_whitelist_enabled(topic_id))
        reputer_wl = self._optional(lambda: self.reputer_whitelist_enabled(topic_id))
        fee = self._optional(lambda: self.fee_revenue(topic_id))
        prev = self._optional(lambda: self.previous_weight(topic_id))
        nonce = self._optional(lambda: self.reward_nonce(topic_id))
        churn = self._optional(lambda: self.next_churning_block(topic_id))
        worker_window = self._optional(lambda: self.worker_window_status(topic_id))
        reputer_window = self._optional(lambda: self.reputer_window_status(topic_id))
        network_inference = self._optional(lambda: self.latest_network_inferences(topic_id)) if active else None
        latest_value, latest_block = _network_inference_summary(network_inference)
        return TopicSnapshot(
            topic_id=topic_id,
            exists=True,
            active=active,
            metadata=str(topic.get("metadata", "")),
            creator=str(topic.get("creator", "")),
            epoch_length=_int_or_none(topic.get("epoch_length")),
            ground_truth_lag=_int_or_none(topic.get("ground_truth_lag")),
            worker_submission_window=_int_or_none(topic.get("worker_submission_window")),
            topic_type=_str_or_none(topic.get("topic_type")),
            output_arity=_str_or_none(topic.get("output_arity")),
            labels=list(topic.get("label_whitelist") or []),
            worker_whitelist_enabled=worker_wl,
            reputer_whitelist_enabled=reputer_wl,
            active_inferer_quantile=_str_or_none(topic.get("active_inferer_quantile")),
            active_forecaster_quantile=_str_or_none(topic.get("active_forecaster_quantile")),
            active_reputer_quantile=_str_or_none(topic.get("active_reputer_quantile")),
            topic_stake=_str_or_none(envelope.get("topic_stake")),
            effective_fee_revenue=_str_or_none(envelope.get("effective_revenue")),
            fee_revenue=fee,
            previous_weight=prev,
            weight=_str_or_none(envelope.get("weight")),
            worker_nonce=_window_nonce(worker_window),
            reputer_nonce=_window_nonce(reputer_window),
            reward_nonce=nonce,
            latest_network_inference=latest_value,
            latest_inference_block=latest_block,
            next_churning_block=churn,
            worker_window_open=_window_open(worker_window),
            reputer_window_open=_window_open(reputer_window),
            next_worker_window_start=_window_int(worker_window, "next_window_start_block"),
            next_worker_window_end=_window_int(worker_window, "next_window_end_block"),
            next_reputer_window_start=_window_int(reputer_window, "next_window_start_block"),
            next_reputer_window_end=_window_int(reputer_window, "next_window_end_block"),
            query_time_utc=datetime.now(timezone.utc).isoformat(),
            source_height=source_height,
            raw=envelope,
        )

    @staticmethod
    def _optional(fn):
        try:
            return fn()
        except Exception:
            return None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _str_or_none(value: Any) -> str | None:
    return None if value is None else str(value)


def _window_open(value: Any) -> bool | None:
    if not isinstance(value, dict):
        return None
    for key in ("is_open", "open", "is_window_open"):
        if isinstance(value.get(key), bool):
            return value[key]
    return None


def _window_int(value: Any, key: str) -> int | None:
    if not isinstance(value, dict):
        return None
    return _int_or_none(value.get(key))


def _window_nonce(value: Any) -> str | None:
    if not isinstance(value, dict):
        return None
    raw = value.get("current_nonce_block_height")
    if raw in (None, "0", 0):
        return None
    return str(raw)


def _network_inference_summary(value: Any) -> tuple[str | None, int | None]:
    if not isinstance(value, dict):
        return None, None
    bundle = value.get("network_inferences") or value.get("network_inference") or value.get("network_inference_bundle")
    if not isinstance(bundle, dict):
        return None, None
    combined = bundle.get("combined_value")
    if isinstance(combined, (dict, list)):
        import json
        combined_s = json.dumps(combined, sort_keys=True, separators=(",", ":"))
    else:
        combined_s = None if combined is None else str(combined)
    height = _int_or_none(bundle.get("nonce") or bundle.get("block_height"))
    if height is None:
        rrn = bundle.get("reputer_request_nonce")
        if isinstance(rrn, dict):
            rn = rrn.get("reputer_nonce")
            if isinstance(rn, dict):
                height = _int_or_none(rn.get("block_height"))
    return combined_s, height
