from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from .models import TopicClass


class TopicAdapter(Protocol):
    def request_context(self, topic_id: int) -> dict[str, Any]: ...


class DataSourceAdapter(Protocol):
    def fetch(self, context: dict[str, Any]) -> dict[str, Any]: ...


class ModelAdapter(Protocol):
    def infer(self, data: dict[str, Any]) -> Any: ...


class GroundTruthAdapter(Protocol):
    def ground_truth(self, context: dict[str, Any]) -> Any: ...


class LossAdapter(Protocol):
    def loss(self, inference: Any, truth: Any) -> float: ...


class RewardEstimator(Protocol):
    def estimate(self, loss: float, context: dict[str, Any]) -> dict[str, Any]: ...


@dataclass
class ShadowResult:
    run_id: str
    topic_id: int
    inference: Any
    inference_hash: str
    truth: Any
    loss: float
    reward_estimate: dict[str, Any]
    created_at: str
    submitted: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ShadowWorkerEngine:
    def run(
        self,
        *,
        topic_id: int,
        topic_class: TopicClass,
        topic_adapter: TopicAdapter,
        data_source: DataSourceAdapter,
        model: ModelAdapter,
        truth_adapter: GroundTruthAdapter,
        loss_adapter: LossAdapter,
        reward_estimator: RewardEstimator,
        persist: Any | None = None,
    ) -> ShadowResult:
        if topic_class == TopicClass.TRADING:
            raise RuntimeError("TRADING_MODEL_EXECUTION_PROHIBITED_BY_ORDER_001")
        if topic_class in (TopicClass.UNKNOWN, TopicClass.AMBIGUOUS):
            raise RuntimeError("SHADOW_EXECUTION_FAIL_CLOSED_UNCLASSIFIED_TOPIC")
        context = topic_adapter.request_context(topic_id)
        data = data_source.fetch(context)
        inference = model.infer(data)
        canonical = json.dumps(inference, sort_keys=True, separators=(",", ":"), default=str)
        digest = hashlib.sha256(canonical.encode()).hexdigest()
        truth = truth_adapter.ground_truth(context)
        loss = float(loss_adapter.loss(inference, truth))
        estimate = reward_estimator.estimate(loss, context)
        result = ShadowResult(
            run_id=str(uuid.uuid4()),
            topic_id=topic_id,
            inference=inference,
            inference_hash=digest,
            truth=truth,
            loss=loss,
            reward_estimate=estimate,
            created_at=datetime.now(timezone.utc).isoformat(),
            submitted=False,
        )
        if persist is not None:
            persist(result)
        return result


class AbsoluteErrorLoss:
    def loss(self, inference: Any, truth: Any) -> float:
        return abs(float(inference) - float(truth))
