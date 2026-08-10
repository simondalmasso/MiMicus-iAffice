from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Any, Callable


@dataclass
class BenchmarkResult:
    requests: int
    successes: int
    errors: int
    error_rate: float
    p50_ms: float | None
    p90_ms: float | None
    p99_ms: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def benchmark(call: Callable[[], Any], requests: int = 10) -> BenchmarkResult:
    if requests <= 0:
        raise ValueError("requests must be positive")
    samples: list[float] = []
    errors = 0
    for _ in range(requests):
        try:
            result = call()
            latency = getattr(result, "latency_ms", None)
            if latency is None:
                raise ValueError("benchmark call did not return latency_ms")
            samples.append(float(latency))
        except Exception:
            errors += 1
    return BenchmarkResult(
        requests=requests,
        successes=len(samples),
        errors=errors,
        error_rate=errors / requests,
        p50_ms=_percentile(samples, 0.50),
        p90_ms=_percentile(samples, 0.90),
        p99_ms=_percentile(samples, 0.99),
    )


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    pos = (len(xs) - 1) * q
    lo = math.floor(pos); hi = math.ceil(pos)
    if lo == hi:
        return xs[lo]
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)
