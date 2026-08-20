from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


def _run(command: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, text=True, capture_output=True, check=False, env=env)


def test_documented_zero_key_cli_run_then_semantic_replay(tmp_path: Path) -> None:
    env = os.environ.copy()
    env.pop("OPENAI_API_KEY", None)
    env["MIMICUS_DATABASE_URL"] = f"sqlite:///{tmp_path / 'quickstart.db'}"

    upgraded = _run(["mimicus", "db", "upgrade"], env)
    assert upgraded.returncode == 0, upgraded.stderr

    executed = _run(
        [
            "mimicus",
            "run",
            "--profile",
            "offline",
            "--task-file",
            "fixtures/order008_quickstart.json",
            "--budget-usd",
            "0",
            "--max-agents",
            "1",
            "--max-concurrency",
            "1",
            "--depth",
            "deep",
        ],
        env,
    )
    assert executed.returncode == 0, executed.stderr
    run = json.loads(executed.stdout)
    assert run["evidence_provenance"]["source_mode"] == "runtime"
    assert run["evidence_provenance"]["provider_input_evidence_hashes"]

    replayed = _run(["mimicus", "replay", str(run["run_id"])], env)
    assert replayed.returncode == 0, replayed.stderr
    replay = json.loads(replayed.stdout)
    assert replay["verified"] is True
    assert replay["integrity_verified"] is True
    assert replay["semantic_reexecution_verified"] is True
