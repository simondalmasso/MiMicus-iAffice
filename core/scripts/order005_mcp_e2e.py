from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from mimicus.memory.models import MemoryItem
from mimicus.storage.repository import Repository
from mimicus.types import MemoryStatus


def _port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _start(database_url: str) -> tuple[subprocess.Popen[str], str]:
    port = _port()
    env = os.environ.copy()
    env.pop("OPENAI_API_KEY", None)
    env["MIMICUS_DATABASE_URL"] = database_url
    process = subprocess.Popen(
        [sys.executable, "-m", "mimicus.interfaces.cli", "serve", "--profile", "offline", "--host", "127.0.0.1", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    return process, f"http://127.0.0.1:{port}/mcp"


async def _call(url: str, tool: str, args: dict[str, Any]) -> dict[str, Any]:
    from mcp import Client

    last_error: Exception | None = None
    for _ in range(40):
        try:
            async with Client(url) as client:
                response = await client.call_tool(tool, args)
                content = response.structured_content or {}
                result = content.get("result", content)
                if isinstance(result, dict):
                    return result
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(0.25)
    raise RuntimeError(f"MCP call failed for {tool}: {last_error}")


def _stop(process: subprocess.Popen[str]) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="order005-mcp-") as directory:
        database_url = f"sqlite:///{Path(directory) / 'mcp.db'}"
        repo = Repository(database_url)
        blocked = MemoryItem(
            claim_hash="b" * 64,
            content="blocked memory must not enter runtime context",
            owner_fingerprint="external-untrusted",
            domain="finance",
            origin_clusters=["untrusted"],
            authority=0.99,
            status=MemoryStatus.QUARANTINED,
        )
        repo.save_memory_transition(blocked, reason="ORDER-005 MCP negative memory fixture", from_status="candidate")

        first_process, first_url = _start(database_url)
        try:
            words_only = asyncio.run(
                _call(
                    first_url,
                    "run_mimicus",
                    {
                        "task": "TAM numeric price revenue 12x mismatch",
                        "domain": "finance",
                        "budget_usd": 0.0,
                        "max_agents": 4,
                        "depth": "normal",
                        "learn": False,
                    },
                )
            )
            assert words_only["status"] == "inconclusive"
            assert words_only["evidence_provenance"]["provider_input_evidence_hashes"] == []
            assert blocked.memory_id not in words_only.get("persistent_memory_reused", [])

            with_evidence = asyncio.run(
                _call(
                    first_url,
                    "run_mimicus",
                    {
                        "task": "TAM numeric price revenue 12x mismatch",
                        "domain": "finance",
                        "evidence": [
                            {
                                "origin": "mcp://caller/tam-report",
                                "independence_cluster": "caller-tam",
                                "content": "Explicit TAM inputs from the caller",
                                "extracted_facts": {"price": 10.0, "users": 100.0, "price_period": "monthly", "claimed": 1000.0},
                            }
                        ],
                        "budget_usd": 0.0,
                        "max_agents": 4,
                        "depth": "normal",
                        "learn": False,
                    },
                )
            )
            assert with_evidence["status"] == "answered"
            assert with_evidence["evidence_provenance"]["provider_input_evidence_hashes"]
            assert blocked.memory_id not in with_evidence.get("persistent_memory_reused", [])
            run_id = str(with_evidence["run_id"])
        finally:
            _stop(first_process)

        second_process, second_url = _start(database_url)
        try:
            fetched = asyncio.run(_call(second_url, "get_mimicus_run", {"run_id": run_id}))
            assert fetched.get("found") is True
            assert fetched.get("replay_state", {}).get("verified") is True
            evidence_rows = fetched.get("evidence", [])
            hashes = {str(row.get("evidence_hash")) for row in evidence_rows}
            expected = set(with_evidence["evidence_provenance"]["provider_input_evidence_hashes"])
            assert expected <= hashes
        finally:
            _stop(second_process)

    payload = {
        "pass": True,
        "transport": "streamable-http",
        "path": "/mcp",
        "fixture_flags_exposed": False,
        "words_only": {
            "run_id": words_only["run_id"],
            "status": words_only["status"],
            "provider_input_evidence_hashes": words_only["evidence_provenance"]["provider_input_evidence_hashes"],
        },
        "with_evidence": {
            "run_id": with_evidence["run_id"],
            "status": with_evidence["status"],
            "provider_input_evidence_hashes": with_evidence["evidence_provenance"]["provider_input_evidence_hashes"],
        },
        "blocked_memory_id": blocked.memory_id,
        "blocked_memory_reused": False,
        "server_process_restarted": True,
        "restart_replay_verified": fetched["replay_state"]["verified"],
        "restart_evidence_resolved": True,
        "openai_key_required": False,
    }
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    (output_dir / "MCP_RUNTIME_EVIDENCE_E2E.json").write_text(text, encoding="utf-8")
    (output_dir / "MCP_E2E.json").write_text(text, encoding="utf-8")
    return payload


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("evidence/ORDER-005")
    result = run(output)
    print(json.dumps({"ORDER_005_MCP_E2E": "PASS", "run_id": result["with_evidence"]["run_id"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
