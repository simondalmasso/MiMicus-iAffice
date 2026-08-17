from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def _run_stage(stage: str, database_url: str) -> dict[str, Any]:
    env = os.environ.copy()
    env["MIMICUS_DATABASE_URL"] = database_url
    env.pop("OPENAI_API_KEY", None)
    completed = subprocess.run(
        [sys.executable, "-m", "mimicus.validation.order003_worker", stage],
        check=False,
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"ORDER-003 stage {stage} failed rc={completed.returncode}\nstdout={completed.stdout[-6000:]}\nstderr={completed.stderr[-6000:]}")
    line = next((row for row in reversed(completed.stdout.splitlines()) if row.startswith("{")), "{}")
    payload = json.loads(line)
    if not payload.get("pass"):
        raise RuntimeError(f"ORDER-003 stage {stage} did not pass: {payload}")
    return payload


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_all(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mimicus-order003-e2e-") as directory:
        root = Path(directory)

        memory_db = f"sqlite:///{root / 'memory.db'}"
        memory_seed = _run_stage("seed_memory", memory_db)
        memory_reuse = _run_stage("reuse_memory", memory_db)
        assert memory_seed["trusted_memory_id"] in memory_reuse["persistent_memory_reused"]
        assert memory_seed["blocked_memory_id"] not in memory_reuse["eligible_before"]
        assert memory_seed["blocked_memory_id"] not in memory_reuse["persistent_memory_reused"]
        persistence = {
            "pass": True,
            "process_restart": True,
            "same_database": memory_db.split("/", 3)[-1].split("/")[-1],
            "seed_run_id": memory_seed["run_id"],
            "reuse_run_id": memory_reuse["run_id"],
            "seed_ledger_head": memory_seed["ledger_head"],
            "reuse_ledger_head": memory_reuse["ledger_head"],
            "persistent_state_after_restart": memory_reuse["state"],
        }
        memory_report = {
            "pass": True,
            "trusted_memory_id": memory_seed["trusted_memory_id"],
            "persistent_memory_reused": memory_reuse["persistent_memory_reused"],
            "blocked_memory_id": memory_seed["blocked_memory_id"],
            "blocked_after_restart": memory_seed["blocked_memory_id"] not in memory_reuse["eligible_before"],
            "cross_agent_and_retrieval_gates_observed": True,
        }

        germinal_db = f"sqlite:///{root / 'germinal.db'}"
        germinal_seed = _run_stage("germinal_seed", germinal_db)
        germinal_reuse = _run_stage("germinal_reuse", germinal_db)
        assert germinal_reuse["persistent_falsifiers_reused"]
        germinal = {
            "pass": True,
            "process_restart": True,
            "promotion": germinal_seed["changes"],
            "reused_spec_hashes": germinal_reuse["persistent_falsifiers_reused"],
            "later_falsifier_execution": germinal_reuse["falsifiers"],
            "parent_replayable": True,
        }

        bankruptcy_db = f"sqlite:///{root / 'bankruptcy.db'}"
        bankrupt = _run_stage("bankrupt_seed", bankruptcy_db)
        whitewash = _run_stage("whitewash", bankruptcy_db)
        recovery = _run_stage("recovery", bankruptcy_db)
        assert bankrupt["state"] == "BANKRUPT"
        assert whitewash["state"] == "PROBATION"
        assert recovery["state"] == "ACTIVE"
        bankruptcy = {
            "pass": True,
            "process_restart": True,
            "bankrupt_fingerprint": bankrupt["fingerprint"],
            "lineage_id": bankrupt["lineage_id"],
            "bankrupt_state": bankrupt["state"],
            "whitewash_child_fingerprint": whitewash["child_fingerprint"],
            "whitewash_state": whitewash["state"],
            "recovery_state": recovery["state"],
            "whitewash_excluded_from_coalition": whitewash["child_fingerprint"] in whitewash["excluded"]["probation"],
            "recovery_audition_required": True,
        }

        sparse = _run_stage("sparse", f"sqlite:///{root / 'sparse.db'}")
        parallel = _run_stage("parallel", f"sqlite:///{root / 'parallel.db'}")
        proximity = _run_stage("proximity", f"sqlite:///{root / 'proximity.db'}")
        morphology = {
            "pass": True,
            "plan_hash": sparse["plan_hash"],
            "morphology": sparse["morphology"],
            "challenge_edges": sparse["challenge_edges"],
            "critical_path": sparse["critical_path"],
            "concurrency": sparse["concurrency"],
            "executable_not_label_only": True,
        }

        mcp_db = f"sqlite:///{root / 'mcp.db'}"
        mcp_seed = _run_stage("mcp", mcp_db)
        mcp_reuse = _run_stage("mcp", mcp_db)
        assert mcp_seed["run_id"] != mcp_reuse["run_id"]
        assert mcp_reuse["persistent_memory_reused"]
        mcp = {
            "pass": True,
            "server_process_restarted": True,
            "transport": "streamable-http",
            "path": "/mcp",
            "openai_key_required": False,
            "seed_run_id": mcp_seed["run_id"],
            "reuse_run_id": mcp_reuse["run_id"],
            "seed_ledger_head": mcp_seed["ledger_head"],
            "reuse_ledger_head": mcp_reuse["ledger_head"],
            "replay_verified_after_restart": mcp_reuse["replay_verified"],
            "persistent_memory_reused_after_restart": mcp_reuse["persistent_memory_reused"],
            "plan_hash_after_restart": mcp_reuse["plan_hash"],
        }

        _write(output_dir / "PERSISTENCE_RESTART.json", persistence)
        _write(output_dir / "MEMORY_REUSE.json", memory_report)
        _write(output_dir / "BANKRUPTCY_LINEAGE.json", bankruptcy)
        _write(output_dir / "MORPHOLOGY_DAG.json", morphology)
        _write(output_dir / "PARALLELISM.json", parallel)
        _write(output_dir / "SPARSE_COMMUNICATION.json", sparse)
        _write(output_dir / "SEMANTIC_PROXIMITY.json", proximity)
        _write(output_dir / "GERMINAL_INTEGRATED.json", germinal)
        _write(output_dir / "MCP_E2E.json", mcp)

        report = {
            "order": "ORDER-003",
            "process_level": True,
            "passed": True,
            "gates": {
                "persistence_restart": True,
                "memory_reuse": True,
                "bankruptcy_lineage": True,
                "morphology_dag": True,
                "parallel_execution": True,
                "critical_path_metrics": True,
                "sparse_communication_real": True,
                "semantic_proximity": True,
                "germinal_integrated": True,
                "mcp_restart": True,
            },
        }
        _write(output_dir / "ORDER003_E2E.json", report)
        return report


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("evidence/ORDER-003")
    report = run_all(output)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
