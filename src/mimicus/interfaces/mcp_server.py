from __future__ import annotations

import os
from typing import Any, Literal

from mimicus.claims.evidence_bundle import EvidenceInput
from mimicus.config import Settings
from mimicus.orchestration.engine import MiMicusEngine, RunRequest

_ENGINES: dict[tuple[str, str], MiMicusEngine] = {}


def _engine(profile: str = "offline") -> MiMicusEngine:
    database_url = os.getenv("MIMICUS_DATABASE_URL", "sqlite:///mimicus.db")
    key = (profile, database_url)
    if key not in _ENGINES:
        _ENGINES[key] = MiMicusEngine(database_url, profile=profile)
    return _ENGINES[key]


def create_mcp_server(profile: str = "offline") -> Any:
    from mcp.server import MCPServer
    from mcp_types import ToolAnnotations

    server = MCPServer(
        "MiMicus",
        version="0.2.2",
        description="Persistent auditable agentic immune swarm with executable morphology DAGs and bounded parallelism.",
    )
    run_annotations = ToolAnnotations.model_validate({"readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": profile == "openai"})
    get_annotations = ToolAnnotations.model_validate({"readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False})

    @server.tool(annotations=run_annotations)
    def run_mimicus(
        task: str,
        domain: str | None = None,
        evidence: list[dict[str, Any]] | None = None,
        budget_usd: float = 0.0,
        max_agents: int = 4,
        depth: Literal["fast", "normal", "deep"] = "normal",
        learn: bool = False,
        max_concurrency: int = 4,
    ) -> dict[str, Any]:
        """Run MiMicus with persistent immune state, a hashed execution DAG and bounded concurrency."""
        request = RunRequest(
            task=task,
            domain=domain,
            evidence=[EvidenceInput.model_validate(item) for item in (evidence or [])],
            budget_usd=budget_usd,
            max_agents=max_agents,
            max_concurrency=max_concurrency,
            depth=depth,
            learn=learn,
        )
        return _engine(profile).run(request).model_dump(mode="json")

    @server.tool(annotations=get_annotations)
    def get_mimicus_run(run_id: str) -> dict[str, Any]:
        """Read a persisted MiMicus run, replay state, DAG summaries and immune-state audit context."""
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
