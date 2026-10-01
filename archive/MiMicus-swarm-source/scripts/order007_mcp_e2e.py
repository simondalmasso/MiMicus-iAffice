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

from mimicus.orchestration.engine import MiMicusEngine
from mimicus.storage.swarm_state import SwarmStateStore


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
        [
            sys.executable,
            "-m",
            "mimicus.interfaces.cli",
            "serve",
            "--profile",
            "offline",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
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


async def _run_schema(url: str) -> dict[str, Any]:
    from mcp import Client

    last_error: Exception | None = None
    for _ in range(40):
        try:
            async with Client(url) as client:
                response = await client.list_tools()
                tools = getattr(response, "tools", response)
                for tool in tools:
                    if getattr(tool, "name", None) != "run_mimicus":
                        continue
                    schema = getattr(tool, "input_schema", None)
                    if schema is None:
                        schema = getattr(tool, "inputSchema", None)
                    if isinstance(schema, dict):
                        return schema
                    if hasattr(schema, "model_dump"):
                        dumped = schema.model_dump(mode="json")
                        if isinstance(dumped, dict):
                            return dumped
                raise AssertionError("run_mimicus tool schema not found")
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(0.25)
    raise RuntimeError(f"MCP list_tools failed: {last_error}")


def _stop(process: subprocess.Popen[str]) -> None:
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _run_args() -> dict[str, Any]:
    return {
        "task": "Assess the supplied structured material.",
        "domain": "finance",
        "evidence": [
            {
                "origin": "mcp://order007/numeric",
                "independence_cluster": "order007-mcp-runtime",
                "content": "Structured numeric evidence.",
                "extracted_facts": {
                    "price": 10.0,
                    "users": 10.0,
                    "price_period": "monthly",
                    "claimed": 1248.0,
                },
            }
        ],
        "budget_usd": 0.0,
        "max_agents": 2,
        "depth": "deep",
        "learn": True,
    }


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="order007-mcp-") as directory:
        database_url = f"sqlite:///{Path(directory) / 'mcp.db'}"
        token = "order007-mcp-authority-token-v1"
        verifier_id = "oracle:order007-mcp"
        cluster = "order007-mcp-authority-v1"
        MiMicusEngine(database_url).register_verifier_authority(
            verifier_id=verifier_id,
            authority_class="deterministic_oracle",
            source_independence_cluster=cluster,
            auth_token=token,
        )
        first_process, first_url = _start(database_url)
        try:
            schema = asyncio.run(_run_schema(first_url))
            properties = set((schema.get("properties") or {}).keys())
            assert {"fixture", "core_semantics", "source_mode"}.isdisjoint(properties)

            first = asyncio.run(_call(first_url, "run_mimicus", _run_args()))
            assert first["evidence_provenance"]["source_mode"] == "runtime"
            assert first["swarm_decision"] and first["threat_profile"]
            assert first["falsifiers"] and first["final_claims"]
            run_id = str(first["run_id"])
            claim_hash = str(first["final_claims"][0]["claim_hash"])
            snapshot_hash = str(first["falsifiers"][0]["execution_snapshot_hash"])
            evidence_hashes = list(first["evidence_provenance"]["provider_input_evidence_hashes"])
            before = asyncio.run(_call(first_url, "get_mimicus_run", {"run_id": run_id}))
            assert before["found"] is True

            forged = asyncio.run(
                _call(
                    first_url,
                    "submit_verification",
                    {
                        "run_id": run_id,
                        "claim_hash": claim_hash,
                        "verified_status": "FALSIFIED",
                        "authority_class": "trusted_human",
                        "verifier_id": "human:forged-through-mcp",
                        "auth_token": "caller-cannot-create-trust",
                        "observed_at": "2026-08-18T16:00:00+00:00",
                        "source_independence_cluster": "caller-self-asserted",
                        "evidence_hashes": evidence_hashes,
                        "snapshot_hashes": [snapshot_hash],
                    },
                )
            )
            assert forged["accepted"] is False
            assert forged["receipt"]["rejection_reason"] == "verifier_not_authorized"
            after_forge = asyncio.run(_call(first_url, "get_mimicus_run", {"run_id": run_id}))
            assert after_forge["verification_receipts"] == before["verification_receipts"]
            assert after_forge["swarm_learning"] == before["swarm_learning"]

            valid = asyncio.run(
                _call(
                    first_url,
                    "submit_verification",
                    {
                        "run_id": run_id,
                        "claim_hash": claim_hash,
                        "verified_status": "FALSIFIED",
                        "authority_class": "deterministic_oracle",
                        "verifier_id": verifier_id,
                        "auth_token": token,
                        "observed_at": "2026-08-18T17:00:00+00:00",
                        "source_independence_cluster": cluster,
                        "evidence_hashes": evidence_hashes,
                        "snapshot_hashes": [snapshot_hash],
                    },
                )
            )
            assert valid["accepted"] is True
            assert valid["attributions"]
            assert valid["removal_attributions"]
            fetched_before_restart = asyncio.run(_call(first_url, "get_mimicus_run", {"run_id": run_id}))
            assert fetched_before_restart["verification_receipts"]
            assert fetched_before_restart["replay_state"]["verified"] is True
        finally:
            _stop(first_process)

        second_process, second_url = _start(database_url)
        try:
            fetched_after = asyncio.run(_call(second_url, "get_mimicus_run", {"run_id": run_id}))
            assert fetched_after["found"] is True
            assert fetched_after["verification_receipts"]
            assert fetched_after["replay_state"]["verified"] is True
            rerun = asyncio.run(_call(second_url, "run_mimicus", _run_args()))
            assert rerun["evidence_provenance"]["source_mode"] == "runtime"
        finally:
            _stop(second_process)

        policies = SwarmStateStore(MiMicusEngine(database_url).repository.engine).verifier_policies()
        assert any(row["verifier_id"] == verifier_id for row in policies)

    payload = {
        "pass": True,
        "transport": "streamable-http",
        "path": "/mcp",
        "runtime_schema_properties": sorted(properties),
        "legacy_escape_fields_exposed": sorted({"fixture", "core_semantics", "source_mode"} & properties),
        "first_run": {
            "run_id": run_id,
            "claim_hash": claim_hash,
            "source_mode": first["evidence_provenance"]["source_mode"],
            "morphology": first["morphology"],
        },
        "forged_verification": {
            "accepted": forged["accepted"],
            "rejection_reason": forged["receipt"]["rejection_reason"],
            "learning_state_unchanged": after_forge["swarm_learning"] == before["swarm_learning"],
            "receipt_state_unchanged": after_forge["verification_receipts"] == before["verification_receipts"],
        },
        "authorized_verification": {
            "accepted": valid["accepted"],
            "receipt_hash": valid["receipt"]["receipt_hash"],
            "attributions": valid["attributions"],
            "removal_attributions": valid["removal_attributions"],
        },
        "restart": {
            "receipt_persisted": bool(fetched_after["verification_receipts"]),
            "replay_verified": fetched_after["replay_state"]["verified"],
            "policy_persisted": any(row["verifier_id"] == verifier_id for row in policies),
            "rerun_id": rerun["run_id"],
            "rerun_source_mode": rerun["evidence_provenance"]["source_mode"],
        },
    }
    (output_dir / "MCP_E2E.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("evidence/ORDER-007")
    payload = run(output)
    print(json.dumps({"ORDER_007_MCP_E2E": "PASS", "run_id": payload["first_run"]["run_id"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
