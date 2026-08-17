from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from mimicus.canonical import canonical_json, sha256_text


class LedgerEvent(BaseModel):
    model_config = ConfigDict(frozen=True)

    sequence: int
    event_id: str
    run_id: str
    event_type: str
    timestamp: datetime
    payload: dict[str, Any] = Field(default_factory=dict)
    prev_event_hash: str
    event_hash: str


class EventLedger:
    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self.events: list[LedgerEvent] = []

    @property
    def head(self) -> str:
        return self.events[-1].event_hash if self.events else "0" * 64

    def append(self, event_type: str, payload: dict[str, Any] | None = None) -> LedgerEvent:
        raw = {
            "sequence": len(self.events),
            "event_id": str(uuid4()),
            "run_id": self.run_id,
            "event_type": event_type,
            "timestamp": datetime.now(UTC),
            "payload": payload or {},
            "prev_event_hash": self.head,
        }
        digest = sha256_text(raw["prev_event_hash"] + canonical_json(raw))
        event = LedgerEvent(**raw, event_hash=digest)
        self.events.append(event)
        return event

    @staticmethod
    def verify(events: list[LedgerEvent | dict[str, Any]]) -> tuple[bool, str]:
        prev = "0" * 64
        for index, item in enumerate(events):
            event = item if isinstance(item, LedgerEvent) else LedgerEvent.model_validate(item)
            if event.sequence != index or event.prev_event_hash != prev:
                return False, f"chain linkage mismatch at sequence {index}"
            raw = event.model_dump(exclude={"event_hash"})
            expected = sha256_text(prev + canonical_json(raw))
            if expected != event.event_hash:
                return False, f"event hash mismatch at sequence {index}"
            prev = event.event_hash
        return True, prev
