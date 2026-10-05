from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from mimicus.commercial.decision import DeterministicLeadDecisionService
from mimicus.commercial.funnel import build_commercial_funnel
from mimicus.commercial.models import (
    CommercialContext,
    CommercialStageEvidence,
    LeadCandidate,
    LeadDecisionPolicy,
)

AS_OF = datetime(2026, 10, 4, 15, 0, tzinfo=UTC)


def _policy() -> LeadDecisionPolicy:
    return LeadDecisionPolicy(
        version="funnel-v1",
        max_work_per_lane=5,
        prepared_min_score=70,
        follow_up_after_hours={"messenger": 24, "reddit_comment": 24},
    )


def _candidate(
    prospect_id: str,
    *,
    lane: str = "facebook",
    score: float = 80,
    status: str = "replied",
    commercial_stage: str = "unknown",
    evidence: list[tuple[str, datetime]] | None = None,
) -> LeadCandidate:
    source = "Facebook" if lane == "facebook" else "Reddit"
    channel = "messenger" if lane == "facebook" else "reddit_comment"
    evidence_rows = tuple(
        CommercialStageEvidence(
            stage=stage,
            observed_at=observed_at,
            source_ref=f"private:{prospect_id}:{stage}",
            summary=f"sensitive summary {prospect_id} {stage}",
        )
        for stage, observed_at in (evidence or [])
    )
    return LeadCandidate(
        prospect_id=prospect_id,
        source_name=source,
        lane=lane,
        buyer=f"Sensitive Buyer {prospect_id}",
        title=f"Sensitive title {prospect_id}",
        active=True,
        argentina_eligible=True,
        worker_fee=False,
        scam_risk="low",
        setter_score=score,
        outreach_status=status,
        outreach_channel=channel,
        published_at=AS_OF - timedelta(days=4),
        verified_at=AS_OF - timedelta(days=3),
        contacted_at=AS_OF - timedelta(days=2) if status == "contacted" else None,
        source_url=f"https://private.example/{prospect_id}",
        direct_url=f"https://private.example/{prospect_id}/contact",
        commercial=CommercialContext(
            stage=commercial_stage,
            updated_at=AS_OF - timedelta(minutes=1),
            note=f"private note {prospect_id}",
            evidence=evidence_rows,
        ),
    )


def _snapshot(candidates: list[LeadCandidate]):
    batch = DeterministicLeadDecisionService().decide(
        candidates,
        _policy(),
        as_of=AS_OF,
    )
    return build_commercial_funnel(
        candidates,
        batch,
        as_of=AS_OF,
    )


def test_funnel_aggregates_current_state_and_terminal_win_rate() -> None:
    candidates = [
        _candidate("prepared", status="prepared", score=95),
        _candidate("reply", status="replied"),
        _candidate(
            "proposal",
            commercial_stage="proposal",
            evidence=[
                ("qualified", AS_OF - timedelta(hours=30)),
                ("proposal", AS_OF - timedelta(hours=20)),
            ],
        ),
        _candidate(
            "won",
            lane="reddit",
            status="closed",
            commercial_stage="won",
            evidence=[
                ("qualified", AS_OF - timedelta(hours=40)),
                ("proposal", AS_OF - timedelta(hours=20)),
                ("won", AS_OF - timedelta(hours=5)),
            ],
        ),
        _candidate(
            "lost",
            lane="reddit",
            status="closed",
            commercial_stage="lost",
            evidence=[
                ("qualified", AS_OF - timedelta(hours=50)),
                ("proposal", AS_OF - timedelta(hours=30)),
                ("lost", AS_OF - timedelta(hours=10)),
            ],
        ),
    ]

    snapshot = _snapshot(candidates)

    assert snapshot.overall.lead_count == 5
    assert snapshot.overall.current_commercial_stage_counts["proposal"] == 1
    assert snapshot.overall.terminal_outcome_counts == {"lost": 1, "won": 1}
    assert snapshot.overall.terminal_win_rate == 0.5
    assert snapshot.by_lane["reddit"].terminal_win_rate == 0.5
    assert snapshot.by_lane["facebook"].terminal_win_rate is None
    assert snapshot.overall.disposition_counts["COMPLETE"] == 2
    assert snapshot.overall.next_action_counts["FOLLOW_UP"] == 1


def test_funnel_measures_evidence_grounded_transitions_and_latency() -> None:
    candidates = [
        _candidate(
            "advanced-1",
            commercial_stage="proposal",
            evidence=[
                ("qualified", AS_OF - timedelta(hours=30)),
                ("proposal", AS_OF - timedelta(hours=20)),
            ],
        ),
        _candidate(
            "advanced-2",
            commercial_stage="proposal",
            evidence=[
                ("qualified", AS_OF - timedelta(hours=20)),
                ("proposal", AS_OF - timedelta(hours=10)),
            ],
        ),
        _candidate(
            "stuck-qualified",
            commercial_stage="qualified",
            evidence=[("qualified", AS_OF - timedelta(hours=15))],
        ),
        _candidate(
            "won",
            status="closed",
            commercial_stage="won",
            evidence=[
                ("qualified", AS_OF - timedelta(hours=40)),
                ("proposal", AS_OF - timedelta(hours=25)),
                ("won", AS_OF - timedelta(hours=5)),
            ],
        ),
    ]

    snapshot = _snapshot(candidates)
    q2p = snapshot.overall.qualified_to_proposal
    p2t = snapshot.overall.proposal_to_terminal

    assert q2p.eligible_count == 4
    assert q2p.advanced_count == 3
    assert q2p.rate == 0.75
    assert q2p.invalid_order_count == 0
    assert q2p.median_hours == 10.0

    assert p2t.eligible_count == 3
    assert p2t.advanced_count == 1
    assert p2t.rate == pytest.approx(1 / 3)
    assert p2t.median_hours == 20.0


def test_funnel_excludes_future_evidence_and_flags_invalid_order() -> None:
    candidate = _candidate(
        "time-anomaly",
        commercial_stage="proposal",
        evidence=[
            ("qualified", AS_OF - timedelta(hours=5)),
            ("proposal", AS_OF - timedelta(hours=10)),
            ("proposal", AS_OF + timedelta(hours=2)),
        ],
    )

    snapshot = _snapshot([candidate])
    stats = snapshot.overall.qualified_to_proposal

    assert stats.eligible_count == 1
    assert stats.advanced_count == 0
    assert stats.invalid_order_count == 1
    assert stats.rate == 0.0
    assert stats.median_hours is None


def test_calibration_rows_are_sanitized_and_canonical() -> None:
    candidate = _candidate(
        "sanitize",
        commercial_stage="proposal",
        score=92,
        evidence=[
            ("qualified", AS_OF - timedelta(hours=3)),
            ("proposal", AS_OF - timedelta(hours=1)),
        ],
    )

    snapshot = _snapshot([candidate])
    row = snapshot.calibration_rows[0]
    serialized = snapshot.model_dump_json()

    assert row.prospect_id == "sanitize"
    assert row.setter_score == 92
    assert row.qualified_at == AS_OF - timedelta(hours=3)
    assert row.proposal_at == AS_OF - timedelta(hours=1)
    assert "Sensitive Buyer" not in serialized
    assert "Sensitive title" not in serialized
    assert "private.example" not in serialized
    assert "sensitive summary" not in serialized
    assert "private:" not in serialized
    assert "private note" not in serialized


def test_terminal_outcome_uses_authoritative_current_stage() -> None:
    candidate = _candidate(
        "current-won",
        status="closed",
        commercial_stage="won",
        evidence=[
            ("lost", AS_OF - timedelta(days=2)),
            ("won", AS_OF - timedelta(hours=1)),
        ],
    )

    snapshot = _snapshot([candidate])
    row = snapshot.calibration_rows[0]

    assert row.terminal_outcome == "won"
    assert row.terminal_at == AS_OF - timedelta(hours=1)
    assert snapshot.overall.terminal_outcome_counts == {"won": 1}


def test_funnel_fails_closed_on_candidate_batch_mismatch() -> None:
    candidates = [_candidate("a"), _candidate("b")]
    batch = DeterministicLeadDecisionService().decide(
        [candidates[0]],
        _policy(),
        as_of=AS_OF,
    )

    with pytest.raises(ValueError, match="candidate IDs"):
        build_commercial_funnel(candidates, batch, as_of=AS_OF)


def test_funnel_requires_timezone_aware_as_of() -> None:
    candidate = _candidate("a")
    batch = DeterministicLeadDecisionService().decide(
        [candidate],
        _policy(),
        as_of=AS_OF,
    )

    with pytest.raises(ValueError, match="timezone"):
        build_commercial_funnel(
            [candidate],
            batch,
            as_of=datetime(2026, 10, 4, 15, 0),
        )


def test_input_permutation_produces_identical_snapshot_hash() -> None:
    candidates = [
        _candidate(
            "a",
            commercial_stage="proposal",
            evidence=[
                ("qualified", AS_OF - timedelta(hours=5)),
                ("proposal", AS_OF - timedelta(hours=2)),
            ],
        ),
        _candidate("b", lane="reddit", status="prepared", score=99),
    ]
    service = DeterministicLeadDecisionService()
    left_batch = service.decide(candidates, _policy(), as_of=AS_OF)
    right_candidates = list(reversed(candidates))
    right_batch = service.decide(right_candidates, _policy(), as_of=AS_OF)

    left = build_commercial_funnel(candidates, left_batch, as_of=AS_OF)
    right = build_commercial_funnel(right_candidates, right_batch, as_of=AS_OF)

    assert left.model_dump(mode="json") == right.model_dump(mode="json")
    assert left.snapshot_hash == right.snapshot_hash
