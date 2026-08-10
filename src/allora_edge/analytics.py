from __future__ import annotations

from decimal import Decimal, InvalidOperation
from math import isfinite
from statistics import median
from typing import Iterable


def _decimals(values: Iterable[str | int | float | Decimal | None]) -> list[Decimal]:
    out: list[Decimal] = []
    for value in values:
        if value is None:
            continue
        try:
            d = Decimal(str(value))
        except InvalidOperation:
            continue
        if d.is_finite():
            out.append(d)
    return out


def percentile(values: Iterable[str | int | float | Decimal | None], p: float) -> str | None:
    xs = sorted(_decimals(values))
    if not xs:
        return None
    if len(xs) == 1:
        return str(xs[0])
    pos = (len(xs) - 1) * p
    lo = int(pos)
    hi = min(lo + 1, len(xs) - 1)
    frac = Decimal(str(pos - lo))
    return str(xs[lo] + (xs[hi] - xs[lo]) * frac)


def concentration(rewards: Iterable[str | int | float | Decimal | None]) -> dict[str, str | float | int | None]:
    xs = _decimals(rewards)
    if not xs:
        return {"count": 0, "zero_reward_share": None, "top10_reward_share": None, "hhi": None, "p25": None, "p50": None, "p75": None}
    total = sum(xs, Decimal(0))
    zeros = sum(1 for x in xs if x == 0)
    shares = [(x / total) if total != 0 else Decimal(0) for x in xs]
    top10 = sum(sorted(shares, reverse=True)[:10], Decimal(0))
    hhi = sum((s * s for s in shares), Decimal(0))
    return {
        "count": len(xs),
        "zero_reward_share": float(Decimal(zeros) / Decimal(len(xs))),
        "top10_reward_share": float(top10),
        "hhi": float(hhi),
        "p25": percentile(xs, 0.25),
        "p50": percentile(xs, 0.50),
        "p75": percentile(xs, 0.75),
    }


def active_set_requirement(lowest_active_score: str | None, initial_score: str | None) -> dict[str, str | None]:
    return {
        "lowest_active_score": lowest_active_score,
        "cold_start_initial_score": initial_score,
        "minimum_observed_target": lowest_active_score,
    }
