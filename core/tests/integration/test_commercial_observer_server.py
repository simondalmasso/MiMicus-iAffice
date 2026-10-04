from __future__ import annotations

import json
from pathlib import Path
from threading import Thread
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from mimicus.commercial.observer import ActivityBuffer
from mimicus.interfaces.commercial_observer_server import create_observer_server


def _request_json(url: str) -> dict[str, object]:
    with urlopen(url, timeout=2) as response:
        assert response.headers["Cache-Control"] == "no-store"
        return json.loads(response.read().decode("utf-8"))


def test_observer_server_exposes_read_only_activity_and_static_cockpit(tmp_path: Path) -> None:
    cockpit = tmp_path / "public"
    cockpit.mkdir()
    (cockpit / "index.html").write_text("<!doctype html><title>Mimicus Live</title>", encoding="utf-8")
    (cockpit / "app.js").write_text("console.log('live');", encoding="utf-8")

    buffer = ActivityBuffer(max_events=16)
    buffer.append({"event": "lead_ingested", "prospect_id": "lead-a"})

    server = create_observer_server(
        buffer=buffer,
        cockpit_dir=cockpit,
        host="127.0.0.1",
        port=0,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address[:2]
        base = f"http://{host}:{port}"

        health = _request_json(f"{base}/api/health")
        assert health == {
            "ok": True,
            "service": "mimicus-observer",
            "mode": "local-live-observer",
        }

        runtime = _request_json(f"{base}/api/runtime")
        assert runtime["mode"] == "local-live-observer"
        assert runtime["decisionAuthority"] == "MiMicusEngine"
        assert runtime["sideEffects"] is False

        activity = _request_json(f"{base}/api/activity?since=0")
        assert activity["cursor"] == 1
        assert activity["events"][0]["prospect_id"] == "lead-a"

        with urlopen(f"{base}/", timeout=2) as response:
            assert b"Mimicus Live" in response.read()

        with pytest.raises(HTTPError) as exc_info:
            urlopen(Request(f"{base}/api/activity", data=b"{}", method="POST"), timeout=2)
        assert exc_info.value.code == 405
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_observer_server_rejects_non_loopback_bind(tmp_path: Path) -> None:
    cockpit = tmp_path / "public"
    cockpit.mkdir()
    (cockpit / "index.html").write_text("ok", encoding="utf-8")

    with pytest.raises(ValueError, match="loopback"):
        create_observer_server(
            buffer=ActivityBuffer(),
            cockpit_dir=cockpit,
            host="0.0.0.0",
            port=8788,
        )


def test_activity_api_rejects_invalid_cursor(tmp_path: Path) -> None:
    cockpit = tmp_path / "public"
    cockpit.mkdir()
    (cockpit / "index.html").write_text("ok", encoding="utf-8")
    server = create_observer_server(
        buffer=ActivityBuffer(),
        cockpit_dir=cockpit,
        host="127.0.0.1",
        port=0,
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address[:2]
        with pytest.raises(HTTPError) as exc_info:
            urlopen(f"http://{host}:{port}/api/activity?since=-1", timeout=2)
        assert exc_info.value.code == 400
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
