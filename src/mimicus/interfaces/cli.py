from __future__ import annotations

import argparse
import json
import os
from collections.abc import Sequence
from pathlib import Path

from mimicus import __version__
from mimicus.benchmark import write_benchmark
from mimicus.canonical import sha256_obj
from mimicus.config import Settings
from mimicus.orchestration.engine import MiMicusEngine, RunRequest, _spec_keys, scenario_fixture
from mimicus.orchestration.morphology import compile_morphology
from mimicus.plugins.profiles import PROFILES, build_kernel
from mimicus.providers.base import Provider
from mimicus.storage.migrations_adapter import upgrade
from mimicus.storage.repository import Repository


def _database_url() -> str:
    return os.getenv("MIMICUS_DATABASE_URL", "sqlite:///mimicus.db")


def doctor(profile: str) -> dict[str, object]:
    settings = Settings(profile=profile, database_url=_database_url())
    settings.validate()
    repository = Repository(settings.database_url)
    kernel = build_kernel(profile, settings.database_url)
    order = kernel.dependency_order()
    kernel.mount_all()
    services = kernel.services.snapshot()
    placeholders = [capability for capability in services if type(kernel.services.get(capability)) is object]
    provider = kernel.services.get("model_provider")
    if not isinstance(provider, Provider):
        raise RuntimeError("model provider service has invalid type")
    provider_caps = provider.capabilities
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
        "placeholder_services": placeholders,
        "provider_ready": profile != "openai" or bool(os.getenv("OPENAI_API_KEY")),
        "provider_live_credential_present": bool(os.getenv("OPENAI_API_KEY")) if profile == "openai" else False,
        "provider_supports_tools": provider_caps.supports_tools,
        "provider_tool_manifest_hash": provider_caps.tool_manifest_hash,
        "evidence_acquisition_available": provider_caps.evidence_acquisition_available,
        "pricing_metadata_authoritative": provider_caps.pricing_metadata_authoritative,
        "estimated_max_cost_per_call": provider_caps.estimated_max_cost_per_call,
        "pricing_preflight_status": "READY" if provider_caps.known_zero_cost or provider_caps.estimated_max_cost_per_call is not None else "REQUIRED_FOR_MULTI_CALL",
        "mcp_version": mcp_version,
        "secrets_printed": False,
    }


def _engine(profile: str) -> MiMicusEngine:
    return MiMicusEngine(_database_url(), profile=profile)


def _load_task(path: str) -> dict[str, object]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, str):
        return {"task": payload}
    if not isinstance(payload, dict):
        raise ValueError("task file must contain a JSON object or string")
    return payload


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
    p_run.add_argument("--max-concurrency", type=int, default=4)
    p_run.add_argument("--depth", choices=["fast", "normal", "deep"], default="normal")
    p_run.add_argument("--learn", action="store_true")

    p_plan = sub.add_parser("plan")
    p_plan.add_argument("--profile", choices=sorted(PROFILES), default="offline")
    p_plan.add_argument("--task-file", required=True)
    p_plan.add_argument("--max-agents", type=int, default=4)
    p_plan.add_argument("--max-concurrency", type=int, default=4)

    p_state = sub.add_parser("state")
    state_sub = p_state.add_subparsers(dest="state_command", required=True)
    p_inspect = state_sub.add_parser("inspect")
    p_inspect.add_argument("--run-id")

    p_replay = sub.add_parser("replay")
    p_replay.add_argument("run_id")

    p_bench = sub.add_parser("benchmark")
    p_bench.add_argument("--profile", choices=sorted(PROFILES), default="offline")
    p_bench.add_argument("--episodes", type=int, default=200)
    p_bench.add_argument("--output-dir", default="evidence/ORDER-003")

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
        kernel = build_kernel(args.profile, _database_url())
        print(
            json.dumps([plugin.manifest.model_dump(mode="json") | {"manifest_hash": plugin.manifest.manifest_hash} for plugin in kernel.plugins.values()], indent=2, sort_keys=True)
        )
        return 0
    if args.command == "run":
        payload = _load_task(args.task_file)
        payload.update(
            {
                "budget_usd": args.budget_usd,
                "max_agents": args.max_agents,
                "max_concurrency": args.max_concurrency,
                "depth": args.depth,
                "learn": args.learn,
            }
        )
        run_result = _engine(args.profile).run(RunRequest.model_validate(payload))
        print(run_result.model_dump_json(indent=2))
        return 0
    if args.command == "plan":
        payload = _load_task(args.task_file)
        request = RunRequest.model_validate(payload | {"max_agents": args.max_agents, "max_concurrency": args.max_concurrency})
        domain = request.domain or "general"
        scenario, _fixture = scenario_fixture(request)
        from mimicus.coalition.threat_profile import profile_task

        threat = profile_task(request.task, domain, scenario)
        engine = _engine(args.profile)
        candidates = engine.services.agent_factory.candidates()[: request.max_agents]
        specs = engine.services.falsifiers.specs(domain)
        keys = _spec_keys(threat.required_capabilities, scenario)
        plan = compile_morphology(
            task_hash=sha256_obj({"task": request.task, "domain": domain}),
            selected_fingerprints=[row.fingerprint for row in candidates if row.capabilities & set(threat.required_capabilities)][: request.max_agents],
            falsifier_hashes=[specs[key].hash for key in keys],
            complexity=threat.complexity,
            required_capabilities=threat.required_capabilities,
            max_concurrency=request.max_concurrency,
            learn=request.learn,
        )
        print(json.dumps(plan.as_dict(), indent=2, sort_keys=True))
        return 0
    if args.command == "state":
        print(json.dumps(Repository(_database_url()).inspect_state(args.run_id), indent=2, sort_keys=True))
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
            raise SystemExit("ORDER-003 reference benchmark is offline only")
        out = Path(args.output_dir)
        report = write_benchmark(out / "BENCHMARK.json", out / "BENCHMARK.md", args.episodes)
        print(
            json.dumps(
                {
                    "episodes": report["episodes_per_architecture"],
                    "total_runs": report["total_architecture_episodes"],
                    "output": str(out),
                    "anti_rigging": report["anti_rigging"]["passed"],
                }
            )
        )
        return 0
    if args.command == "serve":
        from mimicus.interfaces.mcp_server import serve

        serve(args.profile, args.host, args.port)
        return 0
    raise RuntimeError("unreachable command")


if __name__ == "__main__":
    raise SystemExit(main())
