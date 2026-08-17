from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from mimicus.claims.models import Claim
from mimicus.orchestration.communication import ChallengeRequest, ChallengeResponse
from mimicus.providers.base import Provider, ProviderCapabilities, ProviderRequest, ProviderResponse


@dataclass
class OpenAIAgentsProvider(Provider):
    model: str
    max_turns: int = 3
    timeout_seconds: float = 30.0

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            supports_structured_output=True,
            supports_async=True,
            supports_tools=True,
            provider_id="openai_agents",
            model_id=self.model,
            version="0.21.1-adapter-v2",
            usage_metadata_available=True,
            cancellation="asyncio.wait_for",
        )

    def build_agent(self, phenotype: str, domain: str) -> Any:
        from agents import Agent

        instructions = (
            f"You are the {phenotype} phenotype for domain {domain}. "
            "Return only a structured Claim. Treat missing evidence as uncertainty. "
            "Do not coordinate with peer agents during this sealed first pass."
        )
        return Agent(name=f"mimicus-{phenotype}", instructions=instructions, model=self.model, output_type=Claim)

    async def generate_async(self, task: str, phenotype: str, domain: str) -> tuple[Claim, dict[str, object]]:
        from agents import Runner

        agent = self.build_agent(phenotype, domain)

        async def invoke() -> Any:
            return await Runner.run(agent, task, max_turns=self.max_turns)

        result = await asyncio.wait_for(invoke(), timeout=self.timeout_seconds)
        output = result.final_output
        if not isinstance(output, Claim):
            output = Claim.model_validate(output)
        usage = getattr(getattr(result, "context_wrapper", None), "usage", None)
        metadata = {
            "last_agent": getattr(getattr(result, "last_agent", None), "name", None),
            "usage": str(usage) if usage is not None else None,
            "timeout_seconds": self.timeout_seconds,
        }
        return output, metadata

    async def generate_request_async(self, request: ProviderRequest) -> ProviderResponse:
        started = perf_counter()
        claim, metadata = await self.generate_async(request.task, request.phenotype, request.domain)
        latency_ms = (perf_counter() - started) * 1000.0
        trace_id = str(metadata.get("last_agent") or "") or None
        return ProviderResponse(claim=claim, cost=0.0, latency_ms=latency_ms, trace_id=trace_id, usage=metadata)

    async def challenge_async(self, request: ChallengeRequest) -> ChallengeResponse:
        from agents import Agent, Runner

        agent = Agent(
            name="mimicus-structured-challenger",
            instructions=(
                "Evaluate only the supplied structured claim/evidence/falsifier summary. "
                "Return a concise ChallengeResponse. Never expose hidden chain-of-thought."
            ),
            model=self.model,
            output_type=ChallengeResponse,
        )
        result = await asyncio.wait_for(Runner.run(agent, request.model_dump_json(), max_turns=self.max_turns), timeout=self.timeout_seconds)
        output = result.final_output
        response = output if isinstance(output, ChallengeResponse) else ChallengeResponse.model_validate(output)
        call_id = getattr(getattr(result, "last_agent", None), "name", None)
        return response.model_copy(update={"provider_call_id": str(call_id) if call_id else response.provider_call_id})
