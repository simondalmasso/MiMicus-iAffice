from __future__ import annotations

from dataclasses import dataclass

from .models import LifecycleState, TopicSnapshot


@dataclass(frozen=True)
class LifecycleObservation:
    state: LifecycleState
    reasons: tuple[str, ...]


def infer_lifecycle(topic: TopicSnapshot) -> LifecycleObservation:
    if not topic.exists:
        return LifecycleObservation(LifecycleState.CREATED, ("topic not yet observable",))
    if topic.active is not True:
        return LifecycleObservation(LifecycleState.INACTIVE, ("is_topic_active != true",))
    if topic.reward_nonce not in (None, "0", 0):
        return LifecycleObservation(LifecycleState.REWARDABLE, ("non-zero reward nonce",))
    if topic.reputer_window_open is True:
        return LifecycleObservation(LifecycleState.REPUTER_REQUEST, ("reputer submission window open",))
    if topic.worker_window_open is True:
        return LifecycleObservation(LifecycleState.WORKER_REQUEST, ("worker submission window open",))
    if topic.next_churning_block is not None:
        return LifecycleObservation(LifecycleState.CHURNABLE, ("next churning block known",))
    return LifecycleObservation(LifecycleState.ACTIVE, ("topic active",))


def transition_events(previous: TopicSnapshot | None, current: TopicSnapshot) -> list[str]:
    if previous is None:
        return ["NEW_TOPIC"]
    events: list[str] = []
    if previous.active is not True and current.active is True:
        events.append("TOPIC_ACTIVATED")
    if previous.active is True and current.active is not True:
        events.append("TOPIC_DEACTIVATED")
    if previous.worker_whitelist_enabled != current.worker_whitelist_enabled:
        events.append("WORKER_WHITELIST_CHANGED")
    if previous.fee_revenue != current.fee_revenue:
        events.append("FEE_REVENUE_CHANGED")
    if previous.next_churning_block != current.next_churning_block and current.next_churning_block is not None:
        events.append("TOPIC_NOW_CHURNABLE")
    if previous.reward_nonce != current.reward_nonce and current.reward_nonce not in (None, "0", 0):
        events.append("TOPIC_REWARDABLE")
    return events
