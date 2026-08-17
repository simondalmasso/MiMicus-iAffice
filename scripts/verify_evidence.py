from __future__ import annotations

import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
evidence = root / "evidence" / "ORDER-002"
required = [
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
missing = [name for name in required if not (evidence / name).exists()]
if missing:
    raise SystemExit(f"missing evidence: {missing}")

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

manifest_lines = [line for line in (evidence / "MANIFEST.sha256").read_text(encoding="utf-8").splitlines() if line.strip()]
for line in manifest_lines:
    digest, relative = line.split("  ", 1)
    target = evidence / relative
    actual = hashlib.sha256(target.read_bytes()).hexdigest()
    if actual != digest:
        raise SystemExit(f"evidence manifest mismatch: {relative}")
print(json.dumps({"verified": True, "files": len(required), "manifest_entries": len(manifest_lines)}))
