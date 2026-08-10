from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


@dataclass
class EconomicsResult:
    topic_id: int
    fee_revenue: str | None
    effective_fee_revenue: str | None
    topic_stake: str | None
    protocol_emissions: str | None
    worker_rewards: str | None
    customer_funded_component: str | None
    emission_funded_component: str | None
    external_demand_fraction: str
    source_tag: str = "DERIVED"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def analyze_economics(
    topic_id: int,
    *,
    fee_revenue: str | None,
    effective_fee_revenue: str | None,
    topic_stake: str | None,
    protocol_emissions: str | None = None,
    worker_rewards: str | None = None,
    customer_funded_component: str | None = None,
    emission_funded_component: str | None = None,
) -> EconomicsResult:
    fraction = "UNKNOWN"
    if customer_funded_component is not None and emission_funded_component is not None:
        try:
            c = Decimal(customer_funded_component)
            e = Decimal(emission_funded_component)
            if c + e > 0:
                fraction = str(c / (c + e))
        except InvalidOperation:
            fraction = "UNKNOWN"
    return EconomicsResult(
        topic_id=topic_id,
        fee_revenue=fee_revenue,
        effective_fee_revenue=effective_fee_revenue,
        topic_stake=topic_stake,
        protocol_emissions=protocol_emissions,
        worker_rewards=worker_rewards,
        customer_funded_component=customer_funded_component,
        emission_funded_component=emission_funded_component,
        external_demand_fraction=fraction,
    )
