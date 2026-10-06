from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from mimicus.commercial.decision import DeterministicLeadDecisionService
from mimicus.commercial.models import (
    CommercialGoalCode,
    CommercialStage,
    LeadCandidate,
    LeadDecisionPolicy,
    LeadDisposition,
    LeadNextAction,
    LeadStage,
)

AS_OF = datetime(2026, 10, 1, 15, 0, tzinfo=UTC)


def _candidate(
    prospect_id: str,
    *,
    lane: str = "facebook",
    status: str = "prepared",
    score: float = 80,
    scam_risk: str = "low",
    active: bool = True,
    argentina_eligible: bool | None = True,
    worker_fee: bool | None = False,
    channel: str | None = "messenger",
    contacted_at: datetime | None = None,
    verified_at: datetime | None = None,
    published_at: datetime | None = None,
    commercial_stage: str = "unknown",
    commercial_evidence: list[dict[str, object]] | None = None,
) -> LeadCandidate:
    source_name = "Facebook" if lane == "facebook" else "Reddit"
    if commercial_evidence is None and commercial_stage in {"qualified", "proposal", "won", "lost"}:
        commercial_evidence = [
            {
                "stage": commercial_stage,
                "observed_at": AS_OF - timedelta(minutes=5),
                "source_ref": f"test:{prospect_id}:{commercial_stage}",
            }
        ]
    return LeadCandidate.model_validate(
        {
            "prospect_id": prospect_id,
            "source_name": source_name,
            "lane": lane,
            "buyer": "Buyer",
            "title": f"Lead {prospect_id}",
            "active": active,
            "argentina_eligible": argentina_eligible,
            "worker_fee": worker_fee,
            "scam_risk": scam_risk,
            "setter_score": score,
            "outreach_status": status,
            "outreach_channel": channel,
            "published_at": published_at or (AS_OF - timedelta(days=7)),
            "verified_at": verified_at or (AS_OF - timedelta(hours=1)),
            "contacted_at": contacted_at,
            "source_url": f"https://example.test/{prospect_id}",
            "direct_url": f"https://example.test/{prospect_id}/contact",
            "commercial": {
                "stage": commercial_stage,
                "evidence": commercial_evidence or [],
            },
        }
    )


def _policy(
    *,
    max_work: int = 3,
    thresholds: dict[str, int] | None = None,
    prepared_min_score: float = 0,
) -> LeadDecisionPolicy:
    return LeadDecisionPolicy(
        version="test-v1",
        max_work_per_lane=max_work,
        prepared_min_score=prepared_min_score,
        follow_up_after_hours=thresholds if thresholds is not None else {"messenger": 24, "reddit_comment": 24},
    )


def _by_id(batch: object) -> dict[str, object]:
    decisions = batch.decisions  # type: ignore[attr-defined]
    return {decision.prospect_id: decision for decision in decisions}


def test_replied_outranks_prepared_even_with_lower_setter_score() -> None:
    service = DeterministicLeadDecisionService()
    batch = service.decide(
        [
            _candidate("prepared", status="prepared", score=99),
            _candidate("reply", status="replied", score=50),
        ],
        _policy(),
        as_of=AS_OF,
    )

    assert batch.selected_by_lane["facebook"] == ("reply", "prepared")
    assert _by_id(batch)["reply"].rank_position == 1  # type: ignore[union-attr]


def test_only_three_actionable_records_per_lane_are_work_now() -> None:
    service = DeterministicLeadDecisionService()
    batch = service.decide(
        [_candidate(f"lead-{score}", score=score) for score in (90, 80, 70, 60)],
        _policy(max_work=3),
        as_of=AS_OF,
    )
    decisions = _by_id(batch)

    assert batch.selected_by_lane["facebook"] == ("lead-90", "lead-80", "lead-70")
    assert decisions["lead-60"].disposition == LeadDisposition.HOLD  # type: ignore[union-attr]


def test_contacted_waiting_is_hold_even_when_lane_has_free_capacity() -> None:
    batch = DeterministicLeadDecisionService().decide(
        [
            _candidate(
                "waiting",
                status="contacted",
                contacted_at=AS_OF - timedelta(hours=1),
            )
        ],
        _policy(max_work=3),
        as_of=AS_OF,
    )
    decision = _by_id(batch)["waiting"]

    assert decision.stage == LeadStage.CONTACTED_WAITING  # type: ignore[union-attr]
    assert decision.disposition == LeadDisposition.HOLD  # type: ignore[union-attr]
    assert batch.selected_by_lane["facebook"] == ()


def test_closed_high_score_never_becomes_work_now() -> None:
    batch = DeterministicLeadDecisionService().decide(
        [_candidate("closed", status="closed", score=100)],
        _policy(),
        as_of=AS_OF,
    )
    decision = _by_id(batch)["closed"]

    assert decision.stage == LeadStage.TERMINAL  # type: ignore[union-attr]
    assert decision.disposition == LeadDisposition.REJECT  # type: ignore[union-attr]


def test_high_scam_risk_never_becomes_work_now() -> None:
    decision = _by_id(
        DeterministicLeadDecisionService().decide(
            [_candidate("scam", scam_risk="high", score=100)],
            _policy(),
            as_of=AS_OF,
        )
    )["scam"]

    assert decision.disposition == LeadDisposition.REJECT  # type: ignore[union-attr]


@pytest.mark.parametrize(
    ("candidate", "reason_fragment"),
    [
        (_candidate("fee", worker_fee=True), "worker_fee"),
        (_candidate("geo", argentina_eligible=False), "argentina"),
    ],
)
def test_worker_fee_and_argentina_ineligible_are_rejected(
    candidate: LeadCandidate,
    reason_fragment: str,
) -> None:
    decision = _by_id(
        DeterministicLeadDecisionService().decide([candidate], _policy(), as_of=AS_OF)
    )[candidate.prospect_id]

    assert decision.disposition == LeadDisposition.REJECT  # type: ignore[union-attr]
    assert any(reason_fragment in reason for reason in decision.reasons)  # type: ignore[union-attr]


def test_missing_contacted_at_is_repair_data() -> None:
    decision = _by_id(
        DeterministicLeadDecisionService().decide(
            [_candidate("missing-time", status="contacted", contacted_at=None)],
            _policy(),
            as_of=AS_OF,
        )
    )["missing-time"]

    assert decision.disposition == LeadDisposition.REPAIR_DATA  # type: ignore[union-attr]
    assert "missing_contacted_at" in decision.data_quality_issues  # type: ignore[union-attr]


def test_missing_followup_threshold_is_repair_data() -> None:
    decision = _by_id(
        DeterministicLeadDecisionService().decide(
            [
                _candidate(
                    "missing-threshold",
                    status="contacted",
                    channel="email",
                    contacted_at=AS_OF - timedelta(hours=72),
                )
            ],
            _policy(thresholds={"messenger": 24}),
            as_of=AS_OF,
        )
    )["missing-threshold"]

    assert decision.disposition == LeadDisposition.REPAIR_DATA  # type: ignore[union-attr]
    assert "missing_follow_up_threshold" in decision.data_quality_issues  # type: ignore[union-attr]


def test_old_open_lead_is_not_rejected_for_publication_age() -> None:
    batch = DeterministicLeadDecisionService().decide(
        [
            _candidate(
                "old-open",
                status="prepared",
                published_at=AS_OF - timedelta(days=30),
            )
        ],
        _policy(),
        as_of=AS_OF,
    )

    assert batch.selected_by_lane["facebook"] == ("old-open",)


def test_input_permutation_produces_identical_batch_dump_and_hash() -> None:
    service = DeterministicLeadDecisionService()
    candidates = [
        _candidate("a", status="replied", score=40),
        _candidate("b", status="prepared", score=95),
        _candidate(
            "c",
            lane="reddit",
            status="contacted",
            channel="reddit_comment",
            contacted_at=AS_OF - timedelta(hours=30),
        ),
    ]

    left = service.decide(candidates, _policy(), as_of=AS_OF)
    right = service.decide(list(reversed(candidates)), _policy(), as_of=AS_OF)

    assert left.model_dump(mode="json") == right.model_dump(mode="json")
    assert left.batch_hash == right.batch_hash


def test_duplicate_prospect_ids_are_rejected_before_ranking() -> None:
    service = DeterministicLeadDecisionService()

    with pytest.raises(ValueError, match="duplicate prospect_id"):
        service.decide(
            [_candidate("same"), _candidate("same", score=10)],
            _policy(),
            as_of=AS_OF,
        )


def test_unknown_outreach_status_is_repair_data() -> None:
    decision = _by_id(
        DeterministicLeadDecisionService().decide(
            [_candidate("unknown", status="mystery")],
            _policy(),
            as_of=AS_OF,
        )
    )["unknown"]

    assert decision.stage == LeadStage.UNKNOWN  # type: ignore[union-attr]
    assert decision.disposition == LeadDisposition.REPAIR_DATA  # type: ignore[union-attr]


def test_policy_and_batch_mappings_are_immutable() -> None:
    policy = _policy()
    with pytest.raises(TypeError):
        policy.follow_up_after_hours["messenger"] = 1  # type: ignore[index]

    batch = DeterministicLeadDecisionService().decide(
        [_candidate("immutable")],
        policy,
        as_of=AS_OF,
    )
    with pytest.raises(TypeError):
        batch.selected_by_lane["facebook"] = ()  # type: ignore[index]


def test_prepared_below_quality_floor_is_held_with_free_capacity() -> None:
    batch = DeterministicLeadDecisionService().decide(
        [_candidate("weak-prepared", status="prepared", score=69)],
        _policy(max_work=3, prepared_min_score=70),
        as_of=AS_OF,
    )
    decision = _by_id(batch)["weak-prepared"]

    assert decision.disposition == LeadDisposition.HOLD  # type: ignore[union-attr]
    assert "prepared_below_quality_floor" in decision.reasons  # type: ignore[union-attr]
    assert batch.selected_by_lane["facebook"] == ()


def test_prepared_at_quality_floor_can_work_now() -> None:
    batch = DeterministicLeadDecisionService().decide(
        [_candidate("floor-prepared", status="prepared", score=70)],
        _policy(max_work=3, prepared_min_score=70),
        as_of=AS_OF,
    )

    assert batch.selected_by_lane["facebook"] == ("floor-prepared",)


def test_reply_is_not_blocked_by_prepared_quality_floor() -> None:
    batch = DeterministicLeadDecisionService().decide(
        [_candidate("reply-low-score", status="replied", score=1)],
        _policy(max_work=3, prepared_min_score=90),
        as_of=AS_OF,
    )

    assert batch.selected_by_lane["facebook"] == ("reply-low-score",)


def test_due_followup_is_not_blocked_by_prepared_quality_floor() -> None:
    batch = DeterministicLeadDecisionService().decide(
        [
            _candidate(
                "due-low-score",
                status="contacted",
                score=1,
                contacted_at=AS_OF - timedelta(hours=48),
            )
        ],
        _policy(max_work=3, prepared_min_score=90),
        as_of=AS_OF,
    )

    assert batch.selected_by_lane["facebook"] == ("due-low-score",)


def test_weak_prepared_does_not_consume_wip_capacity() -> None:
    batch = DeterministicLeadDecisionService().decide(
        [
            _candidate("strong-1", score=95),
            _candidate("weak", score=10),
            _candidate("strong-2", score=90),
        ],
        _policy(max_work=2, prepared_min_score=70),
        as_of=AS_OF,
    )

    assert batch.selected_by_lane["facebook"] == ("strong-1", "strong-2")
    assert _by_id(batch)["weak"].disposition == LeadDisposition.HOLD  # type: ignore[union-attr]


def test_quality_floor_is_bound_into_policy_hash() -> None:
    service = DeterministicLeadDecisionService()
    candidate = _candidate("same")
    low = service.decide([candidate], _policy(prepared_min_score=0), as_of=AS_OF)
    high = service.decide([candidate], _policy(prepared_min_score=90), as_of=AS_OF)

    assert low.policy_hash != high.policy_hash
    assert low.batch_hash != high.batch_hash


def test_due_followup_outranks_new_prepared_work() -> None:
    batch = DeterministicLeadDecisionService().decide(
        [
            _candidate("fresh-prepared", status="prepared", score=100),
            _candidate(
                "due-followup",
                status="contacted",
                score=10,
                contacted_at=AS_OF - timedelta(hours=48),
            ),
        ],
        _policy(max_work=1, prepared_min_score=0),
        as_of=AS_OF,
    )

    assert batch.selected_by_lane["facebook"] == ("due-followup",)
    assert _by_id(batch)["fresh-prepared"].disposition == LeadDisposition.HOLD  # type: ignore[union-attr]


def test_proposal_outranks_replied_and_due_followup_even_with_lower_score() -> None:
    batch = DeterministicLeadDecisionService().decide(
        [
            _candidate("reply", status="replied", score=100),
            _candidate("due", status="contacted", score=90, contacted_at=AS_OF - timedelta(hours=48)),
            _candidate("proposal", status="contacted", score=10, contacted_at=AS_OF - timedelta(hours=48), commercial_stage="proposal"),
        ],
        _policy(max_work=3),
        as_of=AS_OF,
    )

    assert batch.selected_by_lane["facebook"] == ("proposal", "reply", "due")
    proposal = _by_id(batch)["proposal"]
    assert proposal.stage == LeadStage.PROPOSAL  # type: ignore[union-attr]
    assert proposal.commercial_stage == CommercialStage.PROPOSAL  # type: ignore[union-attr]
    assert proposal.next_action == LeadNextAction.FOLLOW_UP  # type: ignore[union-attr]


def test_qualified_outranks_reply_and_requests_proposal() -> None:
    batch = DeterministicLeadDecisionService().decide(
        [
            _candidate("reply", status="replied", score=99),
            _candidate("qualified", status="replied", score=20, commercial_stage="qualified"),
        ],
        _policy(max_work=2),
        as_of=AS_OF,
    )

    assert batch.selected_by_lane["facebook"] == ("qualified", "reply")
    qualified = _by_id(batch)["qualified"]
    assert qualified.stage == LeadStage.QUALIFIED  # type: ignore[union-attr]
    assert qualified.next_action == LeadNextAction.PROPOSE  # type: ignore[union-attr]


@pytest.mark.parametrize("commercial_stage", ["won", "lost"])
def test_explicit_terminal_outcome_is_complete_not_reject(commercial_stage: str) -> None:
    batch = DeterministicLeadDecisionService().decide(
        [_candidate(f"terminal-{commercial_stage}", status="closed", commercial_stage=commercial_stage)],
        _policy(),
        as_of=AS_OF,
    )
    decision = _by_id(batch)[f"terminal-{commercial_stage}"]

    assert decision.disposition == LeadDisposition.COMPLETE  # type: ignore[union-attr]
    assert decision.next_action == LeadNextAction.NONE  # type: ignore[union-attr]
    assert f"terminal-{commercial_stage}" in batch.completed_ids
    assert f"terminal-{commercial_stage}" not in batch.rejected_ids


def test_legacy_unknown_commercial_stage_keeps_existing_closeability_rules() -> None:
    batch = DeterministicLeadDecisionService().decide(
        [
            _candidate("due", status="contacted", score=1, contacted_at=AS_OF - timedelta(hours=48)),
            _candidate("strong-prepared", status="prepared", score=95),
            _candidate("weak-prepared", status="prepared", score=20),
        ],
        _policy(max_work=3, prepared_min_score=70),
        as_of=AS_OF,
    )

    assert batch.selected_by_lane["facebook"] == ("due", "strong-prepared")
    assert _by_id(batch)["weak-prepared"].disposition == LeadDisposition.HOLD  # type: ignore[union-attr]
    assert "prepared_below_quality_floor" in _by_id(batch)["weak-prepared"].reasons  # type: ignore[union-attr]


def test_next_actions_are_deterministic_by_stage() -> None:
    batch = DeterministicLeadDecisionService().decide(
        [
            _candidate("reply", status="replied"),
            _candidate("prepared", status="prepared"),
            _candidate("due", status="contacted", contacted_at=AS_OF - timedelta(hours=48)),
            _candidate("waiting", status="contacted", contacted_at=AS_OF - timedelta(hours=1)),
        ],
        _policy(max_work=4),
        as_of=AS_OF,
    )
    rows = _by_id(batch)

    assert rows["reply"].next_action == LeadNextAction.QUALIFY  # type: ignore[union-attr]
    assert rows["prepared"].next_action == LeadNextAction.CONTACT  # type: ignore[union-attr]
    assert rows["due"].next_action == LeadNextAction.FOLLOW_UP  # type: ignore[union-attr]
    assert rows["waiting"].next_action == LeadNextAction.WAIT  # type: ignore[union-attr]


def test_qualified_stage_without_matching_evidence_is_repair_data() -> None:
    batch = DeterministicLeadDecisionService().decide(
        [
            _candidate(
                "qualified-no-proof",
                status="replied",
                commercial_stage="qualified",
                commercial_evidence=[],
            )
        ],
        _policy(),
        as_of=AS_OF,
    )
    decision = _by_id(batch)["qualified-no-proof"]

    assert decision.disposition == LeadDisposition.REPAIR_DATA  # type: ignore[union-attr]
    assert "missing_commercial_stage_evidence" in decision.data_quality_issues  # type: ignore[union-attr]
    assert batch.selected_by_lane["facebook"] == ()


def test_proposal_stage_rejects_evidence_for_a_different_stage() -> None:
    batch = DeterministicLeadDecisionService().decide(
        [
            _candidate(
                "proposal-wrong-proof",
                status="replied",
                commercial_stage="proposal",
                commercial_evidence=[
                    {
                        "stage": "qualified",
                        "observed_at": AS_OF - timedelta(minutes=10),
                        "source_ref": "messenger:thread-1",
                        "summary": "Buyer need and scope confirmed.",
                    }
                ],
            )
        ],
        _policy(),
        as_of=AS_OF,
    )
    decision = _by_id(batch)["proposal-wrong-proof"]

    assert decision.disposition == LeadDisposition.REPAIR_DATA  # type: ignore[union-attr]
    assert "missing_commercial_stage_evidence" in decision.data_quality_issues  # type: ignore[union-attr]


def test_matching_proposal_evidence_unlocks_proposal_priority() -> None:
    batch = DeterministicLeadDecisionService().decide(
        [
            _candidate("reply", status="replied", score=100),
            _candidate(
                "proposal-proof",
                status="replied",
                score=1,
                commercial_stage="proposal",
                commercial_evidence=[
                    {
                        "stage": "proposal",
                        "observed_at": AS_OF - timedelta(minutes=5),
                        "source_ref": "messenger:thread-2",
                        "summary": "Proposal sent after buyer confirmed scope.",
                    }
                ],
            ),
        ],
        _policy(max_work=2),
        as_of=AS_OF,
    )

    assert batch.selected_by_lane["facebook"] == ("proposal-proof", "reply")
    proposal = _by_id(batch)["proposal-proof"]
    assert proposal.disposition == LeadDisposition.WORK_NOW  # type: ignore[union-attr]
    assert proposal.next_action == LeadNextAction.FOLLOW_UP  # type: ignore[union-attr]


def test_future_commercial_evidence_is_repair_data() -> None:
    batch = DeterministicLeadDecisionService().decide(
        [
            _candidate(
                "future-proof",
                status="replied",
                commercial_stage="qualified",
                commercial_evidence=[
                    {
                        "stage": "qualified",
                        "observed_at": AS_OF + timedelta(minutes=1),
                        "source_ref": "messenger:future",
                    }
                ],
            )
        ],
        _policy(),
        as_of=AS_OF,
    )
    decision = _by_id(batch)["future-proof"]

    assert decision.disposition == LeadDisposition.REPAIR_DATA  # type: ignore[union-attr]
    assert "commercial_evidence_after_as_of" in decision.data_quality_issues  # type: ignore[union-attr]


@pytest.mark.parametrize("commercial_stage", ["won", "lost"])
def test_terminal_commercial_stage_requires_matching_outcome_evidence(commercial_stage: str) -> None:
    without = DeterministicLeadDecisionService().decide(
        [
            _candidate(
                f"{commercial_stage}-no-proof",
                status="closed",
                commercial_stage=commercial_stage,
                commercial_evidence=[],
            )
        ],
        _policy(),
        as_of=AS_OF,
    )
    without_decision = _by_id(without)[f"{commercial_stage}-no-proof"]
    assert without_decision.disposition == LeadDisposition.REPAIR_DATA  # type: ignore[union-attr]

    with_proof = DeterministicLeadDecisionService().decide(
        [
            _candidate(
                f"{commercial_stage}-proof",
                status="closed",
                commercial_stage=commercial_stage,
                commercial_evidence=[
                    {
                        "stage": commercial_stage,
                        "observed_at": AS_OF - timedelta(minutes=1),
                        "source_ref": f"crm:{commercial_stage}",
                    }
                ],
            )
        ],
        _policy(),
        as_of=AS_OF,
    )
    with_decision = _by_id(with_proof)[f"{commercial_stage}-proof"]
    assert with_decision.disposition == LeadDisposition.COMPLETE  # type: ignore[union-attr]


def test_work_now_produces_auditable_closer_action_ticket() -> None:
    batch = DeterministicLeadDecisionService().decide(
        [
            _candidate("reply", status="replied", score=80),
            _candidate("weak", status="prepared", score=10),
        ],
        _policy(max_work=1, prepared_min_score=70),
        as_of=AS_OF,
    )

    assert len(batch.action_queue) == 1
    ticket = batch.action_queue[0]
    decision = _by_id(batch)["reply"]

    assert ticket.prospect_id == "reply"
    assert ticket.lane == "facebook"
    assert ticket.buyer == "Buyer"
    assert ticket.title == "Lead reply"
    assert ticket.source_url == "https://example.test/reply"
    assert ticket.direct_url == "https://example.test/reply/contact"
    assert ticket.next_action == LeadNextAction.QUALIFY
    assert ticket.commercial_stage == CommercialStage.UNKNOWN
    assert ticket.rank_position == 1
    assert ticket.decision_hash == decision.decision_hash  # type: ignore[union-attr]
    assert ticket.effect_scope == "commercial-outreach"
    assert ticket.requires_human_approval is True
    assert len(ticket.ticket_hash) == 64
    assert all(row.prospect_id != "weak" for row in batch.action_queue)


def test_non_work_dispositions_never_produce_action_tickets() -> None:
    batch = DeterministicLeadDecisionService().decide(
        [
            _candidate("rejected", scam_risk="high"),
            _candidate("repair", status="contacted", contacted_at=None),
            _candidate("completed", status="closed", commercial_stage="won"),
            _candidate("held", status="prepared", score=10),
        ],
        _policy(max_work=1, prepared_min_score=70),
        as_of=AS_OF,
    )

    assert batch.action_queue == ()


def test_action_ticket_hash_binds_contact_target_and_decision() -> None:
    service = DeterministicLeadDecisionService()
    base = _candidate("target", status="replied")
    changed_target = base.model_copy(update={"direct_url": "https://example.test/target/alternate"})

    left = service.decide([base], _policy(), as_of=AS_OF)
    right = service.decide([changed_target], _policy(), as_of=AS_OF)

    assert left.action_queue[0].ticket_hash != right.action_queue[0].ticket_hash
    assert left.action_queue[0].decision_hash != right.action_queue[0].decision_hash


def test_action_queue_is_input_order_invariant() -> None:
    service = DeterministicLeadDecisionService()
    candidates = [
        _candidate("fb-reply", status="replied", score=10),
        _candidate("fb-prepared", status="prepared", score=90),
        _candidate("rd-reply", lane="reddit", status="replied", score=20),
    ]

    left = service.decide(candidates, _policy(max_work=3), as_of=AS_OF)
    right = service.decide(list(reversed(candidates)), _policy(max_work=3), as_of=AS_OF)

    assert left.action_queue == right.action_queue
    assert left.batch_hash == right.batch_hash


def test_action_ticket_carries_source_brief_without_granting_authority() -> None:
    base = _candidate("brief", status="replied", score=80)
    enriched = base.model_copy(
        update={
            "source_brief": {
                "company": "Buyer Co",
                "location": "Remote",
                "need": "Need a bounded CRM cleanup this week",
                "category": "crm",
                "application_mode": "direct",
                "compensation_raw": "USD 150 fixed",
                "setter_reason": "buyer explicitly requested help",
            }
        }
    )

    batch = DeterministicLeadDecisionService().decide(
        [enriched],
        _policy(max_work=1),
        as_of=AS_OF,
    )

    ticket = batch.action_queue[0]
    assert ticket.source_brief.need == "Need a bounded CRM cleanup this week"
    assert ticket.source_brief.compensation_raw == "USD 150 fixed"
    assert ticket.requires_human_approval is True


def test_source_brief_changes_hash_but_not_stage_or_disposition() -> None:
    service = DeterministicLeadDecisionService()
    base = _candidate("brief-hash", status="replied", score=80)
    left_candidate = base.model_copy(
        update={"source_brief": {"need": "Need A"}}
    )
    right_candidate = base.model_copy(
        update={"source_brief": {"need": "Need B"}}
    )

    left = service.decide([left_candidate], _policy(max_work=1), as_of=AS_OF)
    right = service.decide([right_candidate], _policy(max_work=1), as_of=AS_OF)

    assert left.decisions[0].stage == right.decisions[0].stage == LeadStage.REPLIED
    assert left.decisions[0].disposition == right.decisions[0].disposition == LeadDisposition.WORK_NOW
    assert left.decisions[0].decision_hash != right.decisions[0].decision_hash
    assert left.action_queue[0].ticket_hash != right.action_queue[0].ticket_hash


@pytest.mark.parametrize(
    ("candidate", "goal_code", "target_lead_stage", "target_commercial_stages", "requires_evidence"),
    [
        (
            _candidate("goal-contact", status="prepared"),
            CommercialGoalCode.OBTAIN_REPLY,
            LeadStage.REPLIED,
            (),
            False,
        ),
        (
            _candidate("goal-qualify", status="replied"),
            CommercialGoalCode.QUALIFY,
            LeadStage.QUALIFIED,
            (CommercialStage.QUALIFIED,),
            True,
        ),
        (
            _candidate("goal-propose", status="replied", commercial_stage="qualified"),
            CommercialGoalCode.ADVANCE_TO_PROPOSAL,
            LeadStage.PROPOSAL,
            (CommercialStage.PROPOSAL,),
            True,
        ),
        (
            _candidate("goal-resolve", status="replied", commercial_stage="proposal"),
            CommercialGoalCode.RESOLVE_PROPOSAL,
            LeadStage.TERMINAL,
            (CommercialStage.WON, CommercialStage.LOST),
            True,
        ),
        (
            _candidate(
                "goal-followup",
                status="contacted",
                contacted_at=AS_OF - timedelta(hours=48),
            ),
            CommercialGoalCode.OBTAIN_REPLY,
            LeadStage.REPLIED,
            (),
            False,
        ),
    ],
)
def test_action_ticket_has_deterministic_success_goal(
    candidate: LeadCandidate,
    goal_code: CommercialGoalCode,
    target_lead_stage: LeadStage,
    target_commercial_stages: tuple[CommercialStage, ...],
    requires_evidence: bool,
) -> None:
    batch = DeterministicLeadDecisionService().decide(
        [candidate],
        _policy(max_work=1),
        as_of=AS_OF,
    )

    assert len(batch.action_queue) == 1
    ticket = batch.action_queue[0]
    assert ticket.goal.code == goal_code
    assert ticket.goal.target_lead_stage == target_lead_stage
    assert ticket.goal.target_commercial_stages == target_commercial_stages
    assert ticket.goal.requires_stage_evidence is requires_evidence
    assert ticket.requires_human_approval is True


def test_action_goal_is_bound_into_ticket_hash() -> None:
    service = DeterministicLeadDecisionService()
    due = _candidate(
        "goal-hash",
        status="contacted",
        contacted_at=AS_OF - timedelta(hours=48),
    )
    proposal = _candidate(
        "goal-hash",
        status="replied",
        commercial_stage="proposal",
    )

    due_batch = service.decide([due], _policy(max_work=1), as_of=AS_OF)
    proposal_batch = service.decide([proposal], _policy(max_work=1), as_of=AS_OF)

    assert due_batch.action_queue[0].goal.code == CommercialGoalCode.OBTAIN_REPLY
    assert proposal_batch.action_queue[0].goal.code == CommercialGoalCode.RESOLVE_PROPOSAL
    assert due_batch.action_queue[0].ticket_hash != proposal_batch.action_queue[0].ticket_hash
    assert due_batch.batch_hash != proposal_batch.batch_hash
