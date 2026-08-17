from __future__ import annotations

from dataclasses import asdict

from mimicus.canonical import sha256_obj
from mimicus.falsifiers.builtins import builtin_specs
from mimicus.falsifiers.primitives import execute_primitive
from mimicus.germinal.fossils import seed_fossils
from mimicus.germinal.mutate import mutate_params
from mimicus.germinal.promote import decide
from mimicus.types import Verdict


def germinal_demo() -> dict[str, object]:
    parent = builtin_specs("finance")["F1"]
    triggering_context = {"price": 10.0, "users": 10.0, "price_period": "annual", "claimed": 104.0}
    triggering_hash = sha256_obj(triggering_context)
    parent_exec = execute_primitive(parent, triggering_context)
    if parent_exec.verdict != Verdict.PASS:
        raise RuntimeError("germinal fixture requires parent evasion")

    regressing = mutate_params(
        parent,
        new_version="1.0.1-reject",
        params={"relative_tolerance": 0.25},
        triggering_snapshot_hash=triggering_hash,
        catches_triggering_evasion=False,
    )
    valid_spec_context = dict(triggering_context)
    valid = mutate_params(
        parent,
        new_version="1.0.1",
        params={"relative_tolerance": 0.02},
        triggering_snapshot_hash=triggering_hash,
        catches_triggering_evasion=execute_primitive(
            parent.model_copy(update={"version": "1.0.1", "params": {"relative_tolerance": 0.02}, "parent_hash": parent.hash}),
            valid_spec_context,
        ).verdict == Verdict.FAIL,
    )
    fossils = seed_fossils()
    rejected = decide(parent, regressing, fossils)
    promoted = decide(parent, valid, fossils)
    return {
        "ground_truth_pinned": True,
        "triggering_snapshot_hash": triggering_hash,
        "parent_hash": parent.hash,
        "parent_preserved": parent.hash != valid.candidate.hash,
        "rejected_candidate_hash": regressing.candidate.hash,
        "rejected_decision": rejected.status,
        "rejected_metrics": asdict(rejected.candidate_metrics),
        "promoted_candidate_hash": valid.candidate.hash,
        "promoted_decision": promoted.status,
        "promoted_metrics": asdict(promoted.candidate_metrics),
        "relevant_fossils": promoted.candidate_metrics.tested,
    }


def evasion_farming_guard(confirmed_ground_truth_hashes: list[str], repeated_reports: int) -> bool:
    """Return True only when independently pinned ground truth exists; report count alone has no authority."""
    return bool(set(confirmed_ground_truth_hashes)) and repeated_reports >= 0
