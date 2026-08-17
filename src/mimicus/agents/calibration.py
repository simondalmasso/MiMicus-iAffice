from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mimicus.storage.repository import Repository


@dataclass
class CalibrationRecord:
    fingerprint: str
    domain: str
    attempts: int = 0
    successes: int = 0
    failures: int = 0
    brier_sum: float = 0.0
    canary_failure_streak: int = 0
    last_verified_at: datetime | None = None

    @property
    def brier_score(self) -> float | None:
        return self.brier_sum / self.attempts if self.attempts else None

    @property
    def trust(self) -> float:
        if self.attempts < 3:
            return 0.5
        return self.successes / self.attempts

    def update(self, *, predicted_probability: float, outcome: bool, canary: bool = False) -> None:
        p = min(1.0, max(0.0, predicted_probability))
        y = 1.0 if outcome else 0.0
        self.attempts += 1
        self.successes += int(outcome)
        self.failures += int(not outcome)
        self.brier_sum += (p - y) ** 2
        if canary:
            self.canary_failure_streak = 0 if outcome else self.canary_failure_streak + 1
        self.last_verified_at = datetime.now(UTC)


class CalibrationLedger:
    def __init__(self, repository: Repository | None = None) -> None:
        self.repository = repository
        self._records: dict[tuple[str, str], CalibrationRecord] = {}

    def get(self, fingerprint: str, domain: str) -> CalibrationRecord:
        key = (fingerprint, domain)
        if self.repository is not None:
            row = self.repository.calibration(fingerprint, domain)
            last = datetime.fromisoformat(str(row["last_verified_at"])) if row["last_verified_at"] else None
            return CalibrationRecord(
                fingerprint=fingerprint,
                domain=domain,
                attempts=int(row["attempts"]),
                successes=int(row["successes"]),
                failures=int(row["failures"]),
                brier_sum=float(row["brier_sum"]),
                canary_failure_streak=int(row["canary_failure_streak"]),
                last_verified_at=last,
            )
        if key not in self._records:
            self._records[key] = CalibrationRecord(fingerprint, domain)
        return self._records[key]

    def record_verified(self, fingerprint: str, domain: str, *, predicted_probability: float, outcome: bool, canary: bool = False) -> CalibrationRecord:
        if self.repository is None:
            record = self.get(fingerprint, domain)
            record.update(predicted_probability=predicted_probability, outcome=outcome, canary=canary)
            return record
        self.repository.record_calibration(
            fingerprint,
            domain,
            predicted_probability=predicted_probability,
            outcome=outcome,
            canary=canary,
        )
        return self.get(fingerprint, domain)

    def direct_trust(self, fingerprint: str, domain: str) -> float:
        return self.get(fingerprint, domain).trust
