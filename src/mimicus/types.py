from __future__ import annotations

from enum import StrEnum


class Verdict(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"


class ClaimStatus(StrEnum):
    PROPOSED = "proposed"
    SUPPORTED = "supported"
    FALSIFIED = "falsified"
    INCONCLUSIVE = "inconclusive"
    WITHDRAWN = "withdrawn"


class MemoryStatus(StrEnum):
    CANDIDATE = "candidate"
    QUARANTINED = "quarantined"
    PRIVATE_VERIFIED = "private_verified"
    SHARED_VERIFIED = "shared_verified"
    REJECTED = "rejected"
    EXPIRED = "expired"


class BankruptcyState(StrEnum):
    ACTIVE = "ACTIVE"
    BANKRUPT = "BANKRUPT"
