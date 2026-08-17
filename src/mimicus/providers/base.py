from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from mimicus.claims.models import Claim
from mimicus.orchestration.communication import ChallengeRequest, ChallengeResponse
from mimicus.types import ClaimStatus


@dataclass(frozen=True)
class ProviderCapabilities:
    supports_structured_output: bool = True
    supports_async: bool = True
    supports_tools: bool = False
    provider_id: str = "unknown"
    model_id: str = "unknown"
    version: str = "unknown"
    usage_metadata_available: bool = False
    cancellation: str = "asyncio"


@dataclass(frozen=True)
class ProviderRequest:
    task: str
    domain: str
    phenotype: str
    sealed_context_id: str
    fixture: dict[str, Any]
    verified_memory: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class ProviderResponse:
    claim: Claim
    cost: float
    latency_ms: float
    trace_id: str | None = None
    usage: dict[str, Any] = field(default_factory=dict)


class Provider(ABC):
    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(provider_id=type(self).__name__)

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        return asyncio.run(self.generate_request_async(request))

    @abstractmethod
    async def generate_request_async(self, request: ProviderRequest) -> ProviderResponse:
        raise RuntimeError("abstract async provider generate invoked")

    async def challenge_async(self, request: ChallengeRequest) -> ChallengeResponse:
        return ChallengeResponse(
            disposition="unchanged",
            revised_probability=0.5,
            revised_status=ClaimStatus.PROPOSED,
            rationale_summary="provider has no specialized challenge adapter",
            provider_call_id=None,
        )
