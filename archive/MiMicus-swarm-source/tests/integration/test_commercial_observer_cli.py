from __future__ import annotations

import json
from pathlib import Path

import pytest

from mimicus.commercial.observer import FileLedgerSource, UrlLedgerSource
from mimicus.interfaces import commercial_observer_server
from mimicus.interfaces.cli import main


def _write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _policy(path: Path) -> None:
    _write(
        path,
        {
            "version": "observer-cli-v1",
            "max_work_per_lane": 3,
            "follow_up_after_hours": {
                "messenger": 24,
                "post-comment": 24,
            },
        },
    )


def test_cli_observe_file_source_constructs_zero_cost_local_observer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    ledger = tmp_path / "ledger.json"
    policy = tmp_path / "policy.json"
    cockpit = tmp_path / "public"
    cockpit.mkdir()
    (cockpit / "index.html").write_text("Mimicus", encoding="utf-8")
    _write(ledger, {"findings": []})
    _policy(policy)

    captured: dict[str, object] = {}

    def fake_run(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(commercial_observer_server, "run_commercial_observer", fake_run, raising=False)
    monkeypatch.setenv("MIMICUS_DATABASE_URL", "sqlite:///:memory:")

    rc = main(
        [
            "observe",
            "--ledger-file",
            str(ledger),
            "--policy-file",
            str(policy),
            "--cockpit-dir",
            str(cockpit),
        ]
    )

    assert rc == 0
    assert isinstance(captured["observer"].source, FileLedgerSource)  # type: ignore[attr-defined]
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 8788
    assert captured["poll_seconds"] == 5.0
    startup = json.loads(capsys.readouterr().out)
    assert startup["mode"] == "local-live-observer"
    assert startup["sideEffects"] is False
    assert startup["url"] == "http://127.0.0.1:8788/"


def test_cli_observe_url_source_uses_https_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy = tmp_path / "policy.json"
    cockpit = tmp_path / "public"
    cockpit.mkdir()
    (cockpit / "index.html").write_text("Mimicus", encoding="utf-8")
    _policy(policy)

    captured: dict[str, object] = {}

    def fake_run(**kwargs: object) -> None:
        captured.update(kwargs)

    monkeypatch.setattr(commercial_observer_server, "run_commercial_observer", fake_run, raising=False)
    monkeypatch.setenv("MIMICUS_DATABASE_URL", "sqlite:///:memory:")

    assert (
        main(
            [
                "observe",
                "--ledger-url",
                "https://example.test/prospects.json",
                "--policy-file",
                str(policy),
                "--cockpit-dir",
                str(cockpit),
            ]
        )
        == 0
    )
    assert isinstance(captured["observer"].source, UrlLedgerSource)  # type: ignore[attr-defined]


def test_cli_observe_requires_exactly_one_ledger_source(tmp_path: Path) -> None:
    policy = tmp_path / "policy.json"
    cockpit = tmp_path / "public"
    cockpit.mkdir()
    (cockpit / "index.html").write_text("Mimicus", encoding="utf-8")
    _policy(policy)

    with pytest.raises(SystemExit):
        main(
            [
                "observe",
                "--policy-file",
                str(policy),
                "--cockpit-dir",
                str(cockpit),
            ]
        )

    with pytest.raises(SystemExit):
        main(
            [
                "observe",
                "--ledger-file",
                str(tmp_path / "a.json"),
                "--ledger-url",
                "https://example.test/b.json",
                "--policy-file",
                str(policy),
                "--cockpit-dir",
                str(cockpit),
            ]
        )


def test_cli_observe_rejects_insecure_remote_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy = tmp_path / "policy.json"
    cockpit = tmp_path / "public"
    cockpit.mkdir()
    (cockpit / "index.html").write_text("Mimicus", encoding="utf-8")
    _policy(policy)
    monkeypatch.setenv("MIMICUS_DATABASE_URL", "sqlite:///:memory:")

    with pytest.raises(ValueError, match="HTTPS"):
        main(
            [
                "observe",
                "--ledger-url",
                "http://example.test/prospects.json",
                "--policy-file",
                str(policy),
                "--cockpit-dir",
                str(cockpit),
            ]
        )
