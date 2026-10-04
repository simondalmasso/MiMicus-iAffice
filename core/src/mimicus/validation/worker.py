from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
from collections.abc import Callable
from typing import Any

from mimicus.agents.bankruptcy import evaluate_bankruptcy, recover
from mimicus.agents.calibration import CalibrationRecord
from mimicus.coalition.selector import AgentCandidate, correlation
from mimicus.events.ledger import EventLedger
from mimicus.falsifiers.builtins import builtin_specs
from mimicus.germinal.center import evasion_farming_guard, germinal_demo
from mimicus.memory.gates import promotion_gate, write_gate
from mimicus.memory.models import MemoryItem
from mimicus.orchestration.engine import MiMicusEngine, RunRequest
from mimicus.orchestration.replay import verify_replay
from mimicus.types import BankruptcyState, MemoryStatus


def _engine() -> MiMicusEngine:
    return MiMicusEngine(os.getenv("MIMICUS_DATABASE_URL", "sqlite:///:memory:"))


def scenario_01_tam() -> dict[str, Any]:
    result = _engine().run(
        RunRequest(
            task="K3 TAM 12x mismatch",
            domain="finance",
            scenario="tam_12x",
            source_mode="fixture",
            fixture={"claim_statement": "TAM", "claim_type": "numeric", "price": 10.0, "users": 100.0, "price_period": "monthly", "claimed": 1000.0},
            learn=True,
        )
    )
    execution = result.falsifiers[0]
    assert execution["verdict"] == "FAIL"
    assert execution["primitive"] == "numeric_invariant"
    assert len(result.coalition["members"]) == 1
    assert result.replay_verified
    assert "numeric_invariant" in result.answer
    return {
        "scenario": "01_tam_12x",
        "pass": True,
        "run_id": result.run_id,
        "ledger_head": result.ledger_head,
        "coalition_size": 1,
        "primitive": "numeric_invariant",
    }


def scenario_02_echo() -> dict[str, Any]:
    result = _engine().run(
        RunRequest(
            task="source echo same origin citation",
            domain="research",
            scenario="echo_chamber",
            source_mode="fixture",
            fixture={"claim_statement": "sources", "claim_type": "factual", "clusters": ["origin-wire", "origin-wire"], "texts": ["same report", "same report"]},
        )
    )
    assert result.falsifiers[0]["verdict"] == "FAIL"
    assert result.falsifiers[0]["primitive"] == "source_independence"
    item = MemoryItem(
        claim_hash="a" * 64,
        content="echo",
        owner_fingerprint="a",
        domain="research",
        origin_clusters=["same"],
        authority=0.8,
        verified_clusters=["same", "same"],
    )
    assert promotion_gate(write_gate(item)).status == MemoryStatus.QUARANTINED
    return {
        "scenario": "02_source_echo",
        "pass": True,
        "run_id": result.run_id,
        "primitive": "source_independence",
        "memory_promotion_blocked": True,
    }


def scenario_03_freshness() -> dict[str, Any]:
    result = _engine().run(
        RunRequest(
            task="freshness stale current date evidence",
            domain="research",
            scenario="freshness",
            source_mode="fixture",
            fixture={"claim_statement": "freshness", "claim_type": "temporal", "evidence_date": "2025-01-01T00:00:00+00:00", "as_of": "2026-08-17T00:00:00+00:00"},
        )
    )
    assert result.falsifiers[0]["verdict"] == "FAIL"
    assert result.falsifiers[0]["primitive"] == "freshness"
    return {"scenario": "03_freshness", "pass": True, "run_id": result.run_id, "primitive": "freshness"}


def scenario_04_entailment() -> dict[str, Any]:
    result = _engine().run(
        RunRequest(
            task="citation figure entailment mismatch",
            domain="research",
            scenario="citation_entailment",
            source_mode="fixture",
            fixture={
                "claim_statement": "figure",
                "claim_type": "numeric",
                "claim_figure": 42,
                "evidence_spans": [{"span_id": "e1", "supported_figures": [41], "material_support": True}],
            },
        )
    )
    assert any(row["verdict"] == "FAIL" and row["primitive"] == "citation_entailment" for row in result.falsifiers)
    return {
        "scenario": "04_citation_entailment",
        "pass": True,
        "run_id": result.run_id,
        "primitive": "citation_entailment",
    }


def scenario_05_counterexample() -> dict[str, Any]:
    result = _engine().run(
        RunRequest(
            task="absence counterexample none exist",
            domain="research",
            scenario="counterexample",
            source_mode="fixture",
            fixture={"claim_statement": "absence", "claim_type": "factual", "absence_key": "target", "registry": {"target": {"id": "known"}}, "registry_snapshot_hash": "b" * 64},
        )
    )
    assert result.falsifiers[0]["verdict"] == "FAIL"
    assert result.falsifiers[0]["primitive"] == "counterexample_search"
    assert result.falsifiers[0]["evidence"]["counterexample"] is not None
    return {
        "scenario": "05_counterexample",
        "pass": True,
        "run_id": result.run_id,
        "primitive": "counterexample_search",
    }


def scenario_06_bankruptcy() -> dict[str, Any]:
    record = CalibrationRecord("fp", "finance")
    for _ in range(3):
        record.update(predicted_probability=0.9, outcome=False, canary=True)
    bankrupt = evaluate_bankruptcy(record)
    assert bankrupt.state == BankruptcyState.BANKRUPT
    assert recover(bankrupt, recovery_audition_passed=False).state == BankruptcyState.BANKRUPT
    assert recover(bankrupt, recovery_audition_passed=True).state == BankruptcyState.ACTIVE
    return {
        "scenario": "06_bankruptcy",
        "pass": True,
        "failure_streak": record.canary_failure_streak,
        "recovery_requires_audition": True,
    }


def scenario_07_clones() -> dict[str, Any]:
    clone1 = AgentCandidate("c1", "c1", frozenset({"numeric"}), "same", "same", "same", "same")
    clone2 = AgentCandidate("c2", "c2", frozenset({"numeric"}), "same", "same", "same", "same")
    distinct = AgentCandidate("d", "d", frozenset({"numeric"}), "other", "other", "other", "other")
    clone_corr = correlation(clone1, clone2)
    distinct_corr = correlation(clone1, distinct)
    assert clone_corr >= 0.75 and distinct_corr == 0.0
    clone_marginal = 1.0 - 0.8 * clone_corr
    distinct_marginal = 1.0 - 0.8 * distinct_corr
    assert clone_marginal < distinct_marginal / 2
    return {
        "scenario": "07_clone_correlation",
        "pass": True,
        "clone_correlation": clone_corr,
        "distinct_correlation": distinct_corr,
        "clone_marginal": clone_marginal,
        "distinct_marginal": distinct_marginal,
    }


def scenario_08_germinal() -> dict[str, Any]:
    result = germinal_demo()
    assert result["rejected_decision"] == "REJECT"
    assert result["promoted_decision"] == "PROMOTE"
    assert result["parent_preserved"] is True
    return {"scenario": "08_germinal", "pass": True, **result}


def scenario_09_memory_laundering() -> dict[str, Any]:
    original = write_gate(
        MemoryItem(
            claim_hash="a" * 64,
            content="untrusted",
            owner_fingerprint="a",
            domain="d",
            origin_clusters=["o"],
            authority=0.1,
        )
    )
    paraphrase = write_gate(
        MemoryItem(
            claim_hash="b" * 64,
            content="paraphrase",
            owner_fingerprint="b",
            domain="d",
            origin_clusters=["o"],
            authority=0.9,
            derived_from=[original.memory_id],
        ),
        [original],
    )
    repeated = write_gate(
        MemoryItem(
            claim_hash="c" * 64,
            content="repeated",
            owner_fingerprint="c",
            domain="d",
            origin_clusters=["o"],
            authority=0.9,
            derived_from=[paraphrase.memory_id],
        ),
        [paraphrase],
    )
    assert original.authority == paraphrase.authority == repeated.authority == 0.1
    assert promotion_gate(repeated).status == MemoryStatus.QUARANTINED
    return {
        "scenario": "09_memory_laundering",
        "pass": True,
        "authority_chain": [original.authority, paraphrase.authority, repeated.authority],
        "promotion_blocked": True,
    }


def scenario_10_evasion_farming() -> dict[str, Any]:
    assert not evasion_farming_guard([], 1_000_000)
    assert evasion_farming_guard(["pinned-ground-truth"], 1)
    return {"scenario": "10_evasion_farming", "pass": True, "report_count_alone_promotes": False}


def scenario_11_tamper() -> dict[str, Any]:
    ledger = EventLedger("tamper")
    ledger.append("run_started", {"x": 1})
    ledger.append("run_completed", {"x": 2})
    original_head = ledger.head
    tampered = [event.model_dump() for event in ledger.events]
    tampered[0]["payload"]["x"] = 999
    event_tamper_detected = not bool(verify_replay(tampered)["verified"])
    snapshot_mismatch_detected = not bool(verify_replay(ledger.events, "f" * 64)["verified"])
    spec = builtin_specs()["F1"]
    tampered_spec = spec.model_copy(update={"params": {"relative_tolerance": 0.1}})
    spec_tamper_detected = spec.hash != tampered_spec.hash
    assert event_tamper_detected and snapshot_mismatch_detected and spec_tamper_detected
    return {
        "scenario": "11_tamper_replay",
        "pass": True,
        "event_tamper_detected": True,
        "spec_tamper_detected": True,
        "snapshot_mismatch_detected": True,
        "original_head": original_head,
    }


async def _mcp_call(url: str) -> dict[str, Any]:
    from mcp import Client

    last_error: Exception | None = None
    for _ in range(40):
        try:
            async with Client(url) as client:
                run = await client.call_tool(
                    "run_mimicus",
                    {
                        "task": "K3 TAM 12x mismatch",
                        "domain": "finance",
                        "evidence": [
                            {
                                "origin": "mcp://order003-tam",
                                "independence_cluster": "order003-fixture",
                                "content": "Explicit historical TAM evidence",
                                "extracted_facts": {"price": 10.0, "users": 100.0, "price_period": "monthly", "claimed": 1000.0},
                            }
                        ],
                        "budget_usd": 0.0,
                        "max_agents": 4,
                        "depth": "normal",
                        "learn": True,
                    },
                )
                content = run.structured_content or {}
                payload = content.get("result", content)
                if isinstance(payload, dict) and "run_id" in payload:
                    fetched = await client.call_tool("get_mimicus_run", {"run_id": payload["run_id"]})
                    fetched_content = fetched.structured_content or {}
                    fetched_payload = fetched_content.get("result", fetched_content)
                    return {"run": payload, "fetched": fetched_payload}
        except Exception as exc:
            last_error = exc
            await asyncio.sleep(0.25)
    raise RuntimeError(f"MCP client failed: {last_error}")


def scenario_12_mcp() -> dict[str, Any]:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = os.environ.copy()
    env.pop("OPENAI_API_KEY", None)
    env["MIMICUS_DATABASE_URL"] = os.getenv("MIMICUS_DATABASE_URL", "sqlite:///mcp-e2e.db")
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
    try:
        result = asyncio.run(_mcp_call(f"http://127.0.0.1:{port}/mcp"))
        assert result["run"]["status"] in {"answered", "inconclusive"}
        assert result["fetched"].get("found") is True
        assert result["fetched"].get("replay_state", {}).get("verified") is True
        return {
            "scenario": "12_mcp_transport",
            "pass": True,
            "run_id": result["run"]["run_id"],
            "replay_verified": True,
            "openai_key_required": False,
            "transport": "streamable-http",
            "path": "/mcp",
        }
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


SCENARIOS: dict[str, Callable[[], dict[str, Any]]] = {
    "01": scenario_01_tam,
    "02": scenario_02_echo,
    "03": scenario_03_freshness,
    "04": scenario_04_entailment,
    "05": scenario_05_counterexample,
    "06": scenario_06_bankruptcy,
    "07": scenario_07_clones,
    "08": scenario_08_germinal,
    "09": scenario_09_memory_laundering,
    "10": scenario_10_evasion_farming,
    "11": scenario_11_tamper,
    "12": scenario_12_mcp,
}


def main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in SCENARIOS:
        raise SystemExit(f"usage: {sys.executable} -m mimicus.validation.worker <{'|'.join(SCENARIOS)}>")
    result = SCENARIOS[sys.argv[1]]()
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
