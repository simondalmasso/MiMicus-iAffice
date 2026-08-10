from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable

from .safety import assert_safe_url


class ReadError(RuntimeError):
    pass


@dataclass
class HttpResult:
    data: dict[str, Any]
    latency_ms: float
    status: int
    headers: dict[str, str]


Transport = Callable[[str, float], HttpResult]


def urllib_transport(url: str, timeout: float) -> HttpResult:
    assert_safe_url(url)
    req = urllib.request.Request(url, method="GET", headers={"User-Agent": "Allora-Edge/0.1 read-only"})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read()
            status = response.status
            headers = dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        raise ReadError(f"HTTP {exc.code} for {url}") from exc
    except urllib.error.URLError as exc:
        raise ReadError(f"network error for {url}: {exc.reason}") from exc
    elapsed = (time.perf_counter() - started) * 1000
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ReadError(f"malformed JSON from {url}") from exc
    if not isinstance(data, dict):
        raise ReadError(f"unexpected non-object JSON from {url}")
    return HttpResult(data=data, latency_ms=elapsed, status=status, headers=headers)


class ReadOnlyHttpClient:
    def __init__(self, transport: Transport = urllib_transport, timeout: float = 12.0, retries: int = 2):
        self.transport = transport
        self.timeout = timeout
        self.retries = retries

    def get(self, url: str) -> HttpResult:
        assert_safe_url(url)
        last: Exception | None = None
        for attempt in range(self.retries + 1):
            try:
                return self.transport(url, self.timeout)
            except ReadError as exc:
                last = exc
                if "HTTP 429" not in str(exc) and "network error" not in str(exc):
                    raise
                if attempt < self.retries:
                    time.sleep(min(0.25 * (2**attempt), 1.0))
        raise ReadError(str(last) if last else "read failed")
