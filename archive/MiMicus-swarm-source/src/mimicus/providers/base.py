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
    supports_auditions: bool = False
    provider_id: str = "unknown"
    model_id: str = "unknown"
    version: str = "unknown"
    adapter_version: str = "unknown"
    usage_metadata_available: bool = False
    cancellation: str = "asyncio"
    known_zero_cost: bool = False
    estimated_max_cost_per_call: float | None = None
    pricing_metadata_authoritative: bool = False
    tool_manifest_hash: str = "no-tools"
    evidence_acquisition_available: bool = False

    @property
    def runtime_identity(self) -> tuple[str, str, str]:
        return self.provider_id, self.model_id, self.version


@dataclass(frozen=True)
class ProviderRequest:
    task: str
    domain: str
    phenotype: str
    sealed_context_id: str
    fixture: dict[str, Any]
    verified_memory: tuple[dict[str, Any], ...] = ()
    evidence: tuple[dict[str, Any], ...] = ()


@dataclass(frozen=True)
class ProviderResponse:
    claim: Claim
    cost: float | None
    latency_ms: float
    trace_id: str | None = None
    usage: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AuditionRequest:
    fingerprint: str
    domain: str
    phenotype: str
    capability: str
    test_family: str
    category: str
    prompt: str
    sealed_context_id: str


@dataclass(frozen=True)
class ProviderAuditionResponse:
    answer: str
    supported: bool
    cost: float | None
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

    async def audition_async(self, request: AuditionRequest) -> ProviderAuditionResponse:
        """Provider-agnostic canary path. Unsupported adapters stay neutral, never auto-pass."""
        return ProviderAuditionResponse(
            answer="",
            supported=False,
            cost=0.0 if self.capabilities.known_zero_cost else None,
            latency_ms=0.0,
            trace_id=None,
            usage={"provider": self.capabilities.provider_id, "audition_supported": False},
        )

    async def challenge_async(self, request: ChallengeRequest) -> ChallengeResponse:
        return ChallengeResponse(
            disposition="unchanged",
            revised_probability=0.5,
            revised_status=ClaimStatus.PROPOSED,
            rationale_summary="provider has no specialized challenge adapter",
            provider_call_id=None,
            cost=0.0 if self.capabilities.known_zero_cost else None,
            usage={"provider": self.capabilities.provider_id},
        )
