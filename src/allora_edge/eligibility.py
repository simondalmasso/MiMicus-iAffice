from __future__ import annotations

from .models import Classification, EligibilityDecision, TopicClass, TopicSnapshot


def evaluate_eligibility(
    topic: TopicSnapshot,
    classification: Classification,
    *,
    open_to_unknown_worker: bool | None,
    worker_requests_exist: bool | None,
    rewardable: bool | None,
    external_demand_evidence: bool | None,
    liquid_reward_mechanism: bool | None,
    entry_cost_under_100: bool | None,
) -> EligibilityDecision:
    checks: dict[str, bool | None] = {
        "EXISTS": topic.exists,
        "ACTIVE": topic.active,
        "NON_TRADING": classification.classification == TopicClass.NON_TRADING,
        "OPEN_TO_UNKNOWN_WORKER": open_to_unknown_worker,
        "WORKER_REQUESTS_EXIST": worker_requests_exist,
        "REWARDABLE": rewardable,
        "EXTERNAL_DEMAND_EVIDENCE": external_demand_evidence,
        "LIQUID_REWARD_MECHANISM": liquid_reward_mechanism,
        "ENTRY_COST_PLAUSIBLY_UNDER_100": entry_cost_under_100,
    }
    eligible = all(value is True for value in checks.values())
    blockers = [key for key, value in checks.items() if value is not True]
    return EligibilityDecision(
        topic_id=topic.topic_id,
        eligible=eligible,
        checks=checks,
        blockers=blockers,
        evidence=[classification.reason],
    )
