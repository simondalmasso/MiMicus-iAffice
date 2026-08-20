from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def _display(command: list[str]) -> list[str]:
    if command and command[0] == sys.executable:
        return ["python", *command[1:]]
    return command


def _run(command: list[str]) -> dict[str, Any]:
    completed = subprocess.run(command, text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        combined = completed.stdout + completed.stderr
        raise RuntimeError(f"probe failed ({completed.returncode}): {' '.join(command)}\n{combined}")
    return {
        "pass": True,
        "command": _display(command),
        "returncode": completed.returncode,
    }


def _write_json(root: Path, name: str, payload: dict[str, Any]) -> None:
    (root / name).write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _pytest(*nodeids: str) -> dict[str, Any]:
    return _run([sys.executable, "-m", "pytest", *nodeids, "-vv"])


def _runtime_mapping() -> list[str]:
    return [
        "F001|production_runtime|O6R + O8R::F043",
        "F002|production_runtime|O6R::germinal_restart + O8R::F043",
        "F003|production_runtime|O6R::microaudition_bankruptcy",
        "F004|production_runtime|O6R::all_five_morphologies + O8R::F043",
        "F005|production_runtime|O6R::all_five_morphologies",
        "F006|production_runtime|PLUGINS + O5R/O6R engine construction",
        "F007|exact_head_system_gate|BENCH",
        "F008|production_runtime|O6R::germinal_restart",
        "F009|production_runtime_superseding_fixture|O6R::microaudition_bankruptcy",
        "F010|production_contract|O5U::identity_manifest + adapter_version",
        "F011|provider_contract_mock|O4R::openai_verified_memory_structured_input",
        "F012|production_runtime|O5R::unknown_cost_preflight + known_cost_preflight",
        "F013|production_runtime|O5R::provider_refs_restart",
        "F014|production_runtime|O7U::claim_market_novelty",
        "F015|production_runtime|O6R::all_five_morphologies",
        "F016|production_contract|O4U structured-cancellation regressions + FULL",
        "F017|exact_head_system_gate|BENCH + CLI_BENCH",
        "F018|production_runtime|O5R::words_only_no_synthetic_evidence",
        "F019|production_contract|O5U::identity_manifest",
        "F020|production_runtime|O5R::provider_refs_restart + openai_evidence_binding",
        "F021|production_runtime|O6U + O6R::microaudition_bankruptcy",
        "F022|production_contract|O5U::tool_capability_truth + O5R preflight",
        "F023|production_runtime|O6R::microaudition_bankruptcy",
        "F024|production_runtime|O6R::germinal_restart + O7E verifier authority",
        "F025|production_runtime|O6R::germinal_restart",
        "F026|production_runtime|O6R::claim_aware_market_hierarchy",
        "F027|production_runtime|O6U::synthesis + O8 F039 kills",
        "F028|production_runtime|O6R::claim_aware_market_hierarchy",
        "F029|production_runtime|O6R::cofailure_marginal_restart",
        "F030|production_runtime|O6R::all_five_morphologies + BENCH",
        "F031|production_runtime|O6U::structural_threat_profile_wording_invariant",
        "F032|production_runtime|O7E::VERIFIER_AUTHORITY_BINDING + MCP",
        "F033|production_contract|O7U::claim_identity_revision + O7E",
        "F034|production_runtime|O7U::claim_market_novelty + O7E",
        "F035|production_runtime|O7E::HIERARCHY_COMPLETE_EXECUTION + O6R hierarchy",
        "F036|production_runtime|O7E::REMOVAL_ATTRIBUTION + O8R::F042",
        "F037|production_runtime|O7U::runtime_core_lock + O7E::RUNTIME_CORE_LOCK",
    ]


def run(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)

    probes = {
        "CLAIM_BOUND_FALSIFIERS.json": _pytest(
            "tests/integration/test_order008_runtime.py::test_f038_claim_bound_numeric_snapshot_changes_with_exact_assertion",
            "tests/unit/test_order008_f038_claim_bound.py",
        ),
        "HIERARCHICAL_COMPOSITE_SYNTHESIS.json": _pytest("tests/unit/test_order008_f039.py"),
        "RECEIPT_CASCADE_REVOCATION.json": _pytest("tests/unit/test_order008_f040.py::test_one_active_origin_and_promotion_cascade_revocation"),
        "EVIDENCE_PROJECTION_INTEGRITY.json": _pytest("tests/unit/test_order008_f041.py"),
        "VERIFIED_REMOVAL_SCOPE.json": _pytest("tests/integration/test_order008_runtime.py::test_f042_verified_removal_is_selected_claim_scoped_and_revocation_safe"),
        "CORE_MEMORY_LEARN_PROGRESS.json": _pytest("tests/integration/test_order008_runtime.py::test_f043_runtime_learning_memory_restart_revocation_and_no_progress"),
        "SEMANTIC_REPLAY.json": _pytest("tests/integration/test_order008_runtime.py::test_f044_semantic_reexecution_tamper_and_nonreplayable_truth"),
    }
    for name, payload in probes.items():
        _write_json(root, name, payload)

    production_regression = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/unit/test_plugins.py",
            "tests/unit/test_order004_correctness.py",
            "tests/unit/test_order005_correctness.py",
            "tests/integration/test_order005_runtime.py",
            "tests/unit/test_order006_core.py",
            "tests/integration/test_order006_runtime.py",
            "tests/unit/test_order007_correctness.py",
            "tests/integration/test_order008_progress_visibility.py",
            "tests/integration/test_order008_runtime.py::test_f043_runtime_learning_memory_restart_revocation_and_no_progress",
            "tests/integration/test_cli_benchmark.py",
            "-vv",
        ]
    )
    order005 = _run(
        [sys.executable, "scripts/order005_evidence.py", str(root / "order005-runtime-regression")]
    )
    order006 = _run(
        [sys.executable, "scripts/order006_evidence.py", str(root / "order006-runtime-regression")]
    )
    order007 = _run(
        [sys.executable, "scripts/order007_evidence.py", str(root / "order007-runtime-regression")]
    )

    lines = [
        "PROBE=ORDER-008-production-runtime-regression-F001-F037",
        "CLAIM=Applicable prior invariants have explicit normal-core/provider-contract/exact-head sources; legacy fixture checks are not production proof.",
        "ALIAS O4U=tests/unit/test_order004_correctness.py",
        "ALIAS O4R=tests/integration/test_order004_runtime.py",
        "ALIAS O5U=tests/unit/test_order005_correctness.py",
        "ALIAS O5R=tests/integration/test_order005_runtime.py",
        "ALIAS O6U=tests/unit/test_order006_core.py",
        "ALIAS O6R=tests/integration/test_order006_runtime.py",
        "ALIAS O7U=tests/unit/test_order007_correctness.py",
        "ALIAS O8R=tests/integration/test_order008_runtime.py",
        "ALIAS PLUGINS=tests/unit/test_plugins.py",
        "ALIAS CLI_BENCH=tests/integration/test_cli_benchmark.py",
        "ALIAS O7E=scripts/order007_evidence.py",
        "ALIAS BENCH=exact-head benchmark-evidence job (200/architecture, common grader, anti-rigging, leakage)",
        "ALIAS FULL=exact-head full unit/integration coverage gate",
        "PRODUCTION_COMMAND=" + " ".join(production_regression["command"]),
        f"PRODUCTION_RETURN_CODE={production_regression['returncode']}",
        "ORDER005_EVIDENCE_COMMAND=python scripts/order005_evidence.py <ORDER008_OUTPUT>/order005-runtime-regression",
        f"ORDER005_EVIDENCE_RETURN_CODE={order005['returncode']}",
        "ORDER006_EVIDENCE_COMMAND=python scripts/order006_evidence.py <ORDER008_OUTPUT>/order006-runtime-regression",
        f"ORDER006_EVIDENCE_RETURN_CODE={order006['returncode']}",
        "ORDER007_EVIDENCE_COMMAND=python scripts/order007_evidence.py <ORDER008_OUTPUT>/order007-runtime-regression",
        f"ORDER007_EVIDENCE_RETURN_CODE={order007['returncode']}",
        "MAPPING_BEGIN",
        *_runtime_mapping(),
        "MAPPING_END",
        "COMPATIBILITY_ONLY=tests/integration/test_order003_runtime.py and fixture-oriented ORDER-004 regressions remain in the full suite but are not counted as production proof above.",
        "RUNTIME_F001_F037=PASS",
    ]
    (root / "RUNTIME_REGRESSION_F001_F037.txt").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    test_result = _run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/integration/test_engine.py::test_full_flow_and_persistence",
            "tests/integration/test_order003_runtime.py::test_engine_restart_memory_reuse_and_falsifier_germinal_reuse",
            "tests/integration/test_order004_runtime.py::test_evidence_persists_and_all_claim_refs_resolve_after_restart",
            "tests/unit/test_order008_f038_claim_bound.py",
            "tests/unit/test_order008_f039.py",
            "tests/unit/test_order008_f040.py",
            "tests/unit/test_order008_f041.py",
            "tests/integration/test_order008_runtime.py",
            "-vv",
        ]
    )
    (root / "TEST_RESULTS.txt").write_text(
        "PROBE=ORDER-008-final-kills-and-historical-compatibility\n" + "COMMAND=" + " ".join(test_result["command"]) + f"\nRETURN_CODE={test_result['returncode']}\n",
        encoding="utf-8",
    )

    summary = {
        "pass": all(payload["pass"] for payload in probes.values()),
        "probe_files": sorted(probes),
        "runtime_regression": "RUNTIME_REGRESSION_F001_F037.txt",
        "test_results": "TEST_RESULTS.txt",
    }
    print(json.dumps({"ORDER_008_EVIDENCE": "PASS", **summary}, sort_keys=True))
    return summary


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("evidence/ORDER-008")
    run(root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
