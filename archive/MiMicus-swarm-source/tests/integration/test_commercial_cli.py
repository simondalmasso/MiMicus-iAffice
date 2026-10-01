from __future__ import annotations

import json
from pathlib import Path

import pytest

from mimicus.interfaces.cli import main


def _finding(
    prospect_id: str,
    *,
    source_name: str = "Facebook",
    status: str = "prepared",
    score: int = 80,
    channel: str = "messenger",
    contacted_at: str | None = None,
) -> dict[str, object]:
    return {
        "id": prospect_id,
        "title": f"Lead {prospect_id}",
        "buyer": "Buyer",
        "sourceName": source_name,
        "sourceUrl": f"https://example.test/{prospect_id}",
        "directUrl": f"https://example.test/{prospect_id}/contact",
        "publishedAt": "2026-09-30T12:00:00-03:00",
        "verifiedAt": "2026-10-01T12:00:00-03:00",
        "active": True,
        "argentinaEligible": True,
        "workerFee": False,
        "scamRisk": "low",
        "rank": {"score": score},
        "outreach": {
            "status": status,
            "channel": channel,
            "contactedAt": contacted_at,
        },
    }


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_cli_triage_reads_ledger_and_emits_laya_queue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("MIMICUS_DATABASE_URL", "sqlite:///:memory:")
    ledger = tmp_path / "ledger.json"
    policy = tmp_path / "policy.json"
    _write_json(
        ledger,
        {
            "findings": [
                _finding("fb-prepared", score=99),
                _finding("fb-replied", status="replied", score=50),
                _finding(
                    "rd-waiting",
                    source_name="Reddit",
                    status="contacted",
                    channel="post-comment",
                    contacted_at="2026-10-01T14:30:00-03:00",
                ),
            ]
        },
    )
    _write_json(
        policy,
        {
            "version": "operator-v1",
            "max_work_per_lane": 3,
            "follow_up_after_hours": {
                "messenger": 24,
                "post-comment": 24,
            },
        },
    )

    rc = main(
        [
            "triage",
            "--profile",
            "offline",
            "--ledger-file",
            str(ledger),
            "--policy-file",
            str(policy),
            "--as-of",
            "2026-10-01T15:34:00-03:00",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["selected_by_lane"]["facebook"] == ["fb-replied", "fb-prepared"]
    assert payload["selected_by_lane"]["reddit"] == []
    decisions = {row["prospect_id"]: row for row in payload["decisions"]}
    assert decisions["rd-waiting"]["disposition"] == "HOLD"
    assert decisions["rd-waiting"]["stage"] == "contacted_waiting"


def test_cli_triage_requires_explicit_timezone(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MIMICUS_DATABASE_URL", "sqlite:///:memory:")
    ledger = tmp_path / "ledger.json"
    policy = tmp_path / "policy.json"
    _write_json(ledger, {"findings": [_finding("fb")]})
    _write_json(
        policy,
        {
            "version": "operator-v1",
            "max_work_per_lane": 3,
            "follow_up_after_hours": {"messenger": 24},
        },
    )

    with pytest.raises(ValueError, match="timezone"):
        main(
            [
                "triage",
                "--ledger-file",
                str(ledger),
                "--policy-file",
                str(policy),
                "--as-of",
                "2026-10-01T15:34:00",
            ]
        )


def test_cli_triage_trace_jsonl_streams_laya_pipeline(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("MIMICUS_DATABASE_URL", "sqlite:///:memory:")
    ledger = tmp_path / "ledger.json"
    policy = tmp_path / "policy.json"
    _write_json(
        ledger,
        {"findings": [_finding("live-lead", status="replied", score=91)]},
    )
    _write_json(
        policy,
        {
            "version": "operator-live-v1",
            "max_work_per_lane": 3,
            "follow_up_after_hours": {"messenger": 24},
        },
    )

    rc = main(
        [
            "triage",
            "--ledger-file",
            str(ledger),
            "--policy-file",
            str(policy),
            "--as-of",
            "2026-10-01T15:34:00-03:00",
            "--trace-jsonl",
        ]
    )

    assert rc == 0
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [row["event"] for row in rows] == [
        "lead_ingested",
        "laya_reading",
        "decision_emitted",
        "batch_complete",
    ]
    assert rows[0]["prospect_id"] == "live-lead"
    assert rows[1]["policy_version"] == "operator-live-v1"
    assert rows[2]["disposition"] == "WORK_NOW"
    assert rows[2]["stage"] == "replied"
    assert rows[2]["reasons"] == ["stage:replied", "within_lane_wip"]
    assert rows[3]["selected_by_lane"]["facebook"] == ["live-lead"]
    assert rows[3]["batch_hash"]
