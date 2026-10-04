from __future__ import annotations

import json
from pathlib import Path

from mimicus.benchmark import run_benchmark
from mimicus.interfaces.cli import doctor, main


def test_benchmark_200_and_transfer() -> None:
    report = run_benchmark(200)
    assert report["episodes_per_architecture"] == 200
    assert report["total_architecture_episodes"] == 1000
    assert set(report["metrics"]) == {"A", "B", "C", "D", "E"}
    assert report["fingerprint_replacement_transfer"]["kill_question_answer"] in {"YES", "NO"}
    assert report["metrics"]["E"]["memory_poison_propagation_rate"] == 0.0


def test_cli_doctor_run_benchmark_and_plugin(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("MIMICUS_DATABASE_URL", f"sqlite:///{tmp_path / 'cli.db'}")
    info = doctor("offline")
    assert info["secrets_printed"] is False
    assert info["database_reachable"] is True
    assert main(["plugin", "list", "--profile", "offline"]) == 0
    capsys.readouterr()
    task = tmp_path / "task.json"
    task.write_text(json.dumps({"task": "K3 TAM 12x mismatch", "domain": "finance"}), encoding="utf-8")
    assert main(["run", "--profile", "offline", "--task-file", str(task)]) == 0
    run_output = capsys.readouterr().out
    run_id = json.loads(run_output)["run_id"]
    assert main(["replay", run_id]) == 0
    capsys.readouterr()
    out = tmp_path / "bench"
    assert main(["benchmark", "--profile", "offline", "--episodes", "200", "--output-dir", str(out)]) == 0
    assert (out / "BENCHMARK.json").exists()
