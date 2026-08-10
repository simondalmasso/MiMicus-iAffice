from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .models import TopicClass
from .shadow import AbsoluteErrorLoss, ShadowWorkerEngine


class _Topic:
    def request_context(self, topic_id: int) -> dict[str, Any]:
        return {"topic_id": topic_id, "fixture": "SYNTHETIC_TEST_FIXTURE"}


class _Data:
    def __init__(self, payload: dict[str, Any]): self.payload = payload
    def fetch(self, context: dict[str, Any]) -> dict[str, Any]: return dict(self.payload["input"])


class _Model:
    def infer(self, data: dict[str, Any]) -> float:
        # Deliberately non-financial deterministic fixture: charger availability fraction.
        return float(data["available_chargers"]) / float(data["total_chargers"])


class _Truth:
    def __init__(self, payload: dict[str, Any]): self.payload = payload
    def ground_truth(self, context: dict[str, Any]) -> float: return float(self.payload["ground_truth"])


class _Reward:
    def estimate(self, loss: float, context: dict[str, Any]) -> dict[str, Any]:
        return {"would_be_active": None, "would_be_rewarded": None, "estimated_allo_reward": None, "confidence": "LOW", "missing_inputs": ["LIVE_TOPIC_REWARD_DATA"], "source_tag": "SYNTHETIC_FIXTURE"}


def run_synthetic_demo(path: Path, persist=None) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("source_tag") != "SYNTHETIC_TEST_FIXTURE" or raw.get("economic_evidence") is not False:
        raise RuntimeError("FIXTURE_MUST_BE_SYNTHETIC_AND_NOT_ECONOMIC_EVIDENCE")
    result = ShadowWorkerEngine().run(
        topic_id=int(raw["topic_id"]), topic_class=TopicClass.NON_TRADING,
        topic_adapter=_Topic(), data_source=_Data(raw), model=_Model(), truth_adapter=_Truth(raw),
        loss_adapter=AbsoluteErrorLoss(), reward_estimator=_Reward(), persist=persist,
    )
    out = result.to_dict(); out["source_tag"] = "SYNTHETIC_FIXTURE"; out["economic_evidence"] = False
    return out
