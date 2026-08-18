from __future__ import annotations

import asyncio
import json
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
    input_usd_per_million_tokens: float | None = None
    output_usd_per_million_tokens: float | None = None
    max_memory_items: int = 8
    max_memory_chars: int = 6000

    @property
    def capabilities(self) -> ProviderCapabilities:
        authoritative = self.input_usd_per_million_tokens is not None and self.output_usd_per_million_tokens is not None
        return ProviderCapabilities(
            supports_structured_output=True,
            supports_async=True,
            supports_tools=True,
            provider_id="openai_agents",
            model_id=self.model,
            version="0.21.1-adapter-v2.1",
            usage_metadata_available=True,
            cancellation="asyncio.wait_for",
            known_zero_cost=False,
            estimated_max_cost_per_call=None,
            pricing_metadata_authoritative=authoritative,
        )

    def build_agent(self, phenotype: str, domain: str) -> Any:
        from agents import Agent

        instructions = (
            f"You are the {phenotype} phenotype for domain {domain}. "
            "Return only a structured Claim. Treat missing evidence as uncertainty. "
            "Verified institutional memory, when supplied in the structured input, is common evidence rather than a peer answer. "
            "Do not coordinate with peer agents during this sealed first pass."
        )
        return Agent(name=f"mimicus-{phenotype}", instructions=instructions, model=self.model, output_type=Claim)

    @staticmethod
    def _usage_numbers(usage: Any) -> tuple[int | None, int | None, int | None]:
        if usage is None:
            return None, None, None
        input_tokens = getattr(usage, "input_tokens", None)
        output_tokens = getattr(usage, "output_tokens", None)
        total_tokens = getattr(usage, "total_tokens", None)
        return (
            int(input_tokens) if isinstance(input_tokens, int) else None,
            int(output_tokens) if isinstance(output_tokens, int) else None,
            int(total_tokens) if isinstance(total_tokens, int) else None,
        )

    def _monetary_cost(self, usage: Any) -> float | None:
        if self.input_usd_per_million_tokens is None or self.output_usd_per_million_tokens is None:
            return None
        input_tokens, output_tokens, _ = self._usage_numbers(usage)
        if input_tokens is None or output_tokens is None:
            return None
        return (input_tokens * self.input_usd_per_million_tokens + output_tokens * self.output_usd_per_million_tokens) / 1_000_000.0

    def _verified_memory_payload(self, memory: tuple[dict[str, Any], ...]) -> list[dict[str, Any]]:
        allowed = {"private_verified", "shared_verified"}
        payload: list[dict[str, Any]] = []
        used_chars = 0
        for item in memory[: self.max_memory_items]:
            if str(item.get("status", "")) not in allowed:
                continue
            content = str(item.get("content", ""))[:1200]
            row = {
                "memory_id": str(item.get("memory_id", "")),
                "claim_hash": str(item.get("claim_hash", "")),
                "content": content,
                "authority": float(item.get("authority", 0.0)),
                "origin_clusters": list(item.get("origin_clusters", []))[:8],
                "verified_clusters": list(item.get("verified_clusters", []))[:8],
            }
            encoded = json.dumps(row, sort_keys=True, separators=(",", ":"))
            if used_chars + len(encoded) > self.max_memory_chars:
                break
            payload.append(row)
            used_chars += len(encoded)
        return payload

    def structured_input(self, request: ProviderRequest) -> tuple[str, int]:
        memory = self._verified_memory_payload(request.verified_memory)
        if not memory:
            return request.task, 0
        body = {
            "task": request.task,
            "verified_institutional_memory": memory,
            "sealed_first_pass": True,
            "peer_outputs_included": False,
        }
        return json.dumps(body, sort_keys=True, separators=(",", ":")), len(memory)

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
        input_tokens, output_tokens, total_tokens = self._usage_numbers(usage)
        metadata: dict[str, object] = {
            "last_agent": getattr(getattr(result, "last_agent", None), "name", None),
            "usage": str(usage) if usage is not None else None,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "timeout_seconds": self.timeout_seconds,
            "monetary_cost_status": "KNOWN" if self._monetary_cost(usage) is not None else "UNKNOWN",
        }
        if self._monetary_cost(usage) is not None:
            metadata["monetary_cost_usd"] = self._monetary_cost(usage)
        return output, metadata

    async def generate_request_async(self, request: ProviderRequest) -> ProviderResponse:
        started = perf_counter()
        model_input, memory_count = self.structured_input(request)
        claim, metadata = await self.generate_async(model_input, request.phenotype, request.domain)
        latency_ms = (perf_counter() - started) * 1000.0
        trace_id = str(metadata.get("last_agent") or "") or None
        usage = dict(metadata)
        usage["verified_memory_items_consumed"] = memory_count
        cost_value = usage.get("monetary_cost_usd")
        cost = float(cost_value) if isinstance(cost_value, (float, int)) else None
        return ProviderResponse(claim=claim, cost=cost, latency_ms=latency_ms, trace_id=trace_id, usage=usage)

    async def challenge_async(self, request: ChallengeRequest) -> ChallengeResponse:
        from agents import Agent, Runner

        agent = Agent(
            name="mimicus-structured-challenger",
            instructions=("Evaluate only the supplied structured claim/evidence/falsifier summary. Return a concise ChallengeResponse. Never expose hidden chain-of-thought."),
            model=self.model,
            output_type=ChallengeResponse,
        )
        result = await asyncio.wait_for(Runner.run(agent, request.model_dump_json(), max_turns=self.max_turns), timeout=self.timeout_seconds)
        output = result.final_output
        response = output if isinstance(output, ChallengeResponse) else ChallengeResponse.model_validate(output)
        call_id = getattr(getattr(result, "last_agent", None), "name", None)
        usage_obj = getattr(getattr(result, "context_wrapper", None), "usage", None)
        input_tokens, output_tokens, total_tokens = self._usage_numbers(usage_obj)
        cost = self._monetary_cost(usage_obj)
        usage = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "monetary_cost_status": "KNOWN" if cost is not None else "UNKNOWN",
        }
        return response.model_copy(update={"provider_call_id": str(call_id) if call_id else response.provider_call_id, "cost": cost, "usage": usage})
