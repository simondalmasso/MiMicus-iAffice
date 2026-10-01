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
    return {"pass": True, "command": _display(command), "returncode": completed.returncode}


def _write_json(root: Path, name: str, payload: dict[str, Any]) -> None:
    (root / name).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _pytest(*nodeids: str) -> dict[str, Any]:
    return _run([sys.executable, "-m", "pytest", *nodeids, "-vv"])


def _mapping_text() -> str:
    text = Path("docs/ORDER008_RUNTIME_MAPPING.txt").read_text(encoding="utf-8")
    findings = [line.split("|", 1)[0] for line in text.splitlines() if line.startswith("F")]
    assert findings == [f"F{index:03d}" for index in range(1, 38)]
    return text.rstrip()


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

    production = _run(
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
    regression = [
        "PROBE=ORDER-008-production-runtime-regression-F001-F037",
        "CLAIM=Applicable prior invariants have explicit normal-core/provider-contract/exact-head sources; legacy fixture checks are not production proof.",
        "PRODUCTION_COMMAND=" + " ".join(production["command"]),
        f"PRODUCTION_RETURN_CODE={production['returncode']}",
        f"ORDER005_EVIDENCE_RETURN_CODE={order005['returncode']}",
        f"ORDER006_EVIDENCE_RETURN_CODE={order006['returncode']}",
        f"ORDER007_EVIDENCE_RETURN_CODE={order007['returncode']}",
        _mapping_text(),
        "RUNTIME_F001_F037=PASS",
    ]
    (root / "RUNTIME_REGRESSION_F001_F037.txt").write_text("\n".join(regression) + "\n", encoding="utf-8")

    final = _run(
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
            "tests/integration/test_order008_quickstart_cli.py",
            "-vv",
        ]
    )
    (root / "TEST_RESULTS.txt").write_text(
        "PROBE=ORDER-008-final-kills-historical-compatibility-and-quickstart\n" + "COMMAND=" + " ".join(final["command"]) + f"\nRETURN_CODE={final['returncode']}\n",
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
