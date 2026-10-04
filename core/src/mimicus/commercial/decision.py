from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from mimicus.canonical import sha256_obj
from mimicus.commercial.models import (
    CommercialStage,
    LeadCandidate,
    LeadDecision,
    LeadDecisionBatch,
    LeadDecisionPolicy,
    LeadDisposition,
    LeadNextAction,
    LeadStage,
)


@dataclass(frozen=True)
class _Assessment:
    candidate: LeadCandidate
    stage: LeadStage
    commercial_stage: CommercialStage
    next_action: LeadNextAction
    disposition: LeadDisposition
    reasons: tuple[str, ...] = ()
    issues: tuple[str, ...] = ()


class DeterministicLeadDecisionService:
    def decide(
        self,
        candidates: list[LeadCandidate],
        policy: LeadDecisionPolicy,
        *,
        as_of: datetime,
    ) -> LeadDecisionBatch:
        if as_of.utcoffset() is None:
            raise ValueError("as_of must include timezone information")

        ids = [candidate.prospect_id for candidate in candidates]
        duplicates = sorted({prospect_id for prospect_id in ids if ids.count(prospect_id) > 1})
        if duplicates:
            raise ValueError(f"duplicate prospect_id values: {duplicates}")

        policy_hash = sha256_obj(policy)
        assessments = [self._assess(candidate, policy, as_of=as_of) for candidate in candidates]
        decisions: list[LeadDecision] = []
        selected_by_lane: dict[str, tuple[str, ...]] = {"facebook": (), "reddit": ()}

        for lane in ("facebook", "reddit"):
            lane_assessments = [
                assessment
                for assessment in assessments
                if assessment.candidate.lane == lane
                and assessment.disposition == LeadDisposition.HOLD
            ]
            ranked = sorted(lane_assessments, key=lambda item: self._rank_key(item, policy))
            selected: list[str] = []

            for rank_position, assessment in enumerate(ranked, start=1):
                disposition = LeadDisposition.HOLD
                reasons = assessment.reasons
                if assessment.stage == LeadStage.CONTACTED_WAITING:
                    reasons = (*reasons, "follow_up_not_due")
                elif len(selected) < policy.max_work_per_lane:
                    disposition = LeadDisposition.WORK_NOW
                    selected.append(assessment.candidate.prospect_id)
                    reasons = (*reasons, "within_lane_wip")
                else:
                    reasons = (*reasons, "lane_wip_exhausted")

                decisions.append(
                    self._decision(
                        assessment,
                        policy_hash=policy_hash,
                        as_of=as_of,
                        disposition=disposition,
                        rank_position=rank_position,
                        reasons=reasons,
                    )
                )

            selected_by_lane[lane] = tuple(selected)

        ranked_ids = {decision.prospect_id for decision in decisions}
        for assessment in assessments:
            if assessment.candidate.prospect_id in ranked_ids:
                continue
            decisions.append(
                self._decision(
                    assessment,
                    policy_hash=policy_hash,
                    as_of=as_of,
                    disposition=assessment.disposition,
                    rank_position=None,
                    reasons=assessment.reasons,
                )
            )

        canonical_decisions = tuple(
            sorted(
                decisions,
                key=lambda decision: (
                    decision.lane,
                    decision.rank_position is None,
                    decision.rank_position or 0,
                    decision.prospect_id,
                ),
            )
        )
        held_ids = tuple(
            sorted(
                decision.prospect_id
                for decision in canonical_decisions
                if decision.disposition == LeadDisposition.HOLD
            )
        )
        rejected_ids = tuple(
            sorted(
                decision.prospect_id
                for decision in canonical_decisions
                if decision.disposition == LeadDisposition.REJECT
            )
        )
        repair_data_ids = tuple(
            sorted(
                decision.prospect_id
                for decision in canonical_decisions
                if decision.disposition == LeadDisposition.REPAIR_DATA
            )
        )
        completed_ids = tuple(
            sorted(
                decision.prospect_id
                for decision in canonical_decisions
                if decision.disposition == LeadDisposition.COMPLETE
            )
        )
        semantic_batch = {
            "as_of": as_of.isoformat(),
            "input_ids": sorted(ids),
            "decisions": [decision.model_dump(mode="json") for decision in canonical_decisions],
            "selected_by_lane": selected_by_lane,
            "held_ids": held_ids,
            "rejected_ids": rejected_ids,
            "repair_data_ids": repair_data_ids,
            "completed_ids": completed_ids,
            "policy_hash": policy_hash,
        }
        return LeadDecisionBatch(
            input_ids=tuple(sorted(ids)),
            decisions=canonical_decisions,
            selected_by_lane=selected_by_lane,
            held_ids=held_ids,
            rejected_ids=rejected_ids,
            repair_data_ids=repair_data_ids,
            completed_ids=completed_ids,
            policy_hash=policy_hash,
            batch_hash=sha256_obj(semantic_batch),
        )

    def _assess(
        self,
        candidate: LeadCandidate,
        policy: LeadDecisionPolicy,
        *,
        as_of: datetime,
    ) -> _Assessment:
        status = candidate.outreach_status.strip().lower()
        commercial_stage = candidate.commercial.stage

        if commercial_stage in {CommercialStage.WON, CommercialStage.LOST}:
            return _Assessment(
                candidate=candidate,
                stage=LeadStage.TERMINAL,
                commercial_stage=commercial_stage,
                next_action=LeadNextAction.NONE,
                disposition=LeadDisposition.COMPLETE,
                reasons=(f"commercial:{commercial_stage.value}",),
            )
        if status == "closed":
            return _Assessment(
                candidate=candidate,
                stage=LeadStage.TERMINAL,
                commercial_stage=commercial_stage,
                next_action=LeadNextAction.NONE,
                disposition=LeadDisposition.REJECT,
                reasons=("terminal_status",),
            )
        if not candidate.active:
            return _Assessment(
                candidate=candidate,
                stage=self._known_stage(status),
                commercial_stage=commercial_stage,
                next_action=LeadNextAction.NONE,
                disposition=LeadDisposition.REJECT,
                reasons=("inactive",),
            )
        if policy.require_argentina_eligible and candidate.argentina_eligible is False:
            return _Assessment(
                candidate=candidate,
                stage=self._known_stage(status),
                commercial_stage=commercial_stage,
                next_action=LeadNextAction.NONE,
                disposition=LeadDisposition.REJECT,
                reasons=("argentina_ineligible",),
            )
        if policy.reject_worker_fee and candidate.worker_fee is True:
            return _Assessment(
                candidate=candidate,
                stage=self._known_stage(status),
                commercial_stage=commercial_stage,
                next_action=LeadNextAction.NONE,
                disposition=LeadDisposition.REJECT,
                reasons=("worker_fee",),
            )
        if policy.reject_high_scam and candidate.scam_risk == "high":
            return _Assessment(
                candidate=candidate,
                stage=self._known_stage(status),
                commercial_stage=commercial_stage,
                next_action=LeadNextAction.NONE,
                disposition=LeadDisposition.REJECT,
                reasons=("high_scam_risk",),
            )

        issues: list[str] = []
        if policy.require_argentina_eligible and candidate.argentina_eligible is None:
            issues.append("missing_argentina_eligibility")
        if policy.reject_worker_fee and candidate.worker_fee is None:
            issues.append("missing_worker_fee")
        if not candidate.buyer:
            issues.append("missing_buyer")
        if not candidate.source_url:
            issues.append("missing_source_url")
        if not candidate.direct_url:
            issues.append("missing_direct_url")

        if commercial_stage == CommercialStage.PROPOSAL:
            stage = LeadStage.PROPOSAL
        elif commercial_stage == CommercialStage.QUALIFIED:
            stage = LeadStage.QUALIFIED
        elif status == "replied":
            stage = LeadStage.REPLIED
        elif status == "prepared":
            stage = LeadStage.PREPARED
        elif status == "contacted":
            if candidate.contacted_at is None:
                issues.append("missing_contacted_at")
                stage = LeadStage.UNKNOWN
            elif candidate.outreach_channel is None:
                issues.append("missing_outreach_channel")
                stage = LeadStage.UNKNOWN
            elif candidate.outreach_channel not in policy.follow_up_after_hours:
                issues.append("missing_follow_up_threshold")
                stage = LeadStage.UNKNOWN
            elif candidate.contacted_at > as_of:
                issues.append("contacted_at_after_as_of")
                stage = LeadStage.UNKNOWN
            else:
                elapsed_hours = (as_of - candidate.contacted_at).total_seconds() / 3600
                threshold = policy.follow_up_after_hours[candidate.outreach_channel]
                stage = (
                    LeadStage.CONTACTED_DUE
                    if elapsed_hours >= threshold
                    else LeadStage.CONTACTED_WAITING
                )
        else:
            issues.append("unknown_outreach_status")
            stage = LeadStage.UNKNOWN

        if issues:
            return _Assessment(
                candidate=candidate,
                stage=stage,
                commercial_stage=commercial_stage,
                next_action=LeadNextAction.NONE,
                disposition=LeadDisposition.REPAIR_DATA,
                issues=tuple(sorted(set(issues))),
            )

        return _Assessment(
            candidate=candidate,
            stage=stage,
            commercial_stage=commercial_stage,
            next_action=self._next_action(stage),
            disposition=LeadDisposition.HOLD,
            reasons=(f"stage:{stage.value}",),
        )

    @staticmethod
    def _next_action(stage: LeadStage) -> LeadNextAction:
        return {
            LeadStage.PROPOSAL: LeadNextAction.FOLLOW_UP,
            LeadStage.QUALIFIED: LeadNextAction.PROPOSE,
            LeadStage.REPLIED: LeadNextAction.QUALIFY,
            LeadStage.PREPARED: LeadNextAction.CONTACT,
            LeadStage.CONTACTED_DUE: LeadNextAction.FOLLOW_UP,
            LeadStage.CONTACTED_WAITING: LeadNextAction.WAIT,
            LeadStage.TERMINAL: LeadNextAction.NONE,
            LeadStage.UNKNOWN: LeadNextAction.NONE,
        }[stage]

    @staticmethod
    def _known_stage(status: str) -> LeadStage:
        return {
            "replied": LeadStage.REPLIED,
            "prepared": LeadStage.PREPARED,
            "contacted": LeadStage.UNKNOWN,
            "closed": LeadStage.TERMINAL,
        }.get(status, LeadStage.UNKNOWN)

    @staticmethod
    def _rank_key(
        assessment: _Assessment,
        policy: LeadDecisionPolicy,
    ) -> tuple[int, int, int, float, float, str]:
        precedence = {stage: index for index, stage in enumerate(policy.stage_precedence)}
        risk_order = {"low": 0, "medium": 1, "high": 2}
        candidate = assessment.candidate
        metadata_complete = int(
            not all((candidate.buyer, candidate.source_url, candidate.direct_url))
        )
        return (
            precedence.get(assessment.stage, len(precedence)),
            risk_order[candidate.scam_risk],
            metadata_complete,
            -candidate.setter_score,
            -candidate.verified_at.timestamp(),
            candidate.prospect_id,
        )

    @staticmethod
    def _decision(
        assessment: _Assessment,
        *,
        policy_hash: str,
        as_of: datetime,
        disposition: LeadDisposition,
        rank_position: int | None,
        reasons: tuple[str, ...],
    ) -> LeadDecision:
        input_hash = sha256_obj(assessment.candidate)
        payload = {
            "prospect_id": assessment.candidate.prospect_id,
            "lane": assessment.candidate.lane,
            "disposition": disposition.value,
            "stage": assessment.stage.value,
            "commercial_stage": assessment.commercial_stage.value,
            "next_action": assessment.next_action.value,
            "rank_position": rank_position,
            "reasons": reasons,
            "data_quality_issues": assessment.issues,
            "input_hash": input_hash,
            "policy_hash": policy_hash,
            "as_of": as_of.isoformat(),
        }
        return LeadDecision(
            prospect_id=assessment.candidate.prospect_id,
            lane=assessment.candidate.lane,
            disposition=disposition,
            stage=assessment.stage,
            commercial_stage=assessment.commercial_stage,
            next_action=assessment.next_action,
            rank_position=rank_position,
            reasons=reasons,
            data_quality_issues=assessment.issues,
            input_hash=input_hash,
            policy_hash=policy_hash,
            decision_hash=sha256_obj(payload),
        )
