from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


@dataclass
class RewardSimulationResult:
    would_be_active: bool | None
    would_be_rewarded: bool | None
    estimated_allo_reward: str | None
    confidence: str
    missing_inputs: list[str]
    method: str
    derived_topic_reward: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def canonical_topic_reward(*, topic_weight: str | None, sum_topic_weights: str | None, current_emission_per_block: str | None, epoch_length: int | None) -> str | None:
    """Deployed v0.16 main-path topic reward: (weight / total previous weights) * emission_per_block * epoch_length.

    Treasury-cap redistribution and MaxActiveTopicsPerBlock selection happen outside this helper; callers must not
    treat this value as final unless those conditions are also known.
    """
    if None in (topic_weight, sum_topic_weights, current_emission_per_block, epoch_length):
        return None
    try:
        w = Decimal(str(topic_weight)); total = Decimal(str(sum_topic_weights)); emission = Decimal(str(current_emission_per_block)); epoch = Decimal(int(epoch_length))
        if total <= 0 or epoch <= 0:
            return None
        return str((w / total) * emission * epoch)
    except (InvalidOperation, ValueError, TypeError):
        return None


def simulate_reward(
    *,
    our_score: str | None,
    lowest_active_score: str | None,
    topic_reward: str | None = None,
    our_reward_fraction: str | None = None,
    topic_weight: str | None = None,
    sum_topic_weights: str | None = None,
    current_emission_per_block: str | None = None,
    epoch_length: int | None = None,
) -> RewardSimulationResult:
    missing: list[str] = []
    active: bool | None = None
    if our_score is None:
        missing.append("our_score")
    if lowest_active_score is None:
        missing.append("lowest_active_score")
    if our_score is not None and lowest_active_score is not None:
        try:
            active = Decimal(our_score) >= Decimal(lowest_active_score)
        except InvalidOperation:
            missing.append("valid_score_decimals")

    derived = canonical_topic_reward(
        topic_weight=topic_weight, sum_topic_weights=sum_topic_weights,
        current_emission_per_block=current_emission_per_block, epoch_length=epoch_length,
    )
    effective_topic_reward = topic_reward if topic_reward is not None else derived

    estimated: str | None = None
    rewarded: bool | None = None
    if active is False:
        rewarded = False
        estimated = "0"
    elif active is True:
        if effective_topic_reward is None:
            missing.append("topic_reward_or_canonical_topic_reward_inputs")
        if our_reward_fraction is None:
            missing.append("our_reward_fraction")
        if effective_topic_reward is not None and our_reward_fraction is not None:
            try:
                estimated = str(Decimal(effective_topic_reward) * Decimal(our_reward_fraction))
                rewarded = Decimal(estimated) > 0
            except InvalidOperation:
                missing.append("valid_reward_decimals")

    # Even a derived main-path topic reward cannot be HIGH confidence without treasury-cap / rewardable-topic selection
    # and the participant fraction reconstructed from canonical participant reward code.
    confidence = "HIGH" if not missing and topic_reward is not None else ("MEDIUM" if active is not None else "LOW")
    return RewardSimulationResult(
        would_be_active=active,
        would_be_rewarded=rewarded,
        estimated_allo_reward=estimated,
        confidence=confidence,
        missing_inputs=sorted(set(missing)),
        method="v0.16 active-threshold check + explicit participant reward fraction; optional canonical main-path topic-reward formula; treasury cap/participant fractions are never imputed",
        derived_topic_reward=derived,
    )
