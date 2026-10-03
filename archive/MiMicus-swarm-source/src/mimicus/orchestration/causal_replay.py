from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from mimicus.canonical import sha256_obj
from mimicus.orchestration.dag_executor import DagExecution
from mimicus.orchestration.morphology import MorphologyPlan

_CAUSAL_VERSION = "mimicus-causal-execution-v1"
_SUCCESS_STATES = {"COMPLETED", "PRECOMPLETED"}


def _hash64(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value.lower())


def _causal_input_hash(declared_input_hash: str, prerequisite_output_hashes: Mapping[str, str]) -> str:
    return sha256_obj(
        {
            "declared_input_hash": declared_input_hash,
            "prerequisite_output_hashes": dict(sorted(prerequisite_output_hashes.items())),
        }
    )


def build_causal_execution(
    plan: MorphologyPlan,
    execution: DagExecution,
    *,
    precompleted_ids: set[str] | frozenset[str] = frozenset(),
    effect_decisions: list[dict[str, Any]] | tuple[dict[str, Any], ...] = (),
    incidental: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a semantic causal record from one successful DAG execution.

    Runtime timings, scheduler turns, run IDs and timestamps belong in the
    incidental section and never participate in semantic_hash.
    """

    plan.validate()
    node_ids = {node.node_id for node in plan.nodes}
    unknown_precompleted = set(precompleted_ids) - node_ids
    if unknown_precompleted:
        raise ValueError(f"precompleted node is not in plan: {sorted(unknown_precompleted)}")

    rows: list[dict[str, Any]] = []
    for node in sorted(plan.nodes, key=lambda item: item.node_id):
        output_hash = execution.output_hashes.get(node.node_id)
        if not _hash64(output_hash):
            raise ValueError(f"successful causal record requires output hash for node {node.node_id}")
        assert isinstance(output_hash, str)

        prerequisites = tuple(node.prerequisites)
        prerequisite_hashes: dict[str, str] = {}
        for parent in prerequisites:
            parent_hash = execution.output_hashes.get(parent)
            if not _hash64(parent_hash):
                raise ValueError(f"missing prerequisite output hash for {node.node_id}: {parent}")
            assert isinstance(parent_hash, str)
            prerequisite_hashes[parent] = parent_hash

        status = "PRECOMPLETED" if node.node_id in precompleted_ids else "COMPLETED"
        rows.append(
            {
                "node_id": node.node_id,
                "kind": node.kind.value,
                "prerequisites": list(prerequisites),
                "declared_input_hash": node.input_hash,
                "prerequisite_output_hashes": dict(sorted(prerequisite_hashes.items())),
                "causal_input_hash": _causal_input_hash(node.input_hash, prerequisite_hashes),
                "output_hash": output_hash,
                "status": status,
            }
        )

    normalized_effects = sorted(
        (deepcopy(dict(row)) for row in effect_decisions),
        key=sha256_obj,
    )
    semantic = {
        "version": _CAUSAL_VERSION,
        "plan_hash": plan.plan_hash,
        "nodes": rows,
        "effect_decisions": normalized_effects,
    }
    return {
        "semantic": semantic,
        "semantic_hash": sha256_obj(semantic),
        "incidental": deepcopy(dict(incidental or {})),
    }


def verify_causal_execution(record: Mapping[str, Any]) -> dict[str, object]:
    semantic = record.get("semantic")
    semantic_hash = record.get("semantic_hash")
    if not isinstance(semantic, dict):
        return {"verified": False, "semantic_hash": semantic_hash, "reason": "causal semantic record missing"}
    if not _hash64(semantic_hash) or sha256_obj(semantic) != semantic_hash:
        return {"verified": False, "semantic_hash": semantic_hash, "reason": "causal semantic hash mismatch"}
    if semantic.get("version") != _CAUSAL_VERSION:
        return {"verified": False, "semantic_hash": semantic_hash, "reason": "unsupported causal record version"}
    if not _hash64(semantic.get("plan_hash")):
        return {"verified": False, "semantic_hash": semantic_hash, "reason": "causal plan hash invalid"}

    raw_nodes = semantic.get("nodes")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        return {"verified": False, "semantic_hash": semantic_hash, "reason": "causal nodes missing"}

    nodes: dict[str, dict[str, Any]] = {}
    for raw in raw_nodes:
        if not isinstance(raw, dict):
            return {"verified": False, "semantic_hash": semantic_hash, "reason": "causal node malformed"}
        node_id = raw.get("node_id")
        if not isinstance(node_id, str) or not node_id:
            return {"verified": False, "semantic_hash": semantic_hash, "reason": "causal node id invalid"}
        if node_id in nodes:
            return {"verified": False, "semantic_hash": semantic_hash, "reason": f"duplicate causal node: {node_id}"}
        if raw.get("status") not in _SUCCESS_STATES:
            return {"verified": False, "semantic_hash": semantic_hash, "reason": f"causal node status invalid: {node_id}"}
        if not _hash64(raw.get("output_hash")):
            return {"verified": False, "semantic_hash": semantic_hash, "reason": f"causal output hash invalid: {node_id}"}
        if not isinstance(raw.get("declared_input_hash"), str):
            return {"verified": False, "semantic_hash": semantic_hash, "reason": f"causal declared input invalid: {node_id}"}
        prerequisites = raw.get("prerequisites")
        prerequisite_hashes = raw.get("prerequisite_output_hashes")
        if not isinstance(prerequisites, list) or not all(isinstance(value, str) for value in prerequisites):
            return {"verified": False, "semantic_hash": semantic_hash, "reason": f"causal prerequisites invalid: {node_id}"}
        if not isinstance(prerequisite_hashes, dict):
            return {"verified": False, "semantic_hash": semantic_hash, "reason": f"causal prerequisite outputs invalid: {node_id}"}
        nodes[node_id] = raw

    incoming = {node_id: 0 for node_id in nodes}
    outgoing: dict[str, list[str]] = {node_id: [] for node_id in nodes}
    for node_id, row in nodes.items():
        prerequisites = list(row["prerequisites"])
        hashes = row["prerequisite_output_hashes"]
        if set(hashes) != set(prerequisites):
            return {"verified": False, "semantic_hash": semantic_hash, "reason": f"prerequisite output set mismatch: {node_id}"}
        for parent in prerequisites:
            if parent not in nodes:
                return {"verified": False, "semantic_hash": semantic_hash, "reason": f"missing causal prerequisite: {parent}"}
            if hashes[parent] != nodes[parent]["output_hash"]:
                return {"verified": False, "semantic_hash": semantic_hash, "reason": f"prerequisite output hash mismatch: {node_id}:{parent}"}
            incoming[node_id] += 1
            outgoing[parent].append(node_id)

        expected_input = _causal_input_hash(
            str(row["declared_input_hash"]),
            {str(key): str(value) for key, value in hashes.items()},
        )
        if row.get("causal_input_hash") != expected_input:
            return {"verified": False, "semantic_hash": semantic_hash, "reason": f"causal input hash mismatch: {node_id}"}

    ready = sorted(node_id for node_id, degree in incoming.items() if degree == 0)
    seen: list[str] = []
    while ready:
        current = ready.pop(0)
        seen.append(current)
        for child in sorted(outgoing[current]):
            incoming[child] -= 1
            if incoming[child] == 0:
                ready.append(child)
                ready.sort()
    if len(seen) != len(nodes):
        return {"verified": False, "semantic_hash": semantic_hash, "reason": "causal dependency cycle"}

    effects = semantic.get("effect_decisions")
    if not isinstance(effects, list) or not all(isinstance(row, dict) for row in effects):
        return {"verified": False, "semantic_hash": semantic_hash, "reason": "causal effect decisions malformed"}

    return {"verified": True, "semantic_hash": semantic_hash, "reason": None}
