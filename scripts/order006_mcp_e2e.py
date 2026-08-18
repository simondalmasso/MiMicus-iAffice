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


def _run_args() -> dict[str, Any]:
    return {
        "task": "Assess the supplied structured bundle.",
        "domain": "finance",
        "evidence": [
            {
                "origin": "mcp://order006/numeric-registry",
                "independence_cluster": "order006-numeric-registry",
                "content": "Structured numeric bundle with a four percent annualized mismatch.",
                "extracted_facts": {"price": 10.0, "users": 10.0, "price_period": "monthly", "claimed": 1248.0},
            }
        ],
        "budget_usd": 0.0,
        "max_agents": 4,
        "depth": "normal",
        "learn": True,
    }


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="order006-mcp-") as directory:
        database_url = f"sqlite:///{Path(directory) / 'mcp.db'}"
        first_process, first_url = _start(database_url)
        try:
            first = asyncio.run(_call(first_url, "run_mimicus", _run_args()))
            assert first["falsifiers"] and first["falsifiers"][0]["verdict"] == "PASS"
            assert first["final_claims"]
            claim_hash = str(first["final_claims"][0]["claim_hash"])
            run_id = str(first["run_id"])
            execution_hash = str(first["falsifiers"][0]["execution_snapshot_hash"])
            evidence_hashes = list(first["evidence_provenance"]["provider_input_evidence_hashes"])
            verified = asyncio.run(
                _call(
                    first_url,
                    "submit_verification",
                    {
                        "run_id": run_id,
                        "claim_hash": claim_hash,
                        "verified_status": "FALSIFIED",
                        "authority_class": "deterministic_oracle",
                        "verifier_id": "oracle:order006-mcp-registry",
                        "observed_at": "2026-08-18T13:00:00+00:00",
                        "source_independence_cluster": "order006-mcp-registry-v1",
                        "evidence_hashes": evidence_hashes,
                        "snapshot_hashes": [execution_hash],
                    },
                )
            )
            assert verified["accepted"] is True
            assert verified["attributions"]
            assert verified["germinal"] is not None
            fetched_before = asyncio.run(_call(first_url, "get_mimicus_run", {"run_id": run_id}))
            assert fetched_before.get("found") is True
            assert fetched_before.get("replay_state", {}).get("verified") is True
            assert fetched_before.get("verification_receipts")
            assert fetched_before.get("swarm_learning", {}).get("marginal_value")
        finally:
            _stop(first_process)

        second_process, second_url = _start(database_url)
        try:
            fetched_after = asyncio.run(_call(second_url, "get_mimicus_run", {"run_id": run_id}))
            assert fetched_after.get("found") is True
            assert fetched_after.get("replay_state", {}).get("verified") is True
            assert fetched_after.get("verification_receipts")
            assert fetched_after.get("swarm_learning", {}).get("marginal_value")
            rerun = asyncio.run(_call(second_url, "run_mimicus", _run_args()))
            assert rerun.get("persistent_falsifiers_reused")
            assert rerun["falsifiers"] and rerun["falsifiers"][0]["verdict"] == "FAIL"
        finally:
            _stop(second_process)

    payload = {
        "pass": True,
        "transport": "streamable-http",
        "path": "/mcp",
        "server_process_restarted": True,
        "openai_key_required": False,
        "first_run": {
            "run_id": run_id,
            "claim_hash": claim_hash,
            "parent_falsifier_verdict": first["falsifiers"][0]["verdict"],
            "execution_snapshot_hash": execution_hash,
            "evidence_hashes": evidence_hashes,
        },
        "verification": {
            "accepted": verified["accepted"],
            "receipt_hash": verified["receipt"]["receipt_hash"],
            "attributions": verified["attributions"],
            "germinal": verified["germinal"],
        },
        "restart": {
            "receipt_persisted": bool(fetched_after["verification_receipts"]),
            "learned_state_reused": bool(fetched_after["swarm_learning"]["marginal_value"]),
            "replay_verified": fetched_after["replay_state"]["verified"],
            "rerun_id": rerun["run_id"],
            "promoted_falsifier_reused": rerun["persistent_falsifiers_reused"],
            "later_verdict": rerun["falsifiers"][0]["verdict"],
        },
    }
    (output_dir / "MCP_E2E.json").write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("evidence/ORDER-006")
    payload = run(output)
    print(json.dumps({"ORDER_006_MCP_E2E": "PASS", "run_id": payload["first_run"]["run_id"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
