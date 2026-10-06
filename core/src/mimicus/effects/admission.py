from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ActionAdmissionError(ValueError):
    """Raised when an action lacks an explicit source-controlled classification."""


class ToolEffectClass(StrEnum):
    READ_ONLY = "READ_ONLY"
    MUTATING = "MUTATING"
    UNKNOWN = "UNKNOWN"


class ActionAdmissionRule(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    adapter: str = Field(min_length=1, max_length=128)
    operation: str = Field(min_length=1, max_length=128)
    effect_class: ToolEffectClass

    @field_validator("adapter", "operation")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("action admission identifiers must be non-empty")
        if "*" in stripped:
            raise ValueError("wildcard action admission rules are not supported")
        return stripped

    @property
    def key(self) -> tuple[str, str]:
        return (self.adapter, self.operation)


class ActionAdmissionDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    adapter: str
    operation: str
    effect_class: ToolEffectClass
    may_bypass_effect_gate: bool
    reason: str
    policy_version: str


class ActionAdmissionPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = Field(min_length=1, max_length=128)
    rules: tuple[ActionAdmissionRule, ...] = ()

    @field_validator("version")
    @classmethod
    def normalize_version(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("action admission policy version must be non-empty")
        return stripped

    @model_validator(mode="after")
    def reject_duplicate_rules(self) -> ActionAdmissionPolicy:
        seen: set[tuple[str, str]] = set()
        duplicates: set[tuple[str, str]] = set()
        for rule in self.rules:
            if rule.key in seen:
                duplicates.add(rule.key)
            seen.add(rule.key)
        if duplicates:
            formatted = sorted(f"{adapter}:{operation}" for adapter, operation in duplicates)
            raise ValueError(f"duplicate action admission rules: {formatted}")
        return self

    @staticmethod
    def _normalize_request(adapter: str, operation: str) -> tuple[str, str]:
        adapter_value = adapter.strip()
        operation_value = operation.strip()
        if not adapter_value or not operation_value:
            raise ValueError("action admission request identifiers must be non-empty")
        return adapter_value, operation_value

    def classify(self, *, adapter: str, operation: str) -> ActionAdmissionDecision:
        key = self._normalize_request(adapter, operation)
        matched = next((rule for rule in self.rules if rule.key == key), None)
        if matched is None:
            return ActionAdmissionDecision(
                adapter=key[0],
                operation=key[1],
                effect_class=ToolEffectClass.UNKNOWN,
                may_bypass_effect_gate=False,
                reason="unclassified_action",
                policy_version=self.version,
            )

        read_only = matched.effect_class == ToolEffectClass.READ_ONLY
        return ActionAdmissionDecision(
            adapter=key[0],
            operation=key[1],
            effect_class=matched.effect_class,
            may_bypass_effect_gate=read_only,
            reason="explicit_read_only" if read_only else "explicit_mutating",
            policy_version=self.version,
        )

    def require_known(self, *, adapter: str, operation: str) -> ActionAdmissionDecision:
        decision = self.classify(adapter=adapter, operation=operation)
        if decision.effect_class == ToolEffectClass.UNKNOWN:
            raise ActionAdmissionError(
                f"unclassified action requires an explicit admission rule: "
                f"{decision.adapter}:{decision.operation}"
            )
        return decision
