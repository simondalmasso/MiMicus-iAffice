from __future__ import annotations

from dataclasses import dataclass

from mimicus.falsifiers.spec import FalsifierSpec


@dataclass(frozen=True)
class MutationCandidate:
    parent_hash: str
    candidate: FalsifierSpec
    triggering_snapshot_hash: str
    catches_triggering_evasion: bool


def mutate_params(parent: FalsifierSpec, *, new_version: str, params: dict[str, object], triggering_snapshot_hash: str, catches_triggering_evasion: bool) -> MutationCandidate:
    payload = parent.model_dump()
    payload.update({"version": new_version, "params": params, "parent_hash": parent.hash})
    candidate = FalsifierSpec.model_validate(payload)
    return MutationCandidate(parent.hash, candidate, triggering_snapshot_hash, catches_triggering_evasion)
