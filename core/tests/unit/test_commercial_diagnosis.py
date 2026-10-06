from __future__ import annotations

from datetime import UTC, datetime

from mimicus.canonical import sha256_obj
from mimicus.commercial.diagnosis import (
    CommercialBottleneck,
    CommercialDiagnosisPolicy,
    diagnose_commercial_funnel,
)
from mimicus.commercial.funnel import (
    CommercialFunnelSnapshot,
    FunnelMetrics,
    FunnelTransitionStats,
)

AS_OF = datetime(2026, 10, 5, 23, 0, tzinfo=UTC)


def _transition(*, eligible: int, advanced: int, invalid: int = 0) -> FunnelTransitionStats:
    return FunnelTransitionStats(
        eligible_count=eligible,
        advanced_count=advanced,
        rate=None if eligible == 0 else advanced / eligible,
        median_hours=None,
        invalid_order_count=invalid,
    )


def _metrics(
    *,
    leads: int = 10,
    qualify: int = 0,
    q2p: tuple[int, int, int] = (0, 0, 0),
    p2t: tuple[int, int, int] = (0, 0, 0),
    won: int = 0,
    lost: int = 0,
) -> FunnelMetrics:
    q_e, q_a, q_i = q2p
    p_e, p_a, p_i = p2t
    terminal_total = won + lost
    return FunnelMetrics(
        lead_count=leads,
        disposition_counts={"WORK_NOW": leads} if leads else {},
        next_action_counts={"QUALIFY": qualify} if qualify else {},
        current_commercial_stage_counts={},
        terminal_outcome_counts={
            key: value
            for key, value in (("won", won), ("lost", lost))
            if value
        },
        terminal_win_rate=None if terminal_total == 0 else won / terminal_total,
        qualified_to_proposal=_transition(eligible=q_e, advanced=q_a, invalid=q_i),
        proposal_to_terminal=_transition(eligible=p_e, advanced=p_a, invalid=p_i),
    )


def _snapshot(overall: FunnelMetrics, *, by_lane_reversed: bool = False) -> CommercialFunnelSnapshot:
    lanes = {
        "facebook": overall,
        "reddit": _metrics(leads=0),
    }
    if by_lane_reversed:
        lanes = dict(reversed(list(lanes.items())))
    semantic = {
        "as_of": AS_OF.isoformat(),
        "policy_hash": "a" * 64,
        "batch_hash": "b" * 64,
        "overall": overall.model_dump(mode="json"),
        "by_lane": {
            lane: metrics.model_dump(mode="json")
            for lane, metrics in sorted(lanes.items())
        },
        "calibration_rows": [],
    }
    return CommercialFunnelSnapshot(
        as_of=AS_OF,
        policy_hash="a" * 64,
        batch_hash="b" * 64,
        overall=overall,
        by_lane=lanes,
        calibration_rows=(),
        snapshot_hash=sha256_obj(semantic),
    )


def _policy() -> CommercialDiagnosisPolicy:
    return CommercialDiagnosisPolicy(
        version="diagnosis-test-v1",
        min_transition_samples=3,
        min_terminal_samples=3,
        min_transition_rate=0.5,
        min_terminal_win_rate=0.34,
        min_qualify_backlog=3,
    )


def test_invalid_stage_chronology_is_data_quality_bottleneck() -> None:
    diagnosis = diagnose_commercial_funnel(
        _snapshot(_metrics(q2p=(3, 2, 1))),
        _policy(),
    )

    assert diagnosis.bottleneck == CommercialBottleneck.DATA_QUALITY
    assert diagnosis.focus == "repair_stage_evidence"
    assert "invalid_stage_order" in diagnosis.reasons


def test_enough_proposals_without_terminal_progress_is_terminal_stall() -> None:
    diagnosis = diagnose_commercial_funnel(
        _snapshot(_metrics(q2p=(4, 4, 0), p2t=(4, 1, 0))),
        _policy(),
    )

    assert diagnosis.bottleneck == CommercialBottleneck.TERMINAL_STALL
    assert diagnosis.focus == "advance_proposals_to_outcome"


def test_low_terminal_win_rate_is_closing_gap_after_terminal_progress_exists() -> None:
    diagnosis = diagnose_commercial_funnel(
        _snapshot(_metrics(q2p=(6, 5, 0), p2t=(5, 5, 0), won=1, lost=4)),
        _policy(),
    )

    assert diagnosis.bottleneck == CommercialBottleneck.LOW_WIN_RATE
    assert diagnosis.focus == "improve_offer_and_closing"


def test_qualified_leads_not_advancing_to_proposal_is_proposal_stall() -> None:
    diagnosis = diagnose_commercial_funnel(
        _snapshot(_metrics(q2p=(5, 1, 0), p2t=(0, 0, 0))),
        _policy(),
    )

    assert diagnosis.bottleneck == CommercialBottleneck.PROPOSAL_STALL
    assert diagnosis.focus == "convert_qualified_to_proposal"


def test_large_qualify_queue_is_qualification_backlog_when_no_stronger_signal_exists() -> None:
    diagnosis = diagnose_commercial_funnel(
        _snapshot(_metrics(qualify=4)),
        _policy(),
    )

    assert diagnosis.bottleneck == CommercialBottleneck.QUALIFICATION_BACKLOG
    assert diagnosis.focus == "qualify_replied_leads"


def test_sparse_funnel_is_insufficient_data() -> None:
    diagnosis = diagnose_commercial_funnel(
        _snapshot(_metrics(leads=2, qualify=1)),
        _policy(),
    )

    assert diagnosis.bottleneck == CommercialBottleneck.INSUFFICIENT_DATA
    assert diagnosis.focus == "collect_stage_evidence"


def test_healthy_observed_transitions_have_no_bottleneck() -> None:
    diagnosis = diagnose_commercial_funnel(
        _snapshot(_metrics(q2p=(5, 4, 0), p2t=(4, 3, 0), won=2, lost=1)),
        _policy(),
    )

    assert diagnosis.bottleneck == CommercialBottleneck.NO_OBSERVED_BOTTLENECK
    assert diagnosis.focus == "maintain_and_measure"


def test_diagnosis_hash_is_canonical_and_binds_policy() -> None:
    left = diagnose_commercial_funnel(
        _snapshot(_metrics(q2p=(5, 1, 0)), by_lane_reversed=False),
        _policy(),
    )
    right = diagnose_commercial_funnel(
        _snapshot(_metrics(q2p=(5, 1, 0)), by_lane_reversed=True),
        _policy(),
    )

    assert left == right
    assert len(left.diagnosis_hash) == 64

    changed = diagnose_commercial_funnel(
        _snapshot(_metrics(q2p=(5, 1, 0))),
        _policy().model_copy(update={"min_transition_rate": 0.2}),
    )
    assert changed.diagnosis_hash != left.diagnosis_hash
