from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from mimicus.events.ledger import EventLedger, LedgerEvent


def verify_replay(events: Sequence[LedgerEvent | dict[str, Any]], expected_head: str | None = None) -> dict[str, object]:
    ok, head = EventLedger.verify(events)
    if expected_head is not None and head != expected_head:
        return {"verified": False, "head": head, "reason": "snapshot/head mismatch"}
    return {"verified": ok, "head": head, "reason": None if ok else head}
