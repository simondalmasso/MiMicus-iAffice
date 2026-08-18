from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
order = sys.argv[1] if len(sys.argv) > 1 else "ORDER-002"
if order not in {"ORDER-002", "ORDER-003"}:
    raise SystemExit(f"unsupported evidence order: {order}")

evidence = root / "evidence" / order

required_order002 = [
    "REMOTE_TRUTH.md",
    "ENVIRONMENT.md",
    "COMMANDS.md",
    "K3_COMPATIBILITY.json",
    "TEST_RESULTS.txt",
    "E2E_RESULTS.json",
    "MCP_E2E.json",
    "BENCHMARK.json",
    "BENCHMARK.md",
    "LEDGER_VERIFY.json",
    "MIGRATION_VERIFY.txt",
    "PACKAGE_VERIFY.txt",
    "MANIFEST.sha256",
    "FULL_RUN_TRACE.json",
]

required_order003 = [
    "REMOTE_TRUTH.md",
    "AUD_FINDINGS_CLOSURE.md",
    "ENVIRONMENT.md",
    "COMMANDS.md",
    "TEST_RESULTS.txt",
    "PERSISTENCE_RESTART.json",
    "MEMORY_REUSE.json",
    "BANKRUPTCY_LINEAGE.json",
    "MORPHOLOGY_DAG.json",
    "PARALLELISM.json",
    "SPARSE_COMMUNICATION.json",
    "GERMINAL_INTEGRATED.json",
    "MCP_E2E.json",
    "BENCHMARK_RAW.jsonl",
    "BENCHMARK.json",
    "BENCHMARK.md",
    "BENCHMARK_ANTI_RIGGING.json",
    "LEDGER_VERIFY.json",
    "MIGRATION_VERIFY.txt",
    "PACKAGE_VERIFY.txt",
    "MANIFEST.sha256",
    "SEMANTIC_PROXIMITY.json",
    "ORDER003_E2E.json",
]

required = required_order002 if order == "ORDER-002" else required_order003
missing = [name for name in required if not (evidence / name).exists()]
if missing:
    raise SystemExit(f"missing evidence: {missing}")

if order == "ORDER-002":
    k3 = json.loads((evidence / "K3_COMPATIBILITY.json").read_text(encoding="utf-8"))
    e2e = json.loads((evidence / "E2E_RESULTS.json").read_text(encoding="utf-8"))
    mcp = json.loads((evidence / "MCP_E2E.json").read_text(encoding="utf-8"))
    bench = json.loads((evidence / "BENCHMARK.json").read_text(encoding="utf-8"))
    ledger = json.loads((evidence / "LEDGER_VERIFY.json").read_text(encoding="utf-8"))
    assert k3["passed"] is True
    assert len(k3["vectors"]) >= 10
    assert e2e["passed"] is True and len(e2e["scenarios"]) == 12
    assert mcp["pass"] is True and mcp["path"] == "/mcp"
    assert int(bench["episodes_per_architecture"]) >= 200
    assert ledger["clean_verified"] is True and ledger["tamper_detected"] is True
else:
    e2e = json.loads((evidence / "ORDER003_E2E.json").read_text(encoding="utf-8"))
    persistence = json.loads((evidence / "PERSISTENCE_RESTART.json").read_text(encoding="utf-8"))
    memory = json.loads((evidence / "MEMORY_REUSE.json").read_text(encoding="utf-8"))
    bankruptcy = json.loads((evidence / "BANKRUPTCY_LINEAGE.json").read_text(encoding="utf-8"))
    morphology = json.loads((evidence / "MORPHOLOGY_DAG.json").read_text(encoding="utf-8"))
    parallel = json.loads((evidence / "PARALLELISM.json").read_text(encoding="utf-8"))
    sparse = json.loads((evidence / "SPARSE_COMMUNICATION.json").read_text(encoding="utf-8"))
    germinal = json.loads((evidence / "GERMINAL_INTEGRATED.json").read_text(encoding="utf-8"))
    mcp = json.loads((evidence / "MCP_E2E.json").read_text(encoding="utf-8"))
    bench = json.loads((evidence / "BENCHMARK.json").read_text(encoding="utf-8"))
    anti = json.loads((evidence / "BENCHMARK_ANTI_RIGGING.json").read_text(encoding="utf-8"))
    ledger = json.loads((evidence / "LEDGER_VERIFY.json").read_text(encoding="utf-8"))
    proximity = json.loads((evidence / "SEMANTIC_PROXIMITY.json").read_text(encoding="utf-8"))

    assert e2e["passed"] is True and all(bool(value) for value in e2e["gates"].values())
    assert persistence["pass"] is True and persistence["process_restart"] is True
    assert memory["pass"] is True and memory["blocked_after_restart"] is True and memory["persistent_memory_reused"]
    assert bankruptcy["pass"] is True and bankruptcy["bankrupt_state"] == "BANKRUPT" and bankruptcy["whitewash_state"] == "PROBATION" and bankruptcy["recovery_state"] == "ACTIVE"
    assert morphology["pass"] is True and morphology["executable_not_label_only"] is True and morphology["plan_hash"]
    assert parallel["pass"] is True and parallel["metrics"]["peak_concurrency"] >= 2 and parallel["metrics"]["critical_path_ms"] < parallel["metrics"]["serial_work_ms"]
    assert sparse["pass"] is True and sparse["challenge_edges"] > 0 and sparse["challenge_calls"] == sparse["challenge_edges"]
    assert germinal["pass"] is True and germinal["process_restart"] is True and germinal["reused_spec_hashes"]
    assert mcp["pass"] is True and mcp["server_process_restarted"] is True and mcp["path"] == "/mcp" and mcp["replay_verified_after_restart"] is True
    assert int(bench["episodes_per_architecture"]) >= 200 and int(bench["total_architecture_episodes"]) >= 1000
    assert set(bench["metrics"]) == {"A", "B", "C", "D", "E"}
    assert bench["benchmark_version"] == "ORDER-003-v0.2-execution-derived"
    assert anti["passed"] is True
    assert ledger["clean_verified"] is True and ledger["tamper_detected"] is True and ledger["snapshot_mismatch_detected"] is True
    assert proximity["pass"] is True and proximity["contradiction"]["useful_contradiction"] is True

manifest_lines = [line for line in (evidence / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines() if line.strip()]
for line in manifest_lines:
    digest, relative = line.split("  ", 1)
    target = evidence / relative
    actual = hashlib.sha256(target.read_bytes()).hexdigest()
    if actual != digest:
        raise SystemExit(f"evidence manifest mismatch: {relative}")

print(json.dumps({"verified": True, "order": order, "files": len(required), "manifest_entries": len(manifest_lines)}))
