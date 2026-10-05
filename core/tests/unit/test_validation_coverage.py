from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import types
from pathlib import Path

import pytest
from pydantic import ValidationError

from mimicus.agents.phenotypes import PHENOTYPES
from mimicus.config import Settings
from mimicus.falsifiers.builtins import builtin_specs
from mimicus.falsifiers.spec import FalsifierSpec
from mimicus.germinal.mutate import mutate_params
from mimicus.interfaces import mcp_server
from mimicus.interfaces.cli import main
from mimicus.providers.openai_agents import OpenAIAgentsProvider
from mimicus.storage.migrations_adapter import upgrade
from mimicus.validation import e2e, worker


def test_phenotypes_and_settings_validation(monkeypatch) -> None:
    assert len(PHENOTYPES) == 5
    monkeypatch.setenv("DATABASE_URL", "sqlite:///legacy.db")
    monkeypatch.setenv("MIMICUS_DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("MIMICUS_MAX_AGENTS", "4")
    settings = Settings.from_env("offline")
    settings.validate()
    assert settings.database_url == "sqlite:///:memory:"
    for bad in [
        Settings(profile="bad"),
        Settings(max_agents=0),
        Settings(max_tests=0),
        Settings(information_floor=-1),
    ]:
        with pytest.raises(ValueError):
            bad.validate()


def test_mutation_revalidates_no_source() -> None:
    parent = builtin_specs()["F1"]
    with pytest.raises(ValidationError):
        mutate_params(
            parent,
            new_version="2",
            params={"python": "untrusted"},
            triggering_snapshot_hash="a" * 64,
            catches_triggering_evasion=True,
        )


def test_process_scenarios_01_to_11_direct(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("MIMICUS_DATABASE_URL", f"sqlite:///{tmp_path / 'worker.db'}")
    results = [worker.SCENARIOS[f"{i:02d}"]() for i in range(1, 12)]
    assert all(row["pass"] for row in results)


def test_e2e_runner_success_and_failure_branches(tmp_path, monkeypatch) -> None:
    calls = 0

    def fake_run(*args, **kwargs):
        nonlocal calls
        calls += 1
        key = args[0][-1]
        if key == "03":
            return subprocess.CompletedProcess(args[0], 1, stdout="bad", stderr="boom")
        return subprocess.CompletedProcess(
            args[0],
            0,
            stdout=json.dumps({"scenario": key, "pass": True}) + "\n",
            stderr="",
        )

    monkeypatch.setattr(e2e.subprocess, "run", fake_run)
    report = e2e.run_all(tmp_path / "E2E.json")
    assert calls == 12
    assert report["passed"] is False
    assert (tmp_path / "E2E.json").exists()


def test_mcp_server_with_fake_sdk(monkeypatch) -> None:
    mcp_module = types.ModuleType("mcp")
    server_module = types.ModuleType("mcp.server")
    types_module = types.ModuleType("mcp_types")

    class ToolAnnotations:
        @classmethod
        def model_validate(cls, payload):
            return payload

    class MCPServer:
        def __init__(self, *args, **kwargs):
            self.tools = {}
            self.run_kwargs = None

        def tool(self, **kwargs):
            def decorator(fn):
                self.tools[fn.__name__] = (fn, kwargs)
                return fn

            return decorator

        def run(self, **kwargs):
            self.run_kwargs = kwargs

    server_module.MCPServer = MCPServer
    types_module.ToolAnnotations = ToolAnnotations
    monkeypatch.setitem(sys.modules, "mcp", mcp_module)
    monkeypatch.setitem(sys.modules, "mcp.server", server_module)
    monkeypatch.setitem(sys.modules, "mcp_types", types_module)
    monkeypatch.setenv("MIMICUS_DATABASE_URL", "sqlite:///:memory:")
    mcp_server._ENGINES.clear()
    server = mcp_server.create_mcp_server("offline")
    run_fn = server.tools["run_mimicus"][0]
    get_fn = server.tools["get_mimicus_run"][0]
    result = run_fn("K3 TAM 12x mismatch", domain="finance", evidence=None, budget_usd=0.0, max_agents=4, depth="normal", learn=True)
    fetched = get_fn(result["run_id"])
    assert fetched["found"] is True
    assert get_fn("missing")["found"] is False
    server.run(transport="streamable-http")
    assert server.run_kwargs["transport"] == "streamable-http"


def test_mcp_serve_with_fake_create(monkeypatch) -> None:
    observed = {}
    fake = types.SimpleNamespace(run=lambda **kwargs: observed.update(kwargs))
    monkeypatch.setattr(mcp_server, "create_mcp_server", lambda profile: fake)
    mcp_server.serve("offline", "127.0.0.1", 9999)
    assert observed["streamable_http_path"] == "/mcp"
    assert observed["stateless_http"] is True
    with pytest.raises(ValueError, match="loopback-only"):
        mcp_server.serve("offline", "0.0.0.0", 9999)


def test_worker_mcp_with_fake_transport(monkeypatch, tmp_path) -> None:
    class Proc:
        def terminate(self):
            self.terminated = True

        def wait(self, timeout=None):
            return 0

        def kill(self):
            self.killed = True

    async def fake_call(url):
        return {
            "run": {"status": "answered", "run_id": "r"},
            "fetched": {"found": True, "replay_state": {"verified": True}},
        }

    monkeypatch.setattr(worker.subprocess, "Popen", lambda *args, **kwargs: Proc())
    monkeypatch.setattr(worker, "_mcp_call", fake_call)
    monkeypatch.setenv("MIMICUS_DATABASE_URL", f"sqlite:///{tmp_path / 'mcp.db'}")
    assert worker.scenario_12_mcp()["pass"] is True


def test_migration_adapter_and_cli_db(tmp_path, monkeypatch, capsys) -> None:
    db = tmp_path / "mig.db"
    url = f"sqlite:///{db}"
    upgrade(url, str(Path(__file__).parents[2] / "alembic.ini"))
    assert db.exists()
    monkeypatch.chdir(Path(__file__).parents[2])
    monkeypatch.setenv("MIMICUS_DATABASE_URL", f"sqlite:///{tmp_path / 'cli-mig.db'}")
    assert main(["db", "upgrade"]) == 0
    assert "upgraded" in capsys.readouterr().out


def test_openai_provider_timeout(monkeypatch) -> None:
    module = types.ModuleType("agents")

    class Agent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class Runner:
        @staticmethod
        async def run(agent, task, max_turns):
            await asyncio.sleep(0.1)
            return None

    module.Agent = Agent
    module.Runner = Runner
    monkeypatch.setitem(sys.modules, "agents", module)
    provider = OpenAIAgentsProvider("x", timeout_seconds=0.001)
    with pytest.raises(TimeoutError):
        asyncio.run(provider.generate_async("t", "synthesizer", "d"))


def test_unknown_primitive_rejected() -> None:
    payload = builtin_specs()["F1"].model_dump()
    payload["primitive"] = "unknown"
    with pytest.raises(ValidationError):
        FalsifierSpec.model_validate(payload)
