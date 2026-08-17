from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


def run_all(output: Path | None = None) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="mimicus-e2e-") as directory:
        root = Path(directory)
        for number in range(1, 13):
            key = f"{number:02d}"
            env = os.environ.copy()
            env["MIMICUS_DATABASE_URL"] = f"sqlite:///{root / f'scenario-{key}.db'}"
            env.pop("OPENAI_API_KEY", None)
            completed = subprocess.run(
                [sys.executable, "-m", "mimicus.validation.worker", key],
                check=False,
                capture_output=True,
                text=True,
                env=env,
                timeout=90,
            )
            if completed.returncode != 0:
                results.append(
                    {
                        "scenario": key,
                        "pass": False,
                        "returncode": completed.returncode,
                        "stdout": completed.stdout[-4000:],
                        "stderr": completed.stderr[-4000:],
                    }
                )
                continue
            line = next((line for line in reversed(completed.stdout.splitlines()) if line.startswith("{")), "{}")
            results.append(json.loads(line))
    report = {
        "order": "ORDER-002",
        "process_level": True,
        "clean_temp_db_per_scenario": True,
        "scenarios": results,
        "passed": len(results) == 12 and all(bool(row.get("pass")) for row in results),
    }
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    report = run_all(output)
    print(json.dumps({"passed": report["passed"], "scenarios": len(report["scenarios"])}))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
