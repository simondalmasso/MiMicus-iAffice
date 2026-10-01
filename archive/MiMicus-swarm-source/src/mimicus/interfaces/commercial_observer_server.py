from __future__ import annotations

import ipaddress
import json
from functools import partial
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlsplit

from mimicus.commercial.observer import ActivityBuffer


class ObserverHTTPServer(ThreadingHTTPServer):
    daemon_threads = True


def _is_loopback_host(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


def _handler_factory(buffer: ActivityBuffer, cockpit_dir: Path) -> type[SimpleHTTPRequestHandler]:
    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(cockpit_dir), **kwargs)

        def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _method_not_allowed(self) -> None:
            self.send_response(HTTPStatus.METHOD_NOT_ALLOWED)
            self.send_header("Allow", "GET, HEAD")
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlsplit(self.path)
            if parsed.path == "/api/health":
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "ok": True,
                        "service": "mimicus-observer",
                        "mode": "local-live-observer",
                    },
                )
                return
            if parsed.path == "/api/runtime":
                self._send_json(
                    HTTPStatus.OK,
                    {
                        "mode": "local-live-observer",
                        "decisionAuthority": "MiMicusEngine",
                        "sideEffects": False,
                        "activityEndpoint": "/api/activity",
                    },
                )
                return
            if parsed.path == "/api/activity":
                query = parse_qs(parsed.query)
                raw_since = query.get("since", ["0"])[0]
                try:
                    since = int(raw_since)
                    payload = buffer.since(since)
                except (TypeError, ValueError):
                    self._send_json(
                        HTTPStatus.BAD_REQUEST,
                        {"ok": False, "error": "invalid_cursor"},
                    )
                    return
                self._send_json(HTTPStatus.OK, payload)
                return
            if parsed.path.startswith("/api/"):
                self._send_json(
                    HTTPStatus.NOT_FOUND,
                    {"ok": False, "error": "not_found"},
                )
                return
            super().do_GET()

        def do_POST(self) -> None:  # noqa: N802
            self._method_not_allowed()

        def do_PUT(self) -> None:  # noqa: N802
            self._method_not_allowed()

        def do_PATCH(self) -> None:  # noqa: N802
            self._method_not_allowed()

        def do_DELETE(self) -> None:  # noqa: N802
            self._method_not_allowed()

        def log_message(self, _format: str, *args: Any) -> None:
            return

    return Handler


def create_observer_server(
    *,
    buffer: ActivityBuffer,
    cockpit_dir: str | Path,
    host: str = "127.0.0.1",
    port: int = 8788,
) -> ObserverHTTPServer:
    if not _is_loopback_host(host):
        raise ValueError("observer host must be loopback-only")
    if not (0 <= port <= 65535):
        raise ValueError("observer port must be between 0 and 65535")

    root = Path(cockpit_dir).resolve()
    if not root.is_dir():
        raise ValueError("cockpit_dir must be an existing directory")
    if not (root / "index.html").is_file():
        raise ValueError("cockpit_dir must contain index.html")

    handler = _handler_factory(buffer, root)
    return ObserverHTTPServer((host, port), handler)
