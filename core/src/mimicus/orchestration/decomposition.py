from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from mimicus.canonical import sha256_obj
from mimicus.coalition.threat_profile import ThreatProfile


class Subtask(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    subtask_id: str
    objective: str
    required_capabilities: tuple[str, ...]
    evidence_scope: tuple[str, ...]
    dependency_group: str
    parent_task_hash: str

    @property
    def hash(self) -> str:
        return sha256_obj(self)


def decompose_task(task_hash: str, profile: ThreatProfile, evidence_facts: dict[str, Any]) -> list[Subtask]:
    """Deterministic structural decomposition; no answer-bearing or role-theater switches."""
    capabilities = list(profile.required_capabilities)
    if len(capabilities) < 2:
        return []
    scope_by_cap = {
        "numeric": ("price", "users", "price_period", "claimed", "claim_figure"),
        "freshness": ("evidence_date", "as_of"),
        "source": ("clusters", "texts", "evidence_spans"),
        "independence": ("clusters", "texts"),
        "entailment": ("claim_figure", "evidence_spans"),
        "counterexample": ("absence_key", "registry", "registry_snapshot_hash"),
        "synthesize": tuple(sorted(evidence_facts)),
    }
    rows: list[Subtask] = []
    for index, capability in enumerate(capabilities):
        available_scope = tuple(key for key in scope_by_cap.get(capability, tuple(sorted(evidence_facts))) if key in evidence_facts)
        objective = f"Evaluate the {capability} subproblem using only its structured evidence scope; return a bounded claim."
        material = {"parent": task_hash, "capability": capability, "scope": available_scope, "index": index}
        rows.append(
            Subtask(
                subtask_id=f"subtask-{index:02d}-{sha256_obj(material)[:12]}",
                objective=objective,
                required_capabilities=(capability,),
                evidence_scope=available_scope,
                dependency_group=f"capability-{index % 2}",
                parent_task_hash=task_hash,
            )
        )
    return rows
