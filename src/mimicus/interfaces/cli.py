from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence
from pathlib import Path

from mimicus import __version__
from mimicus.benchmark import write_benchmark
from mimicus.config import Settings
from mimicus.orchestration.engine import MiMicusEngine, RunRequest
from mimicus.plugins.profiles import PROFILES, build_kernel
from mimicus.storage.migrations_adapter import upgrade
from mimicus.storage.repository import Repository


def _database_url() -> str:
    return os.getenv("MIMICUS_DATABASE_URL", "sqlite:///mimicus.db")


def doctor(profile: str) -> dict[str, object]:
    settings = Settings(profile=profile, database_url=_database_url())
    settings.validate()
    repository = Repository(settings.database_url)
    kernel = build_kernel(profile)
    order = kernel.dependency_order()
    kernel.mount_all()
    services = kernel.services.snapshot()
    kernel.unmount_all()
    mcp_version = "unknown"
    try:
        from importlib.metadata import version

        mcp_version = version("mcp")
    except Exception as exc:
        mcp_version = f"unavailable:{type(exc).__name__}"
    return {
        "version": __version__,
        "profile": profile,
        "database_reachable": repository.engine.dialect.name in {"sqlite", "postgresql"},
        "plugin_order": order,
        "plugin_services": services,
        "provider_ready": profile != "openai" or bool(os.getenv("OPENAI_API_KEY")),
        "provider_live_credential_present": bool(os.getenv("OPENAI_API_KEY")) if profile == "openai" else False,
        "mcp_version": mcp_version,
        "secrets_printed": False,
    }


def _engine(profile: str) -> MiMicusEngine:
    kernel = build_kernel(profile)
    kernel.mount_all()
    hashes = [plugin.manifest.manifest_hash for plugin in kernel.plugins.values()]
    provider = kernel.services.get("model_provider")
    return MiMicusEngine(_database_url(), plugin_hashes=hashes, provider=provider)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mimicus")
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_doctor = sub.add_parser("doctor")
    p_doctor.add_argument("--profile", choices=sorted(PROFILES), default="offline")

    p_db = sub.add_parser("db")
    db_sub = p_db.add_subparsers(dest="db_command", required=True)
    db_sub.add_parser("upgrade")

    p_plugin = sub.add_parser("plugin")
    plugin_sub = p_plugin.add_subparsers(dest="plugin_command", required=True)
    p_list = plugin_sub.add_parser("list")
    p_list.add_argument("--profile", choices=sorted(PROFILES), default="offline")

    p_run = sub.add_parser("run")
    p_run.add_argument("--profile", choices=sorted(PROFILES), default="offline")
    p_run.add_argument("--task-file", required=True)
    p_run.add_argument("--budget-usd", type=float, default=0.0)
    p_run.add_argument("--max-agents", type=int, default=4)
    p_run.add_argument("--depth", choices=["fast", "normal", "deep"], default="normal")
    p_run.add_argument("--learn", action="store_true")

    p_replay = sub.add_parser("replay")
    p_replay.add_argument("run_id")

    p_bench = sub.add_parser("benchmark")
    p_bench.add_argument("--profile", choices=sorted(PROFILES), default="offline")
    p_bench.add_argument("--episodes", type=int, default=200)
    p_bench.add_argument("--output-dir", default="evidence/ORDER-002")

    p_serve = sub.add_parser("serve")
    p_serve.add_argument("--profile", choices=sorted(PROFILES), default="offline")
    p_serve.add_argument("--host", default="127.0.0.1")
    p_serve.add_argument("--port", type=int, default=8765)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "doctor":
        print(json.dumps(doctor(args.profile), indent=2, sort_keys=True))
        return 0
    if args.command == "db":
        upgrade(_database_url())
        print(json.dumps({"database": "upgraded", "url_scheme": _database_url().split(":", 1)[0]}))
        return 0
    if args.command == "plugin":
        kernel = build_kernel(args.profile)
        print(
            json.dumps([plugin.manifest.model_dump(mode="json") | {"manifest_hash": plugin.manifest.manifest_hash} for plugin in kernel.plugins.values()], indent=2, sort_keys=True)
        )
        return 0
    if args.command == "run":
        payload = json.loads(Path(args.task_file).read_text(encoding="utf-8"))
        if isinstance(payload, str):
            payload = {"task": payload}
        payload.update({"budget_usd": args.budget_usd, "max_agents": args.max_agents, "depth": args.depth, "learn": args.learn})
        run_result = _engine(args.profile).run(RunRequest.model_validate(payload))
        print(run_result.model_dump_json(indent=2))
        return 0
    if args.command == "replay":
        replay_row = Repository(_database_url()).get_run(args.run_id)
        if replay_row is None:
            print(json.dumps({"verified": False, "reason": "run not found", "run_id": args.run_id}))
            return 2
        full = MiMicusEngine(_database_url()).get_run(args.run_id)
        if full is None:
            print(json.dumps({"verified": False, "reason": "run disappeared", "run_id": args.run_id}))
            return 2
        print(json.dumps(full["replay_state"], indent=2, sort_keys=True))
        return 0 if full["replay_state"]["verified"] else 1
    if args.command == "benchmark":
        if args.profile != "offline":
            raise SystemExit("ORDER-002 reference benchmark is offline only")
        out = Path(args.output_dir)
        report = write_benchmark(out / "BENCHMARK.json", out / "BENCHMARK.md", args.episodes)
        print(
            json.dumps({"episodes": report["episodes_per_architecture"], "output": str(out), "kill_question": report["fingerprint_replacement_transfer"]["kill_question_answer"]})
        )
        return 0
    if args.command == "serve":
        from mimicus.interfaces.mcp_server import serve

        serve(args.profile, args.host, args.port)
        return 0
    raise RuntimeError("unreachable command")


if __name__ == "__main__":
    raise SystemExit(main())
