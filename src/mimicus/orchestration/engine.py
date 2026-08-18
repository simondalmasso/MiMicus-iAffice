from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field

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
from mimicus.orchestration.swarm_core import execute_swarm_core
from mimicus.storage.swarm_state import SwarmStateStore
from mimicus.verification.models import VerificationSubmission
from mimicus.verification.service import submit_verification


class RunRequest(LegacyRunRequest):
    model_config = ConfigDict(extra="forbid")
    core_semantics: bool | None = None


class RunResult(LegacyRunResult):
    model_config = ConfigDict(extra="forbid")
    swarm_decision: dict[str, Any] = Field(default_factory=dict)
    subtasks: list[dict[str, Any]] = Field(default_factory=list)
    threat_profile: dict[str, Any] = Field(default_factory=dict)


class MiMicusEngine(LegacyMiMicusEngine):
    async def run_async(self, request: LegacyRunRequest) -> RunResult:
        core_request = request if isinstance(request, RunRequest) else RunRequest.model_validate(request.model_dump(mode="json"))
        use_core = (
            core_request.core_semantics
            if core_request.core_semantics is not None
            else core_request.source_mode == "benchmark" or (core_request.source_mode == "runtime" and not core_request.fixture)
        )
        if use_core:
            return RunResult.model_validate(await execute_swarm_core(self, core_request))
        legacy = await super().run_async(request)
        return RunResult.model_validate(legacy.model_dump(mode="json"))

    def submit_verification(self, submission: VerificationSubmission | dict[str, Any]) -> dict[str, Any]:
        parsed = submission if isinstance(submission, VerificationSubmission) else VerificationSubmission.model_validate(submission)
        return submit_verification(self, parsed)

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        result = super().get_run(run_id)
        if result is None:
            return None
        store = SwarmStateStore(self.repository.engine)
        return result | {
            "verification_receipts": store.receipts_for_run(run_id),
            "swarm_learning": store.learned_state(),
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
