from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .config import SCHEMA_VERSION
from .models import Classification, EligibilityDecision, TopicSnapshot

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS network_snapshots(id INTEGER PRIMARY KEY, observed_at TEXT NOT NULL, network TEXT NOT NULL, chain_id TEXT, block_height INTEGER, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS topics(topic_id INTEGER PRIMARY KEY, first_seen TEXT NOT NULL, last_seen TEXT NOT NULL, metadata TEXT, creator TEXT);
CREATE TABLE IF NOT EXISTS topic_snapshots(id INTEGER PRIMARY KEY, topic_id INTEGER NOT NULL, observed_at TEXT NOT NULL, source_height INTEGER, active INTEGER, payload TEXT NOT NULL, UNIQUE(topic_id, observed_at));
CREATE TABLE IF NOT EXISTS topic_transitions(id INTEGER PRIMARY KEY, topic_id INTEGER NOT NULL, observed_at TEXT NOT NULL, event TEXT NOT NULL, old_state TEXT, new_state TEXT);
CREATE TABLE IF NOT EXISTS workers(id INTEGER PRIMARY KEY, topic_id INTEGER NOT NULL, address TEXT NOT NULL, role TEXT NOT NULL, observed_at TEXT NOT NULL, payload TEXT, UNIQUE(topic_id,address,role,observed_at));
CREATE TABLE IF NOT EXISTS worker_scores(id INTEGER PRIMARY KEY, topic_id INTEGER NOT NULL, address TEXT, role TEXT, block_height INTEGER, score TEXT, observed_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS inferences(id INTEGER PRIMARY KEY, topic_id INTEGER NOT NULL, actor TEXT, block_height INTEGER, value TEXT, observed_at TEXT NOT NULL, payload TEXT);
CREATE TABLE IF NOT EXISTS reward_epochs(id INTEGER PRIMARY KEY, topic_id INTEGER NOT NULL, block_height INTEGER, observed_at TEXT NOT NULL, payload TEXT);
CREATE TABLE IF NOT EXISTS classification_evidence(id INTEGER PRIMARY KEY, topic_id INTEGER NOT NULL, observed_at TEXT NOT NULL, classification TEXT NOT NULL, confidence TEXT NOT NULL, reason TEXT NOT NULL, evidence TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS eligibility_decisions(id INTEGER PRIMARY KEY, topic_id INTEGER NOT NULL, observed_at TEXT NOT NULL, eligible INTEGER NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS shadow_runs(id TEXT PRIMARY KEY, topic_id INTEGER NOT NULL, created_at TEXT NOT NULL, status TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS shadow_inferences(id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, inference_hash TEXT NOT NULL, value TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ground_truth(id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, value TEXT NOT NULL, observed_at TEXT NOT NULL, loss TEXT);
CREATE TABLE IF NOT EXISTS economics(id INTEGER PRIMARY KEY, topic_id INTEGER NOT NULL, observed_at TEXT NOT NULL, payload TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS incidents(id INTEGER PRIMARY KEY, observed_at TEXT NOT NULL, code TEXT NOT NULL, severity TEXT NOT NULL, payload TEXT NOT NULL);
"""


class Storage:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript(SCHEMA)
        self.db.execute("INSERT OR REPLACE INTO meta(key,value) VALUES('schema_version',?)", (str(SCHEMA_VERSION),))
        self.db.commit()

    def close(self) -> None:
        self.db.close()

    def latest_network_height(self, network: str) -> int | None:
        row = self.db.execute("SELECT block_height FROM network_snapshots WHERE network=? ORDER BY id DESC LIMIT 1", (network,)).fetchone()
        return None if row is None else row["block_height"]

    def put_network(self, observed_at: str, network: str, chain_id: str, block_height: int | None, payload: dict[str, Any]) -> None:
        self.db.execute("INSERT INTO network_snapshots(observed_at,network,chain_id,block_height,payload) VALUES(?,?,?,?,?)", (observed_at, network, chain_id, block_height, _json(payload)))
        self.db.commit()

    def latest_topic(self, topic_id: int) -> TopicSnapshot | None:
        row = self.db.execute("SELECT payload FROM topic_snapshots WHERE topic_id=? ORDER BY id DESC LIMIT 1", (topic_id,)).fetchone()
        if not row:
            return None
        return _topic_from_json(row["payload"])

    def put_topic(self, topic: TopicSnapshot, classification: Classification, eligibility: EligibilityDecision, events: list[str]) -> None:
        observed = topic.query_time_utc or "UNKNOWN"
        self.db.execute(
            "INSERT INTO topics(topic_id,first_seen,last_seen,metadata,creator) VALUES(?,?,?,?,?) ON CONFLICT(topic_id) DO UPDATE SET last_seen=excluded.last_seen,metadata=excluded.metadata,creator=excluded.creator",
            (topic.topic_id, observed, observed, topic.metadata, topic.creator),
        )
        self.db.execute(
            "INSERT OR IGNORE INTO topic_snapshots(topic_id,observed_at,source_height,active,payload) VALUES(?,?,?,?,?)",
            (topic.topic_id, observed, topic.source_height, int(topic.active) if topic.active is not None else None, _json(topic.to_dict())),
        )
        self.db.execute(
            "INSERT INTO classification_evidence(topic_id,observed_at,classification,confidence,reason,evidence) VALUES(?,?,?,?,?,?)",
            (topic.topic_id, observed, classification.classification.value, classification.confidence, classification.reason, _json(classification.evidence)),
        )
        self.db.execute(
            "INSERT INTO eligibility_decisions(topic_id,observed_at,eligible,payload) VALUES(?,?,?,?)",
            (topic.topic_id, observed, int(eligibility.eligible), _json(eligibility.to_dict())),
        )
        for event in events:
            self.db.execute(
                "INSERT INTO topic_transitions(topic_id,observed_at,event,old_state,new_state) VALUES(?,?,?,?,?)",
                (topic.topic_id, observed, event, None, None),
            )
        self.db.commit()

    def put_shadow_result(self, result: Any) -> None:
        payload = result.to_dict() if hasattr(result, "to_dict") else dict(result)
        run_id = str(payload["run_id"]); topic_id = int(payload["topic_id"]); created = str(payload["created_at"])
        self.db.execute("INSERT OR REPLACE INTO shadow_runs(id,topic_id,created_at,status,payload) VALUES(?,?,?,?,?)", (run_id,topic_id,created,"COMPLETE",_json(payload)))
        self.db.execute("INSERT INTO shadow_inferences(run_id,inference_hash,value,created_at) VALUES(?,?,?,?)", (run_id,str(payload["inference_hash"]),_json(payload.get("inference")),created))
        if payload.get("truth") is not None:
            self.db.execute("INSERT INTO ground_truth(run_id,value,observed_at,loss) VALUES(?,?,?,?)", (run_id,_json(payload.get("truth")),created,str(payload.get("loss"))))
        self.db.commit()

    def add_incident(self, observed_at: str, code: str, severity: str, payload: dict[str, Any]) -> None:
        self.db.execute("INSERT INTO incidents(observed_at,code,severity,payload) VALUES(?,?,?,?)", (observed_at, code, severity, _json(payload)))
        self.db.commit()

    def topic_rows(self) -> list[dict[str, Any]]:
        rows = self.db.execute("SELECT payload FROM topic_snapshots WHERE id IN (SELECT MAX(id) FROM topic_snapshots GROUP BY topic_id) ORDER BY topic_id").fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def eligibility_rows(self) -> list[dict[str, Any]]:
        rows = self.db.execute("SELECT payload FROM eligibility_decisions WHERE id IN (SELECT MAX(id) FROM eligibility_decisions GROUP BY topic_id) ORDER BY topic_id").fetchall()
        return [json.loads(row["payload"]) for row in rows]

    def health(self) -> dict[str, Any]:
        net = self.db.execute("SELECT * FROM network_snapshots ORDER BY id DESC LIMIT 1").fetchone()
        topic_count = self.db.execute("SELECT COUNT(*) c FROM topics").fetchone()["c"]
        active_count = self.db.execute("SELECT COUNT(*) c FROM topic_snapshots t JOIN (SELECT topic_id,MAX(id) max_id FROM topic_snapshots GROUP BY topic_id) latest ON t.id=latest.max_id WHERE t.active=1").fetchone()["c"]
        eligible_count = self.db.execute("SELECT COUNT(*) c FROM eligibility_decisions e JOIN (SELECT topic_id,MAX(id) max_id FROM eligibility_decisions GROUP BY topic_id) latest ON e.id=latest.max_id WHERE e.eligible=1").fetchone()["c"]
        return {
            "schema_version": SCHEMA_VERSION,
            "topic_count": topic_count,
            "active_count": active_count,
            "eligible_count": eligible_count,
            "last_block": None if net is None else net["block_height"],
            "last_successful_scan": None if net is None else net["observed_at"],
            "ready": net is not None,
        }


def _json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _topic_from_json(raw: str) -> TopicSnapshot:
    data = json.loads(raw)
    data.pop("source_tag", None)
    return TopicSnapshot(**data)
