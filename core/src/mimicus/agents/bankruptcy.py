from __future__ import annotations

from dataclasses import dataclass

from mimicus.agents.calibration import CalibrationRecord
from mimicus.types import BankruptcyState


@dataclass
class BankruptcyRecord:
    fingerprint: str
    domain: str
    state: BankruptcyState = BankruptcyState.ACTIVE
    reason: str | None = None


def evaluate_bankruptcy(calibration: CalibrationRecord, trust_floor: float = 0.35) -> BankruptcyRecord:
    record = BankruptcyRecord(calibration.fingerprint, calibration.domain)
    if calibration.canary_failure_streak >= 3:
        record.state = BankruptcyState.BANKRUPT
        record.reason = "three consecutive verified domain audition failures"
    elif calibration.attempts >= 5 and calibration.trust < trust_floor:
        record.state = BankruptcyState.BANKRUPT
        record.reason = "direct verified domain trust below floor"
    return record


def recover(record: BankruptcyRecord, *, recovery_audition_passed: bool) -> BankruptcyRecord:
    if record.state == BankruptcyState.ACTIVE:
        return record
    if not recovery_audition_passed:
        return BankruptcyRecord(record.fingerprint, record.domain, record.state, "recovery audition required")
    return BankruptcyRecord(record.fingerprint, record.domain, BankruptcyState.ACTIVE, "recovery audition passed")
