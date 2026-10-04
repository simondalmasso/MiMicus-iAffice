from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import inspect

from mimicus.events.bus import EventBus
from mimicus.events.ledger import EventLedger
from mimicus.orchestration.progress_ledger import ProgressLedger
from mimicus.orchestration.replay import verify_replay
from mimicus.security import dynamic_code_execution_findings, spec_rejects_source_payload
from mimicus.storage.models import Base
from mimicus.storage.postgres_compat import compile_postgres_schema
from mimicus.storage.repository import Repository, normalized_database_url


def test_event_bus_ledger_tamper_and_snapshot_mismatch() -> None:
    seen: list[dict[str, object]] = []
    bus = EventBus()
    unsubscribe = bus.subscribe("x", seen.append)
    bus.emit("x", {"a": 1})
    unsubscribe()
    bus.emit("x", {"a": 2})
    assert seen == [{"a": 1}]

    ledger = EventLedger("run")
    ledger.append("run_started", {"x": 1})
    ledger.append("run_completed", {"x": 2})
    assert verify_replay(ledger.events, ledger.head)["verified"] is True
    tampered = [event.model_dump() for event in ledger.events]
    tampered[1]["payload"]["x"] = 999
    assert verify_replay(tampered)["verified"] is False
    assert verify_replay(ledger.events, "f" * 64)["verified"] is False


def test_event_ledger_accepts_injected_clock_and_id_source() -> None:
    moment = datetime(2026, 10, 3, 22, 0, tzinfo=UTC)
    times = iter((moment, moment + timedelta(seconds=1)))
    ids = iter(("event-a", "event-b"))
    ledger = EventLedger("run", clock=lambda: next(times), id_source=lambda: next(ids))

    first = ledger.append("a", {"x": 1})
    second = ledger.append("b", {"x": 2})

    assert first.event_id == "event-a"
    assert second.event_id == "event-b"
    assert first.timestamp == moment
    assert second.timestamp == moment + timedelta(seconds=1)
    assert EventLedger.verify(ledger.events)[0] is True


def test_storage_schema_sqlite_and_postgres_compile(tmp_path: Path) -> None:
    url = f"sqlite:///{tmp_path / 'db.sqlite'}"
    repo = Repository(url)
    tables = set(inspect(repo.engine).get_table_names())
    required = {
        "runs",
        "events",
        "task_ledgers",
        "progress_ledgers",
        "agent_fingerprints",
        "agent_domain_calibration",
        "agent_bankruptcy",
        "coalitions",
        "communications",
        "claims",
        "evidence",
        "falsifier_specs",
        "falsifier_versions",
        "falsifier_executions",
        "evasion_events",
        "fossil_claims",
        "mutation_candidates",
        "memory_items",
        "memory_links",
    }
    assert required <= tables
    ddl = compile_postgres_schema()
    assert required <= set(ddl)
    assert "CREATE TABLE runs" in ddl["runs"]
    assert normalized_database_url("postgres://u:p@h/db").startswith("postgresql+psycopg://")
    assert len(Base.metadata.tables) >= 19


def test_security_no_dynamic_execution_and_source_rejection() -> None:
    src = Path(__file__).parents[2] / "src" / "mimicus"
    findings = dynamic_code_execution_findings(src.rglob("*.py"))
    assert findings == []
    from mimicus.falsifiers.builtins import builtin_specs

    assert spec_rejects_source_payload(builtin_specs()["F1"].model_dump())


def test_progress_stagnation() -> None:
    progress = ProgressLedger()
    progress.advance("a", 1.0)
    progress.advance("b", 1.0)
    assert progress.stagnation_count >= 2
    assert progress.replan_reasons == ["two no-progress steps"]
