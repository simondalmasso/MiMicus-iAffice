from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from uuid import uuid4


@dataclass(frozen=True)
class BudgetReservation:
    reservation_id: str
    category: str
    estimated_max_usd: float


class BudgetLedger:
    """One fail-closed monetary ledger shared by all paid work in a run.

    Known actual costs replace reservations. Unknown monetary costs keep their
    reservation locked so later paid work cannot spend the same capacity.
    """

    def __init__(self, hard_cap_usd: float) -> None:
        if hard_cap_usd < 0:
            raise ValueError("budget hard cap must be non-negative")
        self.hard_cap_usd = float(hard_cap_usd)
        self._lock = asyncio.Lock()
        self._active: dict[str, BudgetReservation] = {}
        self._actual_known_usd = 0.0
        self._unknown_locked_usd = 0.0
        self._overrun_usd = 0.0
        self._fail_closed = False
        self._by_category: dict[str, dict[str, float | int]] = {}

    def _category(self, category: str) -> dict[str, float | int]:
        return self._by_category.setdefault(
            category,
            {
                "estimated_max_usd": 0.0,
                "reserved_usd": 0.0,
                "actual_known_usd": 0.0,
                "unknown_cost_calls": 0,
                "reconciled_calls": 0,
                "cancelled_or_released_calls": 0,
            },
        )

    @property
    def outstanding_reserved_usd(self) -> float:
        return sum(row.estimated_max_usd for row in self._active.values())

    @property
    def committed_usd(self) -> float:
        return self._actual_known_usd + self._unknown_locked_usd + self.outstanding_reserved_usd

    @property
    def remaining_usd(self) -> float:
        return max(0.0, self.hard_cap_usd - self.committed_usd)

    @property
    def fail_closed(self) -> bool:
        return self._fail_closed

    async def reserve(self, category: str, estimated_max_usd: float | None, *, known_zero_cost: bool = False) -> BudgetReservation | None:
        async with self._lock:
            if self._fail_closed:
                return None
            if estimated_max_usd is None:
                if known_zero_cost:
                    estimate = 0.0
                else:
                    estimate = self.remaining_usd
                    if estimate <= 1e-12:
                        return None
            else:
                estimate = float(estimated_max_usd)
                if estimate < 0:
                    raise ValueError("estimated cost must be non-negative")
            if self.committed_usd + estimate > self.hard_cap_usd + 1e-12:
                return None
            reservation = BudgetReservation(str(uuid4()), category, estimate)
            self._active[reservation.reservation_id] = reservation
            row = self._category(category)
            row["estimated_max_usd"] = float(row["estimated_max_usd"]) + estimate
            row["reserved_usd"] = float(row["reserved_usd"]) + estimate
            return reservation

    async def reconcile(self, reservation: BudgetReservation, actual_cost_usd: float | None) -> dict[str, Any]:
        async with self._lock:
            active = self._active.pop(reservation.reservation_id, None)
            if active is None:
                raise ValueError("unknown or already reconciled budget reservation")
            row = self._category(active.category)
            row["reserved_usd"] = max(0.0, float(row["reserved_usd"]) - active.estimated_max_usd)
            row["reconciled_calls"] = int(row["reconciled_calls"]) + 1
            if actual_cost_usd is None:
                self._unknown_locked_usd += active.estimated_max_usd
                row["unknown_cost_calls"] = int(row["unknown_cost_calls"]) + 1
                return {"status": "UNKNOWN", "reservation_usd": active.estimated_max_usd, "remaining_usd": self.remaining_usd}
            actual = float(actual_cost_usd)
            if actual < 0:
                raise ValueError("actual cost must be non-negative")
            self._actual_known_usd += actual
            row["actual_known_usd"] = float(row["actual_known_usd"]) + actual
            if self.committed_usd > self.hard_cap_usd + 1e-12:
                self._overrun_usd = max(self._overrun_usd, self.committed_usd - self.hard_cap_usd)
                self._fail_closed = True
            return {
                "status": "KNOWN",
                "actual_usd": actual,
                "reservation_usd": active.estimated_max_usd,
                "provider_overrun_usd": max(0.0, actual - active.estimated_max_usd),
                "fail_closed": self._fail_closed,
                "remaining_usd": self.remaining_usd,
            }

    async def release(self, reservation: BudgetReservation, *, reason: str = "cancelled") -> dict[str, Any]:
        async with self._lock:
            active = self._active.pop(reservation.reservation_id, None)
            if active is None:
                return {"released": False, "reason": "already reconciled"}
            row = self._category(active.category)
            row["reserved_usd"] = max(0.0, float(row["reserved_usd"]) - active.estimated_max_usd)
            row["cancelled_or_released_calls"] = int(row["cancelled_or_released_calls"]) + 1
            return {"released": True, "reason": reason, "released_usd": active.estimated_max_usd, "remaining_usd": self.remaining_usd}

    def snapshot(self) -> dict[str, Any]:
        monetary_actual: float | str = self._actual_known_usd if self._unknown_locked_usd <= 1e-12 else "UNKNOWN"
        return {
            "limit_usd": self.hard_cap_usd,
            "estimated_or_reserved_usd": self.committed_usd,
            "outstanding_reserved_usd": self.outstanding_reserved_usd,
            "known_actual_usd": self._actual_known_usd,
            "actual_usd": monetary_actual,
            "unknown_cost_reserved_usd": self._unknown_locked_usd,
            "remaining_usd": self.remaining_usd,
            "provider_overrun_usd": self._overrun_usd,
            "fail_closed": self._fail_closed,
            "by_category": {key: dict(value) for key, value in sorted(self._by_category.items())},
        }
