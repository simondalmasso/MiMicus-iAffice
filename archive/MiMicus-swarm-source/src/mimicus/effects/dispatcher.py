from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Protocol

from mimicus.canonical import sha256_obj
from mimicus.effects.models import EffectActionEnvelope, EffectIntent
from mimicus.effects.store import EffectStore


class EffectAdapter(Protocol):
    def dispatch(self, envelope: EffectActionEnvelope) -> object: ...


class EffectDispatcher:
    def __init__(
        self,
        *,
        store: EffectStore,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.store = store
        self.clock = clock or (lambda: datetime.now(UTC))

    def _now(self) -> datetime:
        value = self.clock()
        if value.utcoffset() is None:
            raise ValueError("effect dispatcher clock must be timezone-aware")
        return value.astimezone(UTC)

    def dispatch(
        self,
        envelope: EffectActionEnvelope,
        *,
        approval_id: str,
        adapter: EffectAdapter,
    ) -> EffectIntent:
        intent = self.store.consume_approval(
            approval_id=approval_id,
            envelope_hash=envelope.envelope_hash,
            now=self._now(),
        )
        try:
            outcome = adapter.dispatch(envelope)
            outcome_hash = sha256_obj(outcome)
            return self.store.mark_succeeded(
                intent.intent_id,
                completed_at=self._now(),
                outcome_hash=outcome_hash,
            )
        except Exception as exc:
            try:
                self.store.mark_unknown(
                    intent.intent_id,
                    completed_at=self._now(),
                    error_class=type(exc).__name__,
                )
            except Exception:
                # The effect may already have happened. Never restore approval
                # or attempt an automatic redispatch merely because recording failed.
                pass
            raise
