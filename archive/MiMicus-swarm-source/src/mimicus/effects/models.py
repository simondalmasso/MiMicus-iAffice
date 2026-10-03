from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from mimicus.canonical import sha256_obj

_SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "password",
    "secret",
    "token",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "client_secret",
}


def _contains_raw_credential(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).strip().lower().replace("-", "_")
            if normalized in _SENSITIVE_KEYS:
                return True
            if _contains_raw_credential(item):
                return True
        return False
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_raw_credential(item) for item in value)
    return False


def _aware_utc(value: datetime, *, field_name: str) -> datetime:
    if value.utcoffset() is None:
        raise ValueError(f"{field_name} must include timezone information")
    return value.astimezone(UTC)


class EffectIntentState(StrEnum):
    AUTHORIZED = "AUTHORIZED"
    SUCCEEDED = "SUCCEEDED"
    UNKNOWN = "UNKNOWN"


class EffectActionEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    adapter: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    destination: str = Field(min_length=1)
    resource: str = Field(min_length=1)
    payload: dict[str, Any]
    scope: str = Field(min_length=1)

    @field_validator("adapter", "operation", "destination", "resource", "scope")
    @classmethod
    def strip_nonempty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("effect envelope fields must be non-empty")
        return stripped

    @field_validator("payload")
    @classmethod
    def reject_credentials(cls, value: dict[str, Any]) -> dict[str, Any]:
        if _contains_raw_credential(value):
            raise ValueError("raw credential fields are forbidden in effect payload")
        # Hashing now proves the payload is canonical-JSON serializable before approval.
        sha256_obj(value)
        return value

    @property
    def envelope_hash(self) -> str:
        return sha256_obj(self.model_dump(mode="json"))


class EffectApprovalReceipt(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    approval_id: str = Field(min_length=1, max_length=128)
    envelope_hash: str = Field(min_length=64, max_length=64)
    approver_id: str = Field(min_length=1, max_length=256)
    issued_at: datetime
    expires_at: datetime
    policy_version: str = Field(min_length=1, max_length=128)

    @field_validator("issued_at")
    @classmethod
    def issued_must_be_aware(cls, value: datetime) -> datetime:
        return _aware_utc(value, field_name="issued_at")

    @field_validator("expires_at")
    @classmethod
    def expiry_must_be_aware(cls, value: datetime) -> datetime:
        return _aware_utc(value, field_name="expires_at")

    @model_validator(mode="after")
    def validate_window(self) -> EffectApprovalReceipt:
        if self.expires_at <= self.issued_at:
            raise ValueError("approval expires_at must be after issued_at")
        return self


class EffectIntent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    intent_id: str = Field(min_length=64, max_length=64)
    approval_id: str = Field(min_length=1, max_length=128)
    envelope_hash: str = Field(min_length=64, max_length=64)
    state: EffectIntentState
    created_at: datetime
    completed_at: datetime | None = None
    outcome_hash: str | None = Field(default=None, min_length=64, max_length=64)
    error_class: str | None = None

    @field_validator("created_at", "completed_at")
    @classmethod
    def intent_time_must_be_aware(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        return _aware_utc(value, field_name="intent timestamp")
