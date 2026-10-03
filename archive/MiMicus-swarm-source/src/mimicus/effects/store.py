from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import insert, select, update
from sqlalchemy.exc import IntegrityError

from mimicus.canonical import sha256_obj
from mimicus.effects.models import (
    EffectApprovalReceipt,
    EffectIntent,
    EffectIntentState,
)
from mimicus.storage.models import EffectApprovalRow, EffectIntentRow
from mimicus.storage.repository import Repository


class EffectAuthorizationError(PermissionError):
    """Raised when an effect lacks a valid one-use approval."""


def _utc(value: datetime, *, label: str) -> datetime:
    if value.utcoffset() is None:
        raise ValueError(f"{label} must include timezone information")
    return value.astimezone(UTC)


def _intent_from_row(mapping: Mapping[str, Any]) -> EffectIntent:
    return EffectIntent(
        intent_id=str(mapping["intent_id"]),
        approval_id=str(mapping["approval_id"]),
        envelope_hash=str(mapping["envelope_hash"]),
        state=EffectIntentState(str(mapping["state"])),
        created_at=datetime.fromisoformat(str(mapping["created_at"])),
        completed_at=(
            None
            if mapping["completed_at"] is None
            else datetime.fromisoformat(str(mapping["completed_at"]))
        ),
        outcome_hash=None if mapping["outcome_hash"] is None else str(mapping["outcome_hash"]),
        error_class=None if mapping["error_class"] is None else str(mapping["error_class"]),
    )


class EffectStore:
    def __init__(self, repository: Repository) -> None:
        self.repository = repository

    def register_approval(self, receipt: EffectApprovalReceipt) -> None:
        values = receipt.model_dump(mode="json")
        values["issued_at"] = receipt.issued_at.astimezone(UTC).isoformat()
        values["expires_at"] = receipt.expires_at.astimezone(UTC).isoformat()
        values["consumed_at"] = None
        try:
            with self.repository.engine.begin() as connection:
                connection.execute(insert(EffectApprovalRow).values(**values))
        except IntegrityError as exc:
            raise ValueError(f"approval already exists: {receipt.approval_id}") from exc

    def consume_approval(
        self,
        *,
        approval_id: str,
        envelope_hash: str,
        now: datetime,
    ) -> EffectIntent:
        current = _utc(now, label="effect dispatch time")
        now_iso = current.isoformat()
        intent_id = sha256_obj(
            {
                "approval_id": approval_id,
                "envelope_hash": envelope_hash,
            }
        )

        with self.repository.engine.begin() as connection:
            consumed = connection.execute(
                update(EffectApprovalRow)
                .where(
                    EffectApprovalRow.approval_id == approval_id,
                    EffectApprovalRow.envelope_hash == envelope_hash,
                    EffectApprovalRow.consumed_at.is_(None),
                    EffectApprovalRow.expires_at > now_iso,
                )
                .values(consumed_at=now_iso)
            )
            if consumed.rowcount != 1:
                row = connection.execute(
                    select(EffectApprovalRow).where(
                        EffectApprovalRow.approval_id == approval_id
                    )
                ).first()
                if row is None:
                    raise EffectAuthorizationError("approval not found")
                mapping = row._mapping
                if str(mapping["envelope_hash"]) != envelope_hash:
                    raise EffectAuthorizationError("approval envelope hash mismatch")
                if mapping["consumed_at"] is not None:
                    raise EffectAuthorizationError("approval already consumed")
                expiry = datetime.fromisoformat(str(mapping["expires_at"]))
                if expiry <= current:
                    raise EffectAuthorizationError("approval expired")
                raise EffectAuthorizationError("approval could not be consumed atomically")

            connection.execute(
                insert(EffectIntentRow).values(
                    intent_id=intent_id,
                    approval_id=approval_id,
                    envelope_hash=envelope_hash,
                    state=EffectIntentState.AUTHORIZED.value,
                    created_at=now_iso,
                    completed_at=None,
                    outcome_hash=None,
                    error_class=None,
                )
            )

        return EffectIntent(
            intent_id=intent_id,
            approval_id=approval_id,
            envelope_hash=envelope_hash,
            state=EffectIntentState.AUTHORIZED,
            created_at=current,
        )

    def _complete(
        self,
        intent_id: str,
        *,
        state: EffectIntentState,
        completed_at: datetime,
        outcome_hash: str | None,
        error_class: str | None,
    ) -> EffectIntent:
        if state not in {EffectIntentState.SUCCEEDED, EffectIntentState.UNKNOWN}:
            raise ValueError("effect intent completion state must be terminal")
        completed = _utc(completed_at, label="effect completion time")
        with self.repository.engine.begin() as connection:
            changed = connection.execute(
                update(EffectIntentRow)
                .where(
                    EffectIntentRow.intent_id == intent_id,
                    EffectIntentRow.state == EffectIntentState.AUTHORIZED.value,
                )
                .values(
                    state=state.value,
                    completed_at=completed.isoformat(),
                    outcome_hash=outcome_hash,
                    error_class=error_class,
                )
            )
            if changed.rowcount != 1:
                raise RuntimeError("effect intent is missing or already terminal")
            row = connection.execute(
                select(EffectIntentRow).where(EffectIntentRow.intent_id == intent_id)
            ).first()
            assert row is not None
            return _intent_from_row(dict(row._mapping))

    def mark_succeeded(
        self,
        intent_id: str,
        *,
        completed_at: datetime,
        outcome_hash: str,
    ) -> EffectIntent:
        return self._complete(
            intent_id,
            state=EffectIntentState.SUCCEEDED,
            completed_at=completed_at,
            outcome_hash=outcome_hash,
            error_class=None,
        )

    def mark_unknown(
        self,
        intent_id: str,
        *,
        completed_at: datetime,
        error_class: str,
    ) -> EffectIntent:
        return self._complete(
            intent_id,
            state=EffectIntentState.UNKNOWN,
            completed_at=completed_at,
            outcome_hash=None,
            error_class=error_class,
        )

    def get_intent(self, intent_id: str) -> EffectIntent | None:
        with self.repository.engine.begin() as connection:
            row = connection.execute(
                select(EffectIntentRow).where(EffectIntentRow.intent_id == intent_id)
            ).first()
        return None if row is None else _intent_from_row(row._mapping)

    def intents_for_approval(self, approval_id: str) -> list[EffectIntent]:
        with self.repository.engine.begin() as connection:
            rows = connection.execute(
                select(EffectIntentRow)
                .where(EffectIntentRow.approval_id == approval_id)
                .order_by(EffectIntentRow.created_at)
            ).all()
        return [_intent_from_row(row._mapping) for row in rows]
