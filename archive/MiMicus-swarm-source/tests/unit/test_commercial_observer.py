from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mimicus.commercial.models import LeadDecisionPolicy
from mimicus.commercial.observer import (
    ActivityBuffer,
    CommercialObserver,
    FileLedgerSource,
    UrlLedgerSource,
)
from mimicus.orchestration.engine import MiMicusEngine

AS_OF = datetime(2026, 10, 1, 19, 30, tzinfo=UTC)


def _finding(prospect_id: str, *, status: str = "prepared", score: int = 80) -> dict[str, object]:
    return {
        "id": prospect_id,
        "title": f"Lead {prospect_id}",
        "buyer": "Buyer",
        "sourceName": "Facebook",
        "sourceUrl": f"https://example.test/{prospect_id}",
        "directUrl": f"https://example.test/{prospect_id}/contact",
        "publishedAt": "2026-10-01T10:00:00-03:00",
        "verifiedAt": "2026-10-01T15:00:00-03:00",
        "active": True,
        "argentinaEligible": True,
        "workerFee": False,
        "scamRisk": "low",
        "rank": {"score": score},
        "outreach": {
            "status": status,
            "channel": "messenger",
            "contactedAt": None,
        },
    }


def _policy() -> LeadDecisionPolicy:
    return LeadDecisionPolicy(
        version="observer-test-v1",
        max_work_per_lane=3,
        follow_up_after_hours={"messenger": 24},
    )


def _write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_file_observer_emits_one_cycle_and_dedupes_unchanged_snapshot(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    _write(ledger, {"findings": [_finding("lead-a", status="replied", score=90)]})

    buffer = ActivityBuffer(max_events=32)
    observer = CommercialObserver(
        engine=MiMicusEngine("sqlite:///:memory:"),
        source=FileLedgerSource(ledger),
        policy=_policy(),
        buffer=buffer,
        clock=lambda: AS_OF,
    )

    assert observer.refresh() is True
    first = buffer.since(0)
    assert [row["event"] for row in first["events"]] == [
        "lead_ingested",
        "laya_reading",
        "decision_emitted",
        "batch_complete",
    ]
    assert first["events"][2]["disposition"] == "WORK_NOW"
    assert first["events"][2]["stage"] == "replied"
    assert first["events"][3]["selected_by_lane"]["facebook"] == ["lead-a"]

    assert observer.refresh() is False
    second = buffer.since(first["cursor"])
    assert second == {"cursor": first["cursor"], "events": []}


def test_changed_snapshot_emits_new_cycle_with_monotonic_cursor(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    _write(ledger, {"findings": [_finding("lead-a")]})

    buffer = ActivityBuffer(max_events=64)
    observer = CommercialObserver(
        engine=MiMicusEngine("sqlite:///:memory:"),
        source=FileLedgerSource(ledger),
        policy=_policy(),
        buffer=buffer,
        clock=lambda: AS_OF,
    )

    assert observer.refresh() is True
    cursor = buffer.since(0)["cursor"]

    _write(ledger, {"findings": [_finding("lead-a"), _finding("lead-b", status="replied")]})
    assert observer.refresh() is True

    delta = buffer.since(cursor)
    assert delta["cursor"] > cursor
    assert [row["event"] for row in delta["events"]][-1] == "batch_complete"
    assert any(row.get("prospect_id") == "lead-b" for row in delta["events"])


def test_invalid_json_emits_observer_error_without_destroying_prior_activity(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.json"
    _write(ledger, {"findings": [_finding("lead-a")]})

    buffer = ActivityBuffer(max_events=32)
    observer = CommercialObserver(
        engine=MiMicusEngine("sqlite:///:memory:"),
        source=FileLedgerSource(ledger),
        policy=_policy(),
        buffer=buffer,
        clock=lambda: AS_OF,
    )
    assert observer.refresh() is True
    before = buffer.since(0)

    ledger.write_text("{not-json", encoding="utf-8")
    assert observer.refresh() is False

    after = buffer.since(before["cursor"])
    assert len(after["events"]) == 1
    assert after["events"][0]["event"] == "observer_error"
    assert after["events"][0]["error_type"] == "JSONDecodeError"
    assert buffer.since(0)["events"][0]["event"] == "lead_ingested"


def test_activity_buffer_is_bounded_and_since_uses_global_cursor() -> None:
    buffer = ActivityBuffer(max_events=2)
    buffer.append({"event": "one"})
    buffer.append({"event": "two"})
    buffer.append({"event": "three"})

    snapshot = buffer.since(0)
    assert snapshot["cursor"] == 3
    assert [row["event"] for row in snapshot["events"]] == ["two", "three"]
    assert [row["cursor"] for row in snapshot["events"]] == [2, 3]


def test_url_source_requires_public_https_and_can_use_injected_fetcher() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        UrlLedgerSource("http://example.test/ledger.json")

    with pytest.raises(ValueError, match="credentials"):
        UrlLedgerSource("https://user:pass@example.test/ledger.json")

    source = UrlLedgerSource(
        "https://example.test/ledger.json",
        fetch_bytes=lambda _url, _timeout: json.dumps({"findings": []}).encode(),
    )
    assert source.read() == {"findings": []}
