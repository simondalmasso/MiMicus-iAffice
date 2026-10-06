from __future__ import annotations

import ipaddress
import os
from datetime import datetime
from typing import Any, Literal

from mimicus.claims.evidence_bundle import EvidenceInput
from mimicus.config import Settings
from mimicus.effects.admission import (
    ActionAdmissionError,
    ActionAdmissionPolicy,
    ActionAdmissionRule,
    ToolEffectClass,
)
from mimicus.orchestration.engine import MiMicusEngine, RunRequest
from mimicus.verification.models import VerificationSubmission

_ENGINES: dict[tuple[str, str], MiMicusEngine] = {}

_MCP_ACTION_POLICY = ActionAdmissionPolicy(
    version="mcp-tool-effects-v1",
    rules=(
        ActionAdmissionRule(
            adapter="mcp",
            operation="run_mimicus",
            effect_class=ToolEffectClass.MUTATING,
        ),
        ActionAdmissionRule(
            adapter="mcp",
            operation="submit_verification",
            effect_class=ToolEffectClass.MUTATING,
        ),
        ActionAdmissionRule(
            adapter="mcp",
            operation="get_mimicus_run",
            effect_class=ToolEffectClass.READ_ONLY,
        ),
    ),
)


def _mcp_annotation_payload(tool_name: str, *, profile: str) -> dict[str, bool]:
    decision = _MCP_ACTION_POLICY.require_known(adapter="mcp", operation=tool_name)
    read_only = decision.effect_class == ToolEffectClass.READ_ONLY
    return {
        "readOnlyHint": read_only,
        "destructiveHint": False,
        "idempotentHint": read_only,
        "openWorldHint": tool_name == "run_mimicus" and profile in {"openai", "nvidia"},
    }


def _declared_mcp_tools() -> set[str]:
    return {
        rule.operation
        for rule in _MCP_ACTION_POLICY.rules
        if rule.adapter == "mcp"
    }


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
        version="0.3.1",
        description="Persistent auditable immune swarm with authenticated verified adjudication and immutable claim lineage.",
    )
    registered_tools: set[str] = set()

    def admitted_tool(tool_name: str):
        annotations = ToolAnnotations.model_validate(
            _mcp_annotation_payload(tool_name, profile=profile)
        )
        registered_tools.add(tool_name)
        return server.tool(annotations=annotations)

    @admitted_tool("run_mimicus")
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
        request = RunRequest(
            task=task,
            domain=domain,
            evidence=[EvidenceInput.model_validate(item) for item in (evidence or [])],
            budget_usd=budget_usd,
            max_agents=max_agents,
            max_concurrency=max_concurrency,
            depth=depth,
            learn=learn,
            source_mode="runtime",
        )
        return _engine(profile).run(request).model_dump(mode="json")

    @admitted_tool("submit_verification")
    def submit_verification(
        run_id: str,
        claim_hash: str,
        verified_status: Literal["SUPPORTED", "FALSIFIED"],
        authority_class: str,
        verifier_id: str,
        auth_token: str,
        observed_at: str,
        source_independence_cluster: str,
        evidence_hashes: list[str] | None = None,
        snapshot_hashes: list[str] | None = None,
        supersedes_receipt_hash: str | None = None,
        appeal_of_receipt_hash: str | None = None,
    ) -> dict[str, Any]:
        # Labels remain caller-provided claims. Authority is granted only if the
        # server-side persisted verifier policy authenticates this credential
        # and all proof hashes bind to the target run.
        submission = VerificationSubmission(
            run_id=run_id,
            claim_hash=claim_hash,
            verified_status=verified_status,
            authority_class=authority_class,
            verifier_id=verifier_id,
            auth_token=auth_token,
            observed_at=datetime.fromisoformat(observed_at.replace("Z", "+00:00")),
            source_independence_cluster=source_independence_cluster,
            evidence_hashes=tuple(evidence_hashes or []),
            snapshot_hashes=tuple(snapshot_hashes or []),
            supersedes_receipt_hash=supersedes_receipt_hash,
            appeal_of_receipt_hash=appeal_of_receipt_hash,
        )
        return _engine(profile).submit_verification(submission)

    @admitted_tool("get_mimicus_run")
    def get_mimicus_run(run_id: str) -> dict[str, Any]:
        result = _engine(profile).get_run(run_id)
        if result is None:
            return {"found": False, "run_id": run_id}
        return {"found": True, **result}

    declared_tools = _declared_mcp_tools()
    if registered_tools != declared_tools:
        raise ActionAdmissionError(
            "MCP tool admission policy drift: "
            f"declared={sorted(declared_tools)} registered={sorted(registered_tools)}"
        )
    server_tools = getattr(server, "tools", None)
    if isinstance(server_tools, dict) and set(server_tools) != declared_tools:
        raise ActionAdmissionError(
            "MCP server tool surface drift: "
            f"declared={sorted(declared_tools)} actual={sorted(server_tools)}"
        )

    return server


def _is_loopback_host(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def serve(profile: str = "offline", host: str = "127.0.0.1", port: int = 8765) -> None:
    Settings(profile=profile).validate()
    if not _is_loopback_host(host):
        raise ValueError("MCP host must be loopback-only until transport authentication is implemented")
    server = create_mcp_server(profile)
    server.run(
        transport="streamable-http",
        host=host,
        port=port,
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
    )
