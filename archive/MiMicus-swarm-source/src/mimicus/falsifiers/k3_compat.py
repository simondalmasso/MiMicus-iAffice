from __future__ import annotations

from typing import Any

from mimicus.falsifiers.builtins import builtin_specs
from mimicus.falsifiers.primitives import execute_primitive

K3_ARTIFACT_HASHES = {
    "zip": "f170207468c60b25b0d9ec50ddfcf27366609d5e37773138ca76eb9124eb1478",
    "python": "81b2fd83a313d9910f450ac54a4a1e48cd783dc1cde6bfc1d5bcfd37e6c38f2f",
    "sql": "d596a293e8b3c3543e1ceaae1468c8a937f43428de5ddc60120cb77a39e204a4",
}
K3_CONTRACT_HASHES = {
    "c1_tam_numerical_invariant": "29625d238477193e2f4f1d636c66d38ce8e68dd776ad35c55c8dfd3a89f42b37",
    "c2_source_freshness": "7649c98ea2c00f7623ed28b550539e971cee7ff63a43d5d6a8e028b7cdf3cd4b",
    "c3_source_independence": "7e3dede7c5db53fe332b8a475e8c38010dd2c35bae43821db2f0ce4911fe521d",
    "c4_citation_numeric_entailment": "ff966c84029e43b8b71f5af3a39eb8fef875b79709aa7017458fc15bb8d0f501",
    "c5_absence_counterexample_registry": "8bc04b55871b7f5ed4f1aa87c47d9d40e7e40e15080c871330bc0c09affacc15",
}


def compatibility_vectors() -> list[dict[str, object]]:
    specs = builtin_specs("compat")
    vectors: list[tuple[str, str, dict[str, Any], str]] = [
        ("c1_tam_12x_mismatch", "F1", {"price": 10.0, "users": 100.0, "price_period": "monthly", "claimed": 1000.0}, "FAIL"),
        ("c1_missing_is_inconclusive", "F1", {"price": 10.0, "users": None, "claimed": 1000.0}, "INCONCLUSIVE"),
        ("c2_stale", "F2", {"evidence_date": "2025-01-01T00:00:00+00:00", "as_of": "2026-08-17T00:00:00+00:00"}, "FAIL"),
        ("c2_missing_date_is_inconclusive", "F2", {"as_of": "2026-08-17T00:00:00+00:00"}, "INCONCLUSIVE"),
        ("c3_echo_chamber", "F3", {"clusters": ["wire-a", "wire-a", "wire-a"], "texts": ["same", "same", "same"]}, "FAIL"),
        ("c3_missing_provenance_is_inconclusive", "F3", {"clusters": []}, "INCONCLUSIVE"),
        ("c4_false_entailment", "F4", {"claim_figure": 42, "evidence_spans": [{"span_id": "s1", "supported_figures": [41], "material_support": True}]}, "FAIL"),
        ("c4_missing_span_is_inconclusive", "F4", {"claim_figure": 42, "evidence_spans": []}, "INCONCLUSIVE"),
        ("c5_counterexample", "F5", {"absence_key": "target", "registry": {"target": {"id": 1}}, "registry_snapshot_hash": "a" * 64}, "FAIL"),
        ("c5_unpinned_registry_is_inconclusive", "F5", {"absence_key": "target", "registry": {}}, "INCONCLUSIVE"),
    ]
    results: list[dict[str, object]] = []
    for vector_id, key, context, expected in vectors:
        execution = execute_primitive(specs[key], context)
        results.append(
            {
                "vector_id": vector_id,
                "safe_spec_hash": specs[key].hash,
                "primitive": specs[key].primitive,
                "expected": expected,
                "actual": execution.verdict.value,
                "pass": execution.verdict.value == expected,
                "execution_snapshot_hash": execution.execution_snapshot_hash,
            }
        )
    return results
