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


def _run_args(label: str, *, learn: bool) -> dict[str, Any]:
    return {
        "task": f"Audit ORDER-008 runtime evidence ({label}).",
        "domain": "finance",
        "evidence": [
            {
                "origin": f"mcp://order008/{label}",
                "independence_cluster": f"order008-mcp-{label}",
                "content": "Structured annual numeric evidence.",
                "extracted_facts": {
                    "price": 100.0,
                    "users": 12.0,
                    "price_period": "annual",
                    "claimed": 1200.0,
                },
            }
        ],
        "budget_usd": 0.0,
        "max_agents": 1,
        "max_concurrency": 1,
        "depth": "deep",
        "learn": learn,
    }


def _selected_claim(run: dict[str, Any]) -> dict[str, Any]:
    selected = set(run["swarm_decision"]["selected_claim_hashes"])
    assert selected
    return next(row for row in run["final_claims"] if row["claim_hash"] in selected)


def _snapshot_for(run: dict[str, Any], claim_hash: str) -> str:
    return next(
        str(row["execution_snapshot_hash"])
        for row in run["falsifiers"]
        if claim_hash in set(row["target_claim_hashes"])
    )


def run(output_dir: Path) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="order008-mcp-") as directory:
        database_url = f"sqlite:///{Path(directory) / 'mcp.db'}"
        token = "order008-mcp-authority-token-v1"
        verifier_id = "oracle:order008-mcp"
        cluster = "order008-mcp-authority-v1"
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

            first = asyncio.run(_call(first_url, "run_mimicus", _run_args("learn", learn=True)))
            assert first["evidence_provenance"]["source_mode"] == "runtime"
            claim = _selected_claim(first)
            claim_hash = str(claim["claim_hash"])
            snapshot_hash = _snapshot_for(first, claim_hash)
            evidence_hashes = list(claim.get("evidence_refs") or first["evidence_provenance"]["provider_input_evidence_hashes"])
            assert evidence_hashes

            verified = asyncio.run(
                _call(
                    first_url,
                    "submit_verification",
                    {
                        "run_id": first["run_id"],
                        "claim_hash": claim_hash,
                        "verified_status": "SUPPORTED",
                        "authority_class": "deterministic_oracle",
                        "verifier_id": verifier_id,
                        "auth_token": token,
                        "observed_at": "2026-08-20T15:00:00+00:00",
                        "source_independence_cluster": cluster,
                        "evidence_hashes": evidence_hashes,
                        "snapshot_hashes": [snapshot_hash],
                    },
                )
            )
            assert verified["accepted"] is True
            assert verified["learning_enabled_for_run"] is True
            assert verified["memory_changes"]
            memory_id = str(verified["memory_changes"][0]["memory_id"])
            first_receipt_hash = str(verified["receipt"]["receipt_hash"])
            fetched_first = asyncio.run(_call(first_url, "get_mimicus_run", {"run_id": first["run_id"]}))
            assert fetched_first["found"] is True
            assert fetched_first["replay_state"]["verified"] is True
        finally:
            _stop(first_process)

        second_process, second_url = _start(database_url)
        try:
            after_restart = asyncio.run(_call(second_url, "get_mimicus_run", {"run_id": first["run_id"]}))
            assert after_restart["found"] is True
            assert any(
                row["receipt_hash"] == first_receipt_hash and row["learning_active"]
                for row in after_restart["verification_receipts"]
            )
            reused = asyncio.run(_call(second_url, "run_mimicus", _run_args("reuse", learn=False)))
            assert memory_id in reused["persistent_memory_reused"]

            superseding = asyncio.run(
                _call(
                    second_url,
                    "submit_verification",
                    {
                        "run_id": first["run_id"],
                        "claim_hash": claim_hash,
                        "verified_status": "FALSIFIED",
                        "authority_class": "deterministic_oracle",
                        "verifier_id": verifier_id,
                        "auth_token": token,
                        "observed_at": "2026-08-20T15:01:00+00:00",
                        "source_independence_cluster": cluster,
                        "evidence_hashes": evidence_hashes,
                        "snapshot_hashes": [snapshot_hash],
                        "supersedes_receipt_hash": first_receipt_hash,
                    },
                )
            )
            assert superseding["accepted"] is True
            assert superseding["revocation"]["memory"] >= 1
            superseding_hash = str(superseding["receipt"]["receipt_hash"])
        finally:
            _stop(second_process)

        third_process, third_url = _start(database_url)
        try:
            final_state = asyncio.run(_call(third_url, "get_mimicus_run", {"run_id": first["run_id"]}))
            assert final_state["found"] is True
            old = next(row for row in final_state["verification_receipts"] if row["receipt_hash"] == first_receipt_hash)
            new = next(row for row in final_state["verification_receipts"] if row["receipt_hash"] == superseding_hash)
            assert old["learning_active"] is False
            assert old["superseded_by_hash"] == superseding_hash
            assert new["learning_active"] is True
            assert final_state["replay_state"]["verified"] is True

            excluded = asyncio.run(_call(third_url, "run_mimicus", _run_args("after-revoke", learn=False)))
            assert memory_id not in excluded["persistent_memory_reused"]
        finally:
            _stop(third_process)

        policies = SwarmStateStore(MiMicusEngine(database_url).repository.engine).verifier_policies()
        assert any(row["verifier_id"] == verifier_id for row in policies)

    payload = {
        "pass": True,
        "transport": "streamable-http",
        "path": "/mcp",
        "runtime_schema_properties": sorted(properties),
        "legacy_escape_fields_exposed": sorted({"fixture", "core_semantics", "source_mode"} & properties),
        "first_run_id": first["run_id"],
        "claim_hash": claim_hash,
        "snapshot_hash": snapshot_hash,
        "memory_id": memory_id,
        "first_receipt_hash": first_receipt_hash,
        "restart_before_revocation": {
            "receipt_persisted_active": True,
            "verified_memory_reused": memory_id in reused["persistent_memory_reused"],
        },
        "supersession": {
            "receipt_hash": superseding_hash,
            "revocation": superseding["revocation"],
        },
        "restart_after_revocation": {
            "old_receipt_inactive": old["learning_active"] is False,
            "new_receipt_active": new["learning_active"] is True,
            "revoked_memory_excluded": memory_id not in excluded["persistent_memory_reused"],
            "semantic_replay_verified": final_state["replay_state"]["verified"],
        },
        "policy_persisted": any(row["verifier_id"] == verifier_id for row in policies),
    }
    (output_dir / "MCP_E2E.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload


def main() -> int:
    output = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("evidence/ORDER-008")
    payload = run(output)
    print(json.dumps({"ORDER_008_MCP_E2E": "PASS", "run_id": payload["first_run_id"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
