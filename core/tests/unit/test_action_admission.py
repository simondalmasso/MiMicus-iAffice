from __future__ import annotations

import pytest
from pydantic import ValidationError

from mimicus.effects.admission import (
    ActionAdmissionError,
    ActionAdmissionPolicy,
    ActionAdmissionRule,
    ToolEffectClass,
)


def _policy() -> ActionAdmissionPolicy:
    return ActionAdmissionPolicy(
        version="tool-admission-v1",
        rules=(
            ActionAdmissionRule(
                adapter="mcp",
                operation="get_mimicus_run",
                effect_class=ToolEffectClass.READ_ONLY,
            ),
            ActionAdmissionRule(
                adapter="mcp",
                operation="run_mimicus",
                effect_class=ToolEffectClass.MUTATING,
            ),
        ),
    )


def test_explicit_read_only_may_bypass_effect_gate() -> None:
    decision = _policy().classify(adapter="mcp", operation="get_mimicus_run")

    assert decision.effect_class == ToolEffectClass.READ_ONLY
    assert decision.may_bypass_effect_gate is True
    assert decision.reason == "explicit_read_only"


def test_explicit_mutating_never_bypasses_effect_gate() -> None:
    decision = _policy().classify(adapter="mcp", operation="run_mimicus")

    assert decision.effect_class == ToolEffectClass.MUTATING
    assert decision.may_bypass_effect_gate is False
    assert decision.reason == "explicit_mutating"


def test_unknown_action_fails_dangerous() -> None:
    policy = _policy()
    decision = policy.classify(adapter="mcp", operation="future_tool")

    assert decision.effect_class == ToolEffectClass.UNKNOWN
    assert decision.may_bypass_effect_gate is False
    assert decision.reason == "unclassified_action"

    with pytest.raises(ActionAdmissionError, match="unclassified"):
        policy.require_known(adapter="mcp", operation="future_tool")


def test_classification_is_exact_and_not_inferred_from_action_text() -> None:
    policy = _policy()

    near_match = policy.classify(adapter="mcp", operation="get_mimicus_run_and_delete")
    different_adapter = policy.classify(adapter="browser", operation="get_mimicus_run")

    assert near_match.effect_class == ToolEffectClass.UNKNOWN
    assert different_adapter.effect_class == ToolEffectClass.UNKNOWN


def test_duplicate_exact_rule_is_rejected_even_when_classes_conflict() -> None:
    with pytest.raises(ValidationError, match="duplicate"):
        ActionAdmissionPolicy(
            version="duplicate-test",
            rules=(
                ActionAdmissionRule(
                    adapter="mcp",
                    operation="run_mimicus",
                    effect_class=ToolEffectClass.READ_ONLY,
                ),
                ActionAdmissionRule(
                    adapter="mcp",
                    operation="run_mimicus",
                    effect_class=ToolEffectClass.MUTATING,
                ),
            ),
        )


def test_rule_identifiers_are_trimmed_but_not_wildcarded() -> None:
    rule = ActionAdmissionRule(
        adapter="  mcp  ",
        operation="  get_mimicus_run  ",
        effect_class=ToolEffectClass.READ_ONLY,
    )
    policy = ActionAdmissionPolicy(version="trim-test", rules=(rule,))

    assert policy.classify(adapter="mcp", operation="get_mimicus_run").may_bypass_effect_gate is True
    assert policy.classify(adapter="mcp", operation="*").effect_class == ToolEffectClass.UNKNOWN
