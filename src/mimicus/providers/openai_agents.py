from __future__ import annotations

import asyncio
from dataclasses import dataclass
from time import perf_counter
from typing import Any

from mimicus.claims.models import Claim
from mimicus.providers.base import Provider, ProviderRequest, ProviderResponse


@dataclass
class OpenAIAgentsProvider(Provider):
    model: str
    max_turns: int = 3
    timeout_seconds: float = 30.0


    def generate(self, request: ProviderRequest) -> ProviderResponse:
        started = perf_counter()
        claim, metadata = asyncio.run(self.generate_async(request.task, request.phenotype, request.domain))
        latency_ms = (perf_counter() - started) * 1000.0
        trace_id = str(metadata.get("last_agent") or "") or None
        return ProviderResponse(claim=claim, cost=0.0, latency_ms=latency_ms, trace_id=trace_id)

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
