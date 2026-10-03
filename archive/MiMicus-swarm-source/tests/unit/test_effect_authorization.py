from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from threading import Barrier

import pytest
from pydantic import ValidationError

from mimicus.effects.dispatcher import EffectDispatcher
from mimicus.effects.models import (
    EffectActionEnvelope,
    EffectApprovalReceipt,
    EffectIntentState,
)
from mimicus.effects.store import EffectAuthorizationError, EffectStore
from mimicus.storage.repository import Repository

NOW = datetime(2026, 10, 3, 22, 30, tzinfo=UTC)


class RecordingAdapter:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[EffectActionEnvelope] = []
        self.fail = fail

    def dispatch(self, envelope: EffectActionEnvelope) -> object:
        self.calls.append(envelope)
        if self.fail:
            raise RuntimeError("remote outcome uncertain")
        return {"ok": True, "operation": envelope.operation}


def _envelope(**updates: object) -> EffectActionEnvelope:
    payload: dict[str, object] = {
        "adapter": "test.messaging",
        "operation": "send_message",
        "destination": "buyer:123",
        "resource": "thread:abc",
        "payload": {"text": "hello"},
        "scope": "commercial-outreach",
    }
    payload.update(updates)
    return EffectActionEnvelope.model_validate(payload)


def _approval(envelope: EffectActionEnvelope, approval_id: str = "approval-1", *, expires_at: datetime | None = None) -> EffectApprovalReceipt:
    return EffectApprovalReceipt(
        approval_id=approval_id,
        envelope_hash=envelope.envelope_hash,
        approver_id="human:operator",
        issued_at=NOW,
        expires_at=expires_at or (NOW + timedelta(minutes=10)),
        policy_version="effect-policy-v1",
    )


def _dispatcher(tmp_path: Path) -> tuple[EffectStore, EffectDispatcher]:
    repository = Repository(f"sqlite:///{tmp_path / 'effects.db'}")
    store = EffectStore(repository)
    return store, EffectDispatcher(store=store, clock=lambda: NOW)


def test_default_denies_without_approval_and_adapter_observes_zero_dispatches(tmp_path: Path) -> None:
    _store, dispatcher = _dispatcher(tmp_path)
    adapter = RecordingAdapter()

    with pytest.raises(EffectAuthorizationError, match="approval"):
        dispatcher.dispatch(_envelope(), approval_id="missing", adapter=adapter)

    assert adapter.calls == []


def test_exact_approval_dispatches_once_and_persists_success(tmp_path: Path) -> None:
    store, dispatcher = _dispatcher(tmp_path)
    envelope = _envelope()
    store.register_approval(_approval(envelope))
    adapter = RecordingAdapter()

    result = dispatcher.dispatch(envelope, approval_id="approval-1", adapter=adapter)

    assert len(adapter.calls) == 1
    assert result.state == EffectIntentState.SUCCEEDED
    persisted = store.get_intent(result.intent_id)
    assert persisted is not None
    assert persisted.state == EffectIntentState.SUCCEEDED
    assert persisted.outcome_hash == result.outcome_hash


def test_payload_or_destination_tampering_is_denied_before_dispatch(tmp_path: Path) -> None:
    store, dispatcher = _dispatcher(tmp_path)
    approved = _envelope()
    store.register_approval(_approval(approved))
    adapter = RecordingAdapter()

    with pytest.raises(EffectAuthorizationError, match="envelope"):
        dispatcher.dispatch(
            _envelope(payload={"text": "different"}),
            approval_id="approval-1",
            adapter=adapter,
        )

    with pytest.raises(EffectAuthorizationError, match="envelope"):
        dispatcher.dispatch(
            _envelope(destination="buyer:999"),
            approval_id="approval-1",
            adapter=adapter,
        )

    assert adapter.calls == []


def test_expired_approval_is_denied(tmp_path: Path) -> None:
    store, dispatcher = _dispatcher(tmp_path)
    envelope = _envelope()
    store.register_approval(_approval(envelope, expires_at=NOW - timedelta(seconds=1)))
    adapter = RecordingAdapter()

    with pytest.raises(EffectAuthorizationError, match="expired"):
        dispatcher.dispatch(envelope, approval_id="approval-1", adapter=adapter)

    assert adapter.calls == []


def test_approval_is_one_use(tmp_path: Path) -> None:
    store, dispatcher = _dispatcher(tmp_path)
    envelope = _envelope()
    store.register_approval(_approval(envelope))
    adapter = RecordingAdapter()

    dispatcher.dispatch(envelope, approval_id="approval-1", adapter=adapter)
    with pytest.raises(EffectAuthorizationError, match="consumed"):
        dispatcher.dispatch(envelope, approval_id="approval-1", adapter=adapter)

    assert len(adapter.calls) == 1


def test_adapter_exception_marks_unknown_and_blocks_blind_retry(tmp_path: Path) -> None:
    store, dispatcher = _dispatcher(tmp_path)
    envelope = _envelope()
    store.register_approval(_approval(envelope))
    adapter = RecordingAdapter(fail=True)

    with pytest.raises(RuntimeError, match="uncertain"):
        dispatcher.dispatch(envelope, approval_id="approval-1", adapter=adapter)

    intents = store.intents_for_approval("approval-1")
    assert len(intents) == 1
    assert intents[0].state == EffectIntentState.UNKNOWN

    with pytest.raises(EffectAuthorizationError, match="consumed"):
        dispatcher.dispatch(envelope, approval_id="approval-1", adapter=adapter)
    assert len(adapter.calls) == 1


def test_atomic_consumption_allows_at_most_one_concurrent_dispatch(tmp_path: Path) -> None:
    store, dispatcher = _dispatcher(tmp_path)
    envelope = _envelope()
    store.register_approval(_approval(envelope))
    adapter = RecordingAdapter()
    barrier = Barrier(2)

    def attempt() -> str:
        barrier.wait(timeout=2)
        try:
            dispatcher.dispatch(envelope, approval_id="approval-1", adapter=adapter)
            return "dispatched"
        except EffectAuthorizationError:
            return "denied"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = sorted([pool.submit(attempt).result() for _ in range(2)])

    assert results == ["denied", "dispatched"]
    assert len(adapter.calls) == 1


def test_envelope_rejects_raw_credential_fields() -> None:
    with pytest.raises(ValidationError, match="credential"):
        _envelope(payload={"authorization": "Bearer secret"})
