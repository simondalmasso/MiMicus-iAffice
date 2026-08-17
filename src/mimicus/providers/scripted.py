from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any, Literal
from uuid import NAMESPACE_URL, uuid5

from mimicus.claims.models import Claim
from mimicus.orchestration.communication import ChallengeRequest, ChallengeResponse
from mimicus.providers.base import Provider, ProviderCapabilities, ProviderRequest, ProviderResponse
from mimicus.types import ClaimStatus


class ScriptedProvider(Provider):
    def __init__(self, provider_id: str = "scripted", model_id: str = "fixture-v2") -> None:
        self.provider_id = provider_id
        self.model_id = model_id
        self.generate_calls = 0
        self.challenge_calls = 0
        self.call_ids: list[str] = []

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_structured_output=True,
            supports_async=True,
            supports_tools=False,
            provider_id=self.provider_id,
            model_id=self.model_id,
            version="2",
            usage_metadata_available=True,
            cancellation="asyncio-native",
        )

    @property
    def total_calls(self) -> int:
        return self.generate_calls + self.challenge_calls

    @staticmethod
    def _value_for(mapping: Any, phenotype: str, default: Any) -> Any:
        return mapping.get(phenotype, default) if isinstance(mapping, dict) else default

    async def generate_request_async(self, request: ProviderRequest) -> ProviderResponse:
        fixture = request.fixture
        delay_ms = float(self._value_for(fixture.get("agent_delay_ms"), request.phenotype, fixture.get("default_agent_delay_ms", 0.0)))
        started = perf_counter()
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000.0)
        statement = str(self._value_for(fixture.get("agent_statements"), request.phenotype, fixture.get("claim_statement", request.task)))
        probability = float(self._value_for(fixture.get("agent_probabilities"), request.phenotype, fixture.get("probability", 0.8)))
        claim_type_value = str(fixture.get("claim_type", "other"))
        allowed: set[str] = {"numeric", "factual", "causal", "temporal", "comparative", "other"}
        if claim_type_value not in allowed:
            claim_type_value = "other"
        claim_type: Literal["numeric", "factual", "causal", "temporal", "comparative", "other"] = claim_type_value  # type: ignore[assignment]
        claim = Claim(statement=statement, domain=request.domain, probability=probability, claim_type=claim_type)
        self.generate_calls += 1
        trace_id = str(uuid5(NAMESPACE_URL, f"{request.sealed_context_id}:{request.phenotype}:{request.task}:generate:{self.generate_calls}"))
        self.call_ids.append(trace_id)
        latency_ms = max(delay_ms, (perf_counter() - started) * 1000.0)
        return ProviderResponse(
            claim=claim,
            cost=float(fixture.get("agent_cost", 0.0)),
            latency_ms=latency_ms,
            trace_id=trace_id,
            usage={"simulated": True, "calls": 1, "verified_memory_items": len(request.verified_memory)},
        )

    async def challenge_async(self, request: ChallengeRequest) -> ChallengeResponse:
        self.challenge_calls += 1
        call_id = str(uuid5(NAMESPACE_URL, f"challenge:{request.hash}:{self.challenge_calls}"))
        self.call_ids.append(call_id)
        await asyncio.sleep(0)
        probability = max(0.05, min(0.95, 0.50 + 0.08 * min(request.round, 3)))
        return ChallengeResponse(
            disposition="partial",
            revised_probability=probability,
            revised_status=ClaimStatus.PROPOSED,
            new_evidence_refs=list(request.evidence_refs),
            rationale_summary="structured challenge considered; probability revised without hidden reasoning exchange",
            provider_call_id=call_id,
        )
