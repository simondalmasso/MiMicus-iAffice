from __future__ import annotations

import os
from typing import Any, Literal

from mimicus.config import Settings
from mimicus.orchestration.engine import MiMicusEngine, RunRequest
from mimicus.plugins.profiles import build_kernel

_ENGINE: MiMicusEngine | None = None


def _engine(profile: str = "offline") -> MiMicusEngine:
    global _ENGINE
    if _ENGINE is None:
        kernel = build_kernel(profile)
        kernel.mount_all()
        plugin_hashes = [plugin.manifest.manifest_hash for plugin in kernel.plugins.values()]
        provider = kernel.services.get("model_provider")
        database_url = os.getenv("MIMICUS_DATABASE_URL", "sqlite:///mimicus.db")
        _ENGINE = MiMicusEngine(database_url, plugin_hashes=plugin_hashes, provider=provider)
    return _ENGINE


def create_mcp_server(profile: str = "offline") -> Any:
    from mcp.server import MCPServer
    from mcp_types import ToolAnnotations

    server = MCPServer(
        "MiMicus",
        version="0.1.0",
        description="Auditable agentic immune swarm with deterministic offline reference runtime.",
    )
    run_annotations = ToolAnnotations.model_validate({"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": profile == "openai"})
    get_annotations = ToolAnnotations.model_validate({"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False})

    @server.tool(annotations=run_annotations)
    def run_mimicus(
        task: str,
        domain: str | None = None,
        budget_usd: float = 0.0,
        max_agents: int = 4,
        depth: Literal["fast", "normal", "deep"] = "normal",
        learn: bool = False,
    ) -> dict[str, Any]:
        """Run MiMicus with sealed independent first pass and evidence-gated learning."""
        request = RunRequest(task=task, domain=domain, budget_usd=budget_usd, max_agents=max_agents, depth=depth, learn=learn)
        return _engine(profile).run(request).model_dump(mode="json")

    @server.tool(annotations=get_annotations)
    def get_mimicus_run(run_id: str) -> dict[str, Any]:
        """Read a persisted MiMicus run including provenance and replay verification state."""
        result = _engine(profile).get_run(run_id)
        if result is None:
            return {"found": False, "run_id": run_id}
        return {"found": True, **result}

    return server


def serve(profile: str = "offline", host: str = "127.0.0.1", port: int = 8765) -> None:
    Settings(profile=profile).validate()
    server = create_mcp_server(profile)
    server.run(
        transport="streamable-http",
        host=host,
        port=port,
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
    )
