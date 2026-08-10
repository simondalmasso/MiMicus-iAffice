from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .classify import classify_topic
from .client import VersionAwareAlloraClient
from .economics import analyze_economics
from .eligibility import evaluate_eligibility
from .gate_evidence import GateEvidenceRegistry
from .lifecycle import transition_events
from .models import TopicClass
from .report import write_csv, write_json
from .storage import Storage


class Radar:
    def __init__(self, client: VersionAwareAlloraClient, storage: Storage, evidence_dir: Path, gate_registry: GateEvidenceRegistry | None = None, *, max_head_age_seconds: int = 900):
        self.client = client
        self.storage = storage
        self.evidence_dir = evidence_dir
        self.gate_registry = gate_registry or GateEvidenceRegistry()
        self.max_head_age_seconds = max_head_age_seconds

    def scan(self) -> dict[str, Any]:
        observed = datetime.now(timezone.utc).isoformat()
        network = self.client.verify_network()
        params = self.client.params()
        head = network.get("latest_block_height")
        if network.get("catching_up") is True:
            raise RuntimeError("RPC_CATCHING_UP_FAIL_CLOSED")
        if _head_is_stale(network.get("latest_block_time"), self.max_head_age_seconds):
            self.storage.add_incident(observed, "RPC_STALE_HEAD", "ERROR", {"latest_block_time": network.get("latest_block_time"), "max_age_seconds": self.max_head_age_seconds})
            raise RuntimeError("RPC_STALE_HEAD_FAIL_CLOSED")
        previous_head = self.storage.latest_network_height(self.client.spec.name)
        if previous_head is not None and head is not None and head < previous_head:
            self.storage.add_incident(observed, "CHAIN_HEAD_REGRESSION", "ERROR", {"previous_head": previous_head, "current_head": head})
            raise RuntimeError("CHAIN_HEAD_REGRESSION_FAIL_CLOSED")
        self.storage.put_network(observed, self.client.spec.name, self.client.spec.chain_id, head, network)
        next_id = self.client.next_topic_id()
        topics = []
        classes = []
        eligibility = []
        economics = []
        events = []

        for topic_id in range(1, next_id):
            try:
                current = self.client.census_topic(topic_id, head)
            except Exception as exc:
                self.storage.add_incident(observed, "TOPIC_READ_FAILED", "WARN", {"topic_id": topic_id, "error": str(exc)})
                continue
            previous = self.storage.latest_topic(topic_id)
            classification = classify_topic(current.metadata)
            # Both global and topic whitelist state matter. Arbitrary admission is proven only if both are explicitly disabled.
            global_wl = params.get("global_worker_whitelist_enabled")
            if current.worker_whitelist_enabled is True or global_wl is True:
                open_unknown = False
            elif current.worker_whitelist_enabled is False and global_wl is False:
                open_unknown = True
            else:
                open_unknown = None
            worker_requests = True if (current.worker_window_open is True or current.next_worker_window_start is not None) else None
            rewardable = current.reward_nonce not in (None, "0", 0)
            gate_ev = self.gate_registry.for_topic(topic_id)
            decision = evaluate_eligibility(
                current,
                classification,
                open_to_unknown_worker=open_unknown,
                worker_requests_exist=worker_requests,
                rewardable=rewardable,
                external_demand_evidence=gate_ev.external_demand_evidence,
                liquid_reward_mechanism=gate_ev.liquid_reward_mechanism,
                entry_cost_under_100=gate_ev.entry_cost_under_100,
            )
            ev = transition_events(previous, current)
            if classification.classification == TopicClass.NON_TRADING and (previous is None or classify_topic(previous.metadata).classification != TopicClass.NON_TRADING):
                ev.append("NEW_NON_TRADING_TOPIC")
            if decision.eligible:
                ev.extend(["QUALIFYING_TOPIC_FOUND", "OWNER_AUD_REVIEW_REQUIRED"])
            self.storage.put_topic(current, classification, decision, ev)
            topics.append(current.to_dict())
            classes.append({"topic_id": topic_id, **classification.to_dict()})
            eligibility.append(decision.to_dict())
            economics.append(analyze_economics(topic_id, fee_revenue=current.fee_revenue, effective_fee_revenue=current.effective_fee_revenue, topic_stake=current.topic_stake).to_dict())
            events.extend({"topic_id": topic_id, "event": e, "observed_at": observed} for e in ev)

        qualifying = [d for d in eligibility if d["eligible"]]
        self._export(observed, network, params, next_id, topics, classes, eligibility, economics, events, qualifying)
        return {
            "network": network,
            "next_topic_id": next_id,
            "topic_count": len(topics),
            "active_count": sum(1 for t in topics if t.get("active") is True),
            "non_trading_active_count": sum(1 for t, c in zip(topics, classes) if t.get("active") is True and c["classification"] == "NON_TRADING"),
            "eligible_count": len(qualifying),
            "events": events,
        }

    def _export(self, observed: str, network: dict[str, Any], params: dict[str, Any], next_id: int, topics: list[dict[str, Any]], classes: list[dict[str, Any]], eligibility: list[dict[str, Any]], economics: list[dict[str, Any]], events: list[dict[str, Any]], qualifying: list[dict[str, Any]]) -> None:
        write_json(self.evidence_dir / "run-metadata.json", {"order": "ORDER-001", "observed_at": observed, "source_tag": "LIVE_MAINNET" if self.client.spec.name == "mainnet" else "OFFICIAL_DOC", "transactions": 0, "spend_usd": 0})
        write_json(self.evidence_dir / "network.json", {"network": network, "params": params, "next_topic_id": next_id})
        write_json(self.evidence_dir / "topics.json", topics)
        write_json(self.evidence_dir / "incidents.json", events)
        write_json(self.evidence_dir / "QUALIFYING_TOPICS.json", qualifying)
        topic_fields = ["topic_id","exists","active","metadata","creator","epoch_length","ground_truth_lag","worker_submission_window","worker_whitelist_enabled","reputer_whitelist_enabled","topic_stake","fee_revenue","effective_fee_revenue","previous_weight","weight","reward_nonce","next_churning_block","query_time_utc","source_height","source_tag"]
        write_csv(self.evidence_dir / "topic-census.csv", topics, topic_fields)
        write_csv(self.evidence_dir / "classifications.csv", classes, ["topic_id","classification","reason","evidence","confidence","source_tag"])
        write_csv(self.evidence_dir / "eligibility.csv", eligibility, ["topic_id","eligible","checks","blockers","evidence","source_tag"])
        write_csv(self.evidence_dir / "economics.csv", economics, ["topic_id","fee_revenue","effective_fee_revenue","topic_stake","protocol_emissions","worker_rewards","customer_funded_component","emission_funded_component","external_demand_fraction","source_tag"])
        for name in ("workers.csv", "rewards.csv"):
            if not (self.evidence_dir / name).exists():
                write_csv(self.evidence_dir / name, [], ["topic_id","status","source_tag"])


def _head_is_stale(value: Any, max_age_seconds: int) -> bool:
    if not isinstance(value, str) or not value.strip():
        return False  # missing timestamp is surfaced as an evidence gap, not fabricated staleness
    raw = value.replace("Z", "+00:00")
    try:
        ts = datetime.fromisoformat(raw)
    except ValueError:
        return True
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - ts.astimezone(timezone.utc)).total_seconds()
    return age > max_age_seconds
