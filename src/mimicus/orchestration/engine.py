from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, Field, model_validator

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
from mimicus.storage.swarm_state import SwarmStateStore
from mimicus.verification.models import VerificationSubmission
from mimicus.verification.service import submit_verification


class RunRequest(LegacyRunRequest):
    model_config = ConfigDict(extra="forbid")
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
    async def run_async(self, request: LegacyRunRequest) -> RunResult:
        core_request = request if isinstance(request, RunRequest) else RunRequest.model_validate(request.model_dump(mode="json"))
        if core_request.source_mode != "fixture":
            return RunResult.model_validate(await execute_production_core(self, core_request))
        # Explicit compatibility lane only; MCP and normal CLI do not expose it.
        legacy_request = LegacyRunRequest.model_validate(core_request.model_dump(mode="json", exclude={"core_semantics"}))
        legacy = await super().run_async(legacy_request)
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
        replay = semantic_replay(self.repository, run_id)
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
