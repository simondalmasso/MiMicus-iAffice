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


def _runtime_mapping() -> list[tuple[str, str, str]]:
    return [
        ("F001", "production_runtime", "tests/integration/test_order006_runtime.py + tests/integration/test_order008_runtime.py::test_f043_runtime_learning_memory_restart_revocation_and_no_progress"),
        ("F002", "production_runtime", "tests/integration/test_order006_runtime.py::test_receipt_drives_real_germinal_and_restart_reuses_promoted_falsifier + tests/integration/test_order008_runtime.py::test_f043_runtime_learning_memory_restart_revocation_and_no_progress"),
        ("F003", "production_runtime", "tests/integration/test_order006_runtime.py::test_real_microauditions_fail_incompetent_and_persist_bankruptcy"),
        ("F004", "production_runtime", "tests/integration/test_order006_runtime.py::test_all_five_morphologies_are_runtime_reachable + tests/integration/test_order008_runtime.py::test_f043_runtime_learning_memory_restart_revocation_and_no_progress"),
        ("F005", "production_runtime", "tests/integration/test_order006_runtime.py::test_all_five_morphologies_are_runtime_reachable"),
        ("F006", "production_runtime", "tests/unit/test_plugins.py + normal MiMicusEngine construction exercised by ORDER-005/006 runtime tests"),
        ("F007", "exact_head_system_gate", "benchmark-evidence job: 200 episodes per architecture / 1000 total, common grader, anti-rigging and leakage assertions"),
        ("F008", "production_runtime", "tests/integration/test_order006_runtime.py::test_receipt_drives_real_germinal_and_restart_reuses_promoted_falsifier"),
        ("F009", "production_runtime_superseding_legacy_fixture", "tests/integration/test_order006_runtime.py::test_real_microauditions_fail_incompetent_and_persist_bankruptcy; ORDER-004 fixture audition test is compatibility-only"),
        ("F010", "production_contract", "tests/unit/test_order005_correctness.py::test_material_identity_mutations_change_fingerprint_and_forgery_is_rejected + test_make_identity_binds_adapter_version"),
        ("F011", "provider_contract_mock", "tests/integration/test_order004_runtime.py::test_openai_adapter_consumes_bounded_verified_memory_in_structured_input; live OpenAI is explicitly deferred"),
        ("F012", "production_runtime", "tests/integration/test_order005_runtime.py::test_unknown_cost_multicall_preflight_executes_no_partial_swarm + test_known_cost_preflight_degrades_before_execution"),
        ("F013", "production_runtime", "tests/integration/test_order005_runtime.py::test_provider_refs_are_bound_to_supplied_evidence_and_resolve_after_restart"),
        ("F014", "production_runtime", "tests/unit/test_order007_correctness.py::test_claim_market_applies_novelty_and_probability_can_reorder"),
        ("F015", "production_runtime", "tests/integration/test_order006_runtime.py::test_all_five_morphologies_are_runtime_reachable"),
        ("F016", "production_contract", "tests/unit/test_order004_correctness.py structured-cancellation regression + full unit/integration exact-head gate"),
        ("F017", "exact_head_system_gate", "benchmark-evidence job + tests/integration/test_cli_benchmark.py"),
        ("F018", "production_runtime", "tests/integration/test_order005_runtime.py::test_words_only_runtime_cannot_activate_synthetic_evidence"),
        ("F019", "production_contract", "tests/unit/test_order005_correctness.py::test_material_identity_mutations_change_fingerprint_and_forgery_is_rejected"),
        ("F020", "production_runtime", "tests/integration/test_order005_runtime.py::test_provider_refs_are_bound_to_supplied_evidence_and_resolve_after_restart + test_openai_adapter_receives_canonical_evidence_and_excludes_blocked_memory"),
        ("F021", "production_runtime", "tests/unit/test_order006_core.py + tests/integration/test_order006_runtime.py::test_real_microauditions_fail_incompetent_and_persist_bankruptcy"),
        ("F022", "production_contract", "tests/unit/test_order005_correctness.py::test_openai_tool_capability_matches_actual_tools_and_identity + ORDER-005 cost-preflight runtime tests"),
        ("F023", "production_runtime", "tests/integration/test_order006_runtime.py::test_real_microauditions_fail_incompetent_and_persist_bankruptcy"),
        ("F024", "production_runtime", "tests/integration/test_order006_runtime.py::test_receipt_drives_real_germinal_and_restart_reuses_promoted_falsifier + ORDER-007 verifier-authority evidence"),
        ("F025", "production_runtime", "tests/integration/test_order006_runtime.py::test_receipt_drives_real_germinal_and_restart_reuses_promoted_falsifier"),
        ("F026", "production_runtime", "tests/integration/test_order006_runtime.py::test_claim_aware_runtime_market_and_real_hierarchical_subtasks"),
        ("F027", "production_runtime", "tests/unit/test_order006_core.py::test_swarm_synthesis_materially_uses_claims_and_falsifiers + ORDER-008 F039 composite synthesis kills"),
        ("F028", "production_runtime", "tests/integration/test_order006_runtime.py::test_claim_aware_runtime_market_and_real_hierarchical_subtasks"),
        ("F029", "production_runtime", "tests/integration/test_order006_runtime.py::test_verified_cofailure_and_marginal_value_change_future_coalition_after_restart"),
        ("F030", "production_runtime", "tests/integration/test_order006_runtime.py::test_all_five_morphologies_are_runtime_reachable + benchmark-evidence morphology distribution"),
        ("F031", "production_runtime", "tests/unit/test_order006_core.py::test_structural_threat_profile_is_wording_invariant"),
        ("F032", "production_runtime", "scripts/order007_evidence.py: VERIFIER_AUTHORITY_BINDING.json + MCP_E2E.json"),
        ("F033", "production_contract", "tests/unit/test_order007_correctness.py::test_claim_identity_survives_challenge_revision + scripts/order007_evidence.py"),
        ("F034", "production_runtime", "tests/unit/test_order007_correctness.py::test_claim_market_applies_novelty_and_probability_can_reorder + scripts/order007_evidence.py"),
        ("F035", "production_runtime", "scripts/order007_evidence.py: HIERARCHY_COMPLETE_EXECUTION.json + tests/integration/test_order006_runtime.py::test_claim_aware_runtime_market_and_real_hierarchical_subtasks"),
        ("F036", "production_runtime", "scripts/order007_evidence.py: REMOVAL_ATTRIBUTION.json + ORDER-008 F042 kill"),
        ("F037", "production_runtime", "tests/unit/test_order007_correctness.py::test_normal_runtime_cannot_downgrade_to_legacy + scripts/order007_evidence.py: RUNTIME_CORE_LOCK.json"),
    ]


def run(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=True)

    probes = {
        "CLAIM_BOUND_FALSIFIERS.json": _pytest(
            "tests/integration/test_order008_runtime.py::test_f038_claim_bound_numeric_snapshot_changes_with_exact_assertion",
            "tests/unit/test_order008_f038_claim_bound.py",
        ),
        "HIERARCHICAL_COMPOSITE_SYNTHESIS.json": _pytest("tests/unit/test_order008_f039.py"),
        "RECEIPT_CASCADE_REVOCATION.json": _pytest(
            "tests/unit/test_order008_f040.py::test_one_active_origin_and_promotion_cascade_revocation"
        ),
        "EVIDENCE_PROJECTION_INTEGRITY.json": _pytest("tests/unit/test_order008_f041.py"),
        "VERIFIED_REMOVAL_SCOPE.json": _pytest(
            "tests/integration/test_order008_runtime.py::test_f042_verified_removal_is_selected_claim_scoped_and_revocation_safe"
        ),
        "CORE_MEMORY_LEARN_PROGRESS.json": _pytest(
            "tests/integration/test_order008_runtime.py::test_f043_runtime_learning_memory_restart_revocation_and_no_progress"
        ),
        "SEMANTIC_REPLAY.json": _pytest(
            "tests/integration/test_order008_runtime.py::test_f044_semantic_reexecution_tamper_and_nonreplayable_truth"
        ),
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
    order005 = _run([sys.executable, "scripts/order005_evidence.py", str(root / "order005-runtime-regression")])
    order006 = _run([sys.executable, "scripts/order006_evidence.py", str(root / "order006-runtime-regression")])
    order007 = _run([sys.executable, "scripts/order007_evidence.py", str(root / "order007-runtime-regression")])

    lines = [
        "PROBE=ORDER-008-production-runtime-regression-F001-F037",
        "CLAIM=Every applicable prior invariant below has an explicit normal-core/provider-contract/exact-head source; legacy fixture checks are not counted as production proof.",
        "PRODUCTION_COMMAND=" + " ".join(production_regression["command"]),
        f"PRODUCTION_RETURN_CODE={production_regression['returncode']}",
        "ORDER005_EVIDENCE_COMMAND=python scripts/order005_evidence.py <ORDER008_OUTPUT>/order005-runtime-regression",
        f"ORDER005_EVIDENCE_RETURN_CODE={order005['returncode']}",
        "ORDER006_EVIDENCE_COMMAND=python scripts/order006_evidence.py <ORDER008_OUTPUT>/order006-runtime-regression",
        f"ORDER006_EVIDENCE_RETURN_CODE={order006['returncode']}",
        "ORDER007_EVIDENCE_COMMAND=python scripts/order007_evidence.py <ORDER008_OUTPUT>/order007-runtime-regression",
        f"ORDER007_EVIDENCE_RETURN_CODE={order007['returncode']}",
        "MAPPING_BEGIN",
    ]
    lines.extend(f"{finding}|{scope}|{source}" for finding, scope, source in _runtime_mapping())
    lines.extend(
        [
            "MAPPING_END",
            "COMPATIBILITY_ONLY=tests/integration/test_order003_runtime.py and fixture-oriented ORDER-004 regressions remain in the full suite for historical compatibility but are not used as production-runtime proof above.",
            "RUNTIME_F001_F037=PASS",
        ]
    )
    (root / "RUNTIME_REGRESSION_F001_F037.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

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
        "PROBE=ORDER-008-final-kills-and-historical-compatibility\n"
        + "COMMAND="
        + " ".join(test_result["command"])
        + f"\nRETURN_CODE={test_result['returncode']}\n",
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
