from __future__ import annotations

import ipaddress
import json
import socket
from collections import deque
from collections.abc import Callable, Mapping
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from threading import Lock
from typing import Any, Protocol
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from mimicus.canonical import sha256_obj
from mimicus.commercial.models import CommercialTraceEvent, LeadDecisionPolicy
from mimicus.orchestration.engine import MiMicusEngine

_MAX_REMOTE_BYTES = 2 * 1024 * 1024


class LedgerSource(Protocol):
    def read(self) -> dict[str, Any]: ...


def _decode_json_object(raw: str, *, label: str) -> dict[str, Any]:
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain a JSON object")
    return payload


class FileLedgerSource:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def read(self) -> dict[str, Any]:
        return _decode_json_object(self.path.read_text(encoding="utf-8"), label="ledger file")


FetchBytes = Callable[[str, float], bytes]
ResolveHost = Callable[[str], list[str]]


def _resolve_host(host: str) -> list[str]:
    try:
        rows = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ValueError("ledger URL hostname could not be resolved") from exc
    return sorted({str(row[4][0]) for row in rows})


def _validate_public_https_url(url: str, resolve_host: ResolveHost) -> None:
    parsed = urlsplit(url)
    if parsed.scheme.lower() != "https":
        raise ValueError("ledger URL must use HTTPS")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("ledger URL must not contain credentials")
    if not parsed.hostname:
        raise ValueError("ledger URL must include a hostname")

    addresses = resolve_host(parsed.hostname)
    if not addresses:
        raise ValueError("ledger URL hostname must resolve to a public IP address")

    for raw_address in addresses:
        address = raw_address.split("%", 1)[0]
        try:
            ip = ipaddress.ip_address(address)
        except ValueError as exc:
            raise ValueError("ledger URL hostname returned an invalid IP address") from exc
        if not ip.is_global or ip.is_multicast or ip.is_unspecified or ip.is_reserved:
            raise ValueError("ledger URL hostname must resolve only to public IP addresses")


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(
        self,
        req: Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> Request | None:
        del req, fp, code, msg, headers, newurl
        raise ValueError("remote ledger redirects are not allowed")


def _fetch_https_bytes(url: str, timeout: float, *, resolve_host: ResolveHost) -> bytes:
    _validate_public_https_url(url, resolve_host)
    request = Request(url, headers={"User-Agent": "Mimicus-Live-Observer/1"})
    opener = build_opener(_RejectRedirects())
    with opener.open(request, timeout=timeout) as response:
        body = response.read(_MAX_REMOTE_BYTES + 1)
    if len(body) > _MAX_REMOTE_BYTES:
        raise ValueError("remote ledger exceeds maximum supported size")
    return body


class UrlLedgerSource:
    def __init__(
        self,
        url: str,
        *,
        timeout: float = 5.0,
        fetch_bytes: FetchBytes | None = None,
        resolve_host: ResolveHost | None = None,
    ) -> None:
        resolver = resolve_host or _resolve_host
        _validate_public_https_url(url, resolver)
        if timeout <= 0:
            raise ValueError("ledger URL timeout must be positive")
        self.url = url
        self.timeout = timeout
        self._resolve_host = resolver
        self._fetch_bytes = fetch_bytes

    def read(self) -> dict[str, Any]:
        if self._fetch_bytes is None:
            raw = _fetch_https_bytes(self.url, self.timeout, resolve_host=self._resolve_host)
        else:
            raw = self._fetch_bytes(self.url, self.timeout)
        return _decode_json_object(raw.decode("utf-8"), label="remote ledger")


class ActivityBuffer:
    def __init__(self, *, max_events: int = 512) -> None:
        if max_events < 1:
            raise ValueError("max_events must be positive")
        self._events: deque[dict[str, Any]] = deque(maxlen=max_events)
        self._cursor = 0
        self._lock = Lock()

    def append(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        with self._lock:
            self._cursor += 1
            row = deepcopy(dict(payload))
            row["cursor"] = self._cursor
            self._events.append(row)
            return deepcopy(row)

    def since(self, cursor: int) -> dict[str, Any]:
        if cursor < 0:
            raise ValueError("cursor must be non-negative")
        with self._lock:
            events = [deepcopy(row) for row in self._events if int(row["cursor"]) > cursor]
            return {"cursor": self._cursor, "events": events}


class CommercialObserver:
    def __init__(
        self,
        *,
        engine: MiMicusEngine,
        source: LedgerSource,
        policy: LeadDecisionPolicy,
        buffer: ActivityBuffer,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.engine = engine
        self.source = source
        self.policy = policy
        self.buffer = buffer
        self.clock = clock or (lambda: datetime.now(UTC))
        self._last_payload_hash: str | None = None
        self._last_error_signature: str | None = None

    def _now(self) -> datetime:
        value = self.clock()
        if value.utcoffset() is None:
            raise ValueError("observer clock must return a timezone-aware datetime")
        return value

    def _emit_error(self, exc: Exception) -> None:
        signature = f"{type(exc).__name__}:{exc}"
        if signature == self._last_error_signature:
            return
        self._last_error_signature = signature
        try:
            observed_at = self._now().isoformat()
        except Exception:
            observed_at = datetime.now(UTC).isoformat()
        self.buffer.append(
            {
                "event": "observer_error",
                "observed_at": observed_at,
                "error_type": type(exc).__name__,
                "message": str(exc),
            }
        )

    def refresh(self) -> bool:
        try:
            payload = self.source.read()
            payload_hash = sha256_obj(payload)
            if payload_hash == self._last_payload_hash:
                return False

            as_of = self._now()

            def publish_trace(event: CommercialTraceEvent) -> None:
                self.buffer.append(event.model_dump(mode="json"))

            batch = self.engine.triage_prospects(
                payload,
                policy=self.policy,
                as_of=as_of,
                trace_sink=publish_trace,
            )

            batch_payload = batch.model_dump(mode="json")
            self.buffer.append(
                {
                    "event": "batch_complete",
                    "as_of": as_of.isoformat(),
                    "batch_hash": batch.batch_hash,
                    "selected_by_lane": batch_payload["selected_by_lane"],
                    "held_ids": batch_payload["held_ids"],
                    "rejected_ids": batch_payload["rejected_ids"],
                    "repair_data_ids": batch_payload["repair_data_ids"],
                }
            )
            self._last_payload_hash = payload_hash
            self._last_error_signature = None
            return True
        except Exception as exc:
            self._emit_error(exc)
            return False
