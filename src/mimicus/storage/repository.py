from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, insert, select
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.pool import StaticPool

from mimicus.canonical import canonical_json
from mimicus.events.ledger import LedgerEvent
from mimicus.storage.models import Base, EventRow, RunRow


def normalized_database_url(database_url: str) -> str:
    url = make_url(database_url)
    if url.drivername == "postgres":
        url = url.set(drivername="postgresql+psycopg")
    return str(url)


def make_engine(database_url: str) -> Engine:
    url = normalized_database_url(database_url)
    kwargs: dict[str, Any] = {"future": True}
    if url == "sqlite:///:memory:":
        kwargs.update(connect_args={"check_same_thread": False}, poolclass=StaticPool)
    elif url.startswith("sqlite:///"):
        path = Path(url.removeprefix("sqlite:///"))
        if path.parent != Path("."):
            path.parent.mkdir(parents=True, exist_ok=True)
        kwargs.update(connect_args={"check_same_thread": False})
    return create_engine(url, **kwargs)


def create_schema(engine: Engine) -> None:
    Base.metadata.create_all(engine)


class Repository:
    def __init__(self, database_url: str) -> None:
        self.engine = make_engine(database_url)
        create_schema(self.engine)

    def save_run(self, *, run_id: str, task_hash: str, config_hash: str, status: str, ledger_head: str, result: dict[str, Any], events: list[LedgerEvent]) -> None:
        with self.engine.begin() as connection:
            existing = connection.execute(select(RunRow.run_id).where(RunRow.run_id == run_id)).scalar_one_or_none()
            if existing is not None:
                raise ValueError(f"run already exists: {run_id}")
            connection.execute(
                insert(RunRow).values(
                    run_id=run_id,
                    task_hash=task_hash,
                    config_hash=config_hash,
                    status=status,
                    ledger_head=ledger_head,
                    result_json=canonical_json(result),
                    created_at=datetime.now(UTC).isoformat(),
                )
            )
            for event in events:
                connection.execute(
                    insert(EventRow).values(
                        run_id=run_id,
                        sequence=event.sequence,
                        event_type=event.event_type,
                        event_hash=event.event_hash,
                        prev_event_hash=event.prev_event_hash,
                        event_json=event.model_dump_json(),
                    )
                )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self.engine.connect() as connection:
            row = connection.execute(select(RunRow.result_json).where(RunRow.run_id == run_id)).scalar_one_or_none()
        return None if row is None else json.loads(row)

    def get_events(self, run_id: str) -> list[dict[str, Any]]:
        with self.engine.connect() as connection:
            rows = connection.execute(select(EventRow.event_json).where(EventRow.run_id == run_id).order_by(EventRow.sequence)).scalars().all()
        return [json.loads(row) for row in rows]
