from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from mimicus.claims.models import Claim


@dataclass(frozen=True)
class ProviderRequest:
    task: str
    domain: str
    phenotype: str
    sealed_context_id: str
    fixture: dict[str, Any]


@dataclass(frozen=True)
class ProviderResponse:
    claim: Claim
    cost: float
    latency_ms: float
    trace_id: str | None = None


class Provider(ABC):
    @abstractmethod
    def generate(self, request: ProviderRequest) -> ProviderResponse:
        raise RuntimeError("abstract provider generate invoked")
