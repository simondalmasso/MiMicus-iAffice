from __future__ import annotations

from mimicus.commercial.diagnosis import (
    CommercialBottleneck,
    CommercialDiagnosisPolicy,
    CommercialFunnelDiagnosis,
)
from mimicus.commercial.intervention import (
    CommercialInterventionCode,
    plan_commercial_intervention,
)


def _policy() -> CommercialDiagnosisPolicy:
    return CommercialDiagnosisPolicy(
        version="intervention-test-v1",
        min_transition_samples=4,
        min_terminal_samples=5,
        min_transition_rate=0.6,
        min_terminal_win_rate=0.4,
        min_qualify_backlog=3,
    )


def _diagnosis(
    bottleneck: CommercialBottleneck,
    *,
    metrics: dict[str, int | float | None],
) -> CommercialFunnelDiagnosis:
    return CommercialFunnelDiagnosis(
        snapshot_hash="a" * 64,
        policy_hash="b" * 64,
        bottleneck=bottleneck,
        reasons=("test",),
        focus="test_focus",
        supporting_metrics=metrics,
        diagnosis_hash="c" * 64,
    )


def _criteria(plan) -> dict[str, object]:
    return {row.metric: row for row in plan.criteria}


def test_terminal_stall_targets_configured_transition_rate() -> None:
    diagnosis = _diagnosis(
        CommercialBottleneck.TERMINAL_STALL,
        metrics={"proposal_to_terminal_rate": 0.25},
    )

    plan = plan_commercial_intervention(diagnosis, _policy())

    assert plan.code == CommercialInterventionCode.RESOLVE_PROPOSALS
    criterion = _criteria(plan)["proposal_to_terminal_rate"]
    assert criterion.comparator == "gte"
    assert criterion.target == 0.6
    assert criterion.baseline == 0.25


def test_low_win_rate_targets_configured_win_threshold() -> None:
    plan = plan_commercial_intervention(
        _diagnosis(
            CommercialBottleneck.LOW_WIN_RATE,
            metrics={"terminal_win_rate": 0.2},
        ),
        _policy(),
    )

    assert plan.code == CommercialInterventionCode.IMPROVE_TERMINAL_WIN_RATE
    criterion = _criteria(plan)["terminal_win_rate"]
    assert criterion.target == 0.4
    assert criterion.comparator == "gte"


def test_proposal_stall_targets_qualified_to_proposal_rate() -> None:
    plan = plan_commercial_intervention(
        _diagnosis(
            CommercialBottleneck.PROPOSAL_STALL,
            metrics={"qualified_to_proposal_rate": 0.1},
        ),
        _policy(),
    )

    assert plan.code == CommercialInterventionCode.ADVANCE_QUALIFIED_TO_PROPOSAL
    criterion = _criteria(plan)["qualified_to_proposal_rate"]
    assert criterion.target == 0.6
    assert criterion.baseline == 0.1


def test_qualification_backlog_targets_below_configured_backlog_threshold() -> None:
    plan = plan_commercial_intervention(
        _diagnosis(
            CommercialBottleneck.QUALIFICATION_BACKLOG,
            metrics={"qualify_count": 7},
        ),
        _policy(),
    )

    assert plan.code == CommercialInterventionCode.QUALIFY_BACKLOG
    criterion = _criteria(plan)["qualify_count"]
    assert criterion.comparator == "lt"
    assert criterion.target == 3
    assert criterion.baseline == 7


def test_data_quality_requires_zero_invalid_stage_order() -> None:
    plan = plan_commercial_intervention(
        _diagnosis(
            CommercialBottleneck.DATA_QUALITY,
            metrics={"invalid_order_count": 2},
        ),
        _policy(),
    )

    assert plan.code == CommercialInterventionCode.REPAIR_STAGE_EVIDENCE
    criterion = _criteria(plan)["invalid_order_count"]
    assert criterion.comparator == "eq"
    assert criterion.target == 0


def test_insufficient_data_uses_explicit_sample_thresholds() -> None:
    plan = plan_commercial_intervention(
        _diagnosis(
            CommercialBottleneck.INSUFFICIENT_DATA,
            metrics={
                "qualified_to_proposal_eligible": 2,
                "proposal_to_terminal_eligible": 1,
                "terminal_count": 0,
            },
        ),
        _policy(),
    )
    criteria = _criteria(plan)

    assert plan.code == CommercialInterventionCode.COLLECT_FULL_FUNNEL_EVIDENCE
    assert criteria["qualified_to_proposal_eligible"].target == 4
    assert criteria["proposal_to_terminal_eligible"].target == 4
    assert criteria["terminal_count"].target == 5


def test_no_bottleneck_maintains_configured_floor_contract() -> None:
    plan = plan_commercial_intervention(
        _diagnosis(
            CommercialBottleneck.NO_OBSERVED_BOTTLENECK,
            metrics={
                "qualified_to_proposal_eligible": 6,
                "proposal_to_terminal_eligible": 5,
                "terminal_count": 5,
                "qualified_to_proposal_rate": 0.8,
                "proposal_to_terminal_rate": 0.7,
                "terminal_win_rate": 0.6,
            },
        ),
        _policy(),
    )
    criteria = _criteria(plan)

    assert plan.code == CommercialInterventionCode.MAINTAIN_BASELINE
    assert criteria["qualified_to_proposal_rate"].target == 0.6
    assert criteria["proposal_to_terminal_rate"].target == 0.6
    assert criteria["terminal_win_rate"].target == 0.4


def test_intervention_hash_binds_policy_and_is_stable() -> None:
    diagnosis = _diagnosis(
        CommercialBottleneck.PROPOSAL_STALL,
        metrics={"qualified_to_proposal_rate": 0.2},
    )
    left = plan_commercial_intervention(diagnosis, _policy())
    right = plan_commercial_intervention(diagnosis, _policy())

    assert left == right
    assert len(left.intervention_hash) == 64

    changed = plan_commercial_intervention(
        diagnosis,
        _policy().model_copy(update={"min_transition_rate": 0.7}),
    )
    assert changed.intervention_hash != left.intervention_hash
