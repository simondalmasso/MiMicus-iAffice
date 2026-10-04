from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from typing import Any

from pydantic import ConfigDict, Field, model_validator

from mimicus.commercial.models import CommercialTraceEvent, LeadDecisionBatch, LeadDecisionPolicy
from mimicus.commercial.prospect_ingest import normalize_ledger
from mimicus.orchestration.legacy_engine import (
    MiMicusEngine as LegacyMiMicusEngine,
)
from mimicus.orchestration.legacy_engine import (
    RunRequest as LegacyRunRequest,
)
from mimicus.orchestration.legacy_engine import (
    RunResult as LegacyRunResult,
)
from mimicus.orchestration.legacy_engine import (
    _fingerprint,
    _spec_keys,
    _trust_from_row,
    default_candidates,
    scenario_fixture,
)
from mimicus.orchestration.production_core import execute_production_core
from mimicus.orchestration.semantic_replay import semantic_replay
from mimicus.providers.base import Provider, ProviderCapabilities, ProviderRequest, ProviderResponse
from mimicus.storage.swarm_state import SwarmStateStore
from mimicus.verification.models import VerificationSubmission
from mimicus.verification.service import submit_verification


class _FixtureCompatibilityProvider(Provider):
    """Keep the explicit fixture lane on its historical claim-ref contract."""

    def __init__(self, delegate: Provider) -> None:
        self.delegate = delegate

    @property
    def capabilities(self) -> ProviderCapabilities:
        return self.delegate.capabilities

    async def generate_request_async(self, request: ProviderRequest) -> ProviderResponse:
        response = await self.delegate.generate_request_async(request)
        return replace(response, claim=response.claim.model_copy(update={"evidence_refs": []}))

    async def audition_async(self, request: Any) -> Any:
        return await self.delegate.audition_async(request)

    async def challenge_async(self, request: Any) -> Any:
        return await self.delegate.challenge_async(request)


class RunRequest(LegacyRunRequest):
    model_config = ConfigDict(extra="forbid")
    # Python runtime API preserves historical verified-learning behavior by
    # default. CLI/MCP pass their explicit public learn=False default, while an
    # explicit False here remains fully authoritative and mutation-inert.
    learn: bool = True
    # Compatibility marker only. It cannot disable accepted semantics in runtime.
    core_semantics: bool | None = None

    @model_validator(mode="after")
    def normal_runtime_is_core_locked(self) -> RunRequest:
        if self.source_mode == "runtime" and self.core_semantics is False:
            raise ValueError("normal runtime cannot disable swarm-core semantics")
        if self.source_mode == "runtime" and self.fixture:
            raise ValueError("fixture material is not accepted in normal runtime; use explicit source_mode=fixture compatibility lane")
        return self


class RunResult(LegacyRunResult):
    model_config = ConfigDict(extra="forbid")
    swarm_decision: dict[str, Any] = Field(default_factory=dict)
    subtasks: list[dict[str, Any]] = Field(default_factory=list)
    threat_profile: dict[str, Any] = Field(default_factory=dict)
    hierarchy_execution: dict[str, Any] = Field(default_factory=dict)
    persistent_state: dict[str, Any] = Field(default_factory=dict)
    learning_policy: dict[str, Any] = Field(default_factory=dict)
    production_core: dict[str, Any] = Field(default_factory=dict)
    progress: list[dict[str, Any]] = Field(default_factory=list)
    semantic_replay: dict[str, Any] = Field(default_factory=dict)


class MiMicusEngine(LegacyMiMicusEngine):
    def triage_prospects(
        self,
        payload: dict[str, Any],
        *,
        policy: LeadDecisionPolicy,
        as_of: datetime,
        trace_sink: Callable[[CommercialTraceEvent], None] | None = None,
    ) -> LeadDecisionBatch:
        candidates = normalize_ledger(payload)
        sequence = 0

        def emit(event: CommercialTraceEvent) -> None:
            if trace_sink is None:
                return
            try:
                trace_sink(event)
            except Exception:
                # Observability is explicitly non-authoritative. A broken viewer
                # cannot block or alter the commercial decision.
                return

        for candidate in candidates:
            sequence += 1
            emit(
                CommercialTraceEvent(
                    sequence=sequence,
                    event="lead_ingested",
                    as_of=as_of,
                    prospect_id=candidate.prospect_id,
                    lane=candidate.lane,
                    source_name=candidate.source_name,
                    outreach_status=candidate.outreach_status,
                    setter_score=candidate.setter_score,
                    scam_risk=candidate.scam_risk,
                    active=candidate.active,
                )
            )
            sequence += 1
            emit(
                CommercialTraceEvent(
                    sequence=sequence,
                    event="laya_reading",
                    as_of=as_of,
                    prospect_id=candidate.prospect_id,
                    lane=candidate.lane,
                    source_name=candidate.source_name,
                    outreach_status=candidate.outreach_status,
                    setter_score=candidate.setter_score,
                    scam_risk=candidate.scam_risk,
                    active=candidate.active,
                    commercial_stage=candidate.commercial.stage,
                    commercial_evidence_count=len(candidate.commercial.evidence),
                    commercial_stage_evidenced=any(
                        evidence.stage == candidate.commercial.stage
                        for evidence in candidate.commercial.evidence
                    ),
                    policy_version=policy.version,
                )
            )

        service = self.services.lead_decision
        if service is None:
            raise RuntimeError("lead decision service is not mounted")
        batch = service.decide(candidates, policy, as_of=as_of)

        for decision in batch.decisions:
            sequence += 1
            emit(
                CommercialTraceEvent(
                    sequence=sequence,
                    event="decision_emitted",
                    as_of=as_of,
                    prospect_id=decision.prospect_id,
                    lane=decision.lane,
                    policy_version=policy.version,
                    disposition=decision.disposition,
                    stage=decision.stage,
                    commercial_stage=decision.commercial_stage,
                    next_action=decision.next_action,
                    rank_position=decision.rank_position,
                    reasons=decision.reasons,
                    data_quality_issues=decision.data_quality_issues,
                )
            )
        return batch

    async def run_async(self, request: LegacyRunRequest) -> RunResult:
        core_request = request if isinstance(request, RunRequest) else RunRequest.model_validate(request.model_dump(mode="json"))
        if core_request.source_mode != "fixture":
            return RunResult.model_validate(await execute_production_core(self, core_request))
        # Explicit compatibility lane only; MCP and normal CLI do not expose it.
        legacy_request = LegacyRunRequest.model_validate(core_request.model_dump(mode="json", exclude={"core_semantics"}))
        original_provider = self.provider
        self.provider = _FixtureCompatibilityProvider(original_provider)
        try:
            legacy = await super().run_async(legacy_request)
        finally:
            self.provider = original_provider
        return RunResult.model_validate(legacy.model_dump(mode="json"))

    def register_verifier_authority(
        self,
        *,
        verifier_id: str,
        authority_class: str,
        source_independence_cluster: str,
        auth_token: str,
        verification_method: str = "run_bound_token",
    ) -> dict[str, Any]:
        """Administrative/internal trust provisioning; intentionally not MCP/CLI-exposed."""
        store = SwarmStateStore(self.repository.engine)
        return store.register_verifier_authority(
            verifier_id=verifier_id,
            authority_class=authority_class,
            source_cluster=source_independence_cluster,
            verification_method=verification_method,
            auth_token=auth_token,
        )

    def submit_verification(self, submission: VerificationSubmission | dict[str, Any]) -> dict[str, Any]:
        parsed = submission if isinstance(submission, VerificationSubmission) else VerificationSubmission.model_validate(submission)
        return submit_verification(self, parsed)

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        result = super().get_run(run_id)
        if result is None:
            return None
        store = SwarmStateStore(self.repository.engine)
        replay = result["replay_state"] if result.get("evidence_provenance", {}).get("source_mode") == "fixture" else semantic_replay(self.repository, run_id)
        return result | {
            "verification_receipts": store.receipts_for_run(run_id),
            "swarm_learning": store.learned_state(),
            "replay_state": replay,
        }


__all__ = [
    "MiMicusEngine",
    "RunRequest",
    "RunResult",
    "_fingerprint",
    "_spec_keys",
    "_trust_from_row",
    "default_candidates",
    "scenario_fixture",
]
