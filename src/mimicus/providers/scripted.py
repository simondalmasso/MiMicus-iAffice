from __future__ import annotations

from uuid import NAMESPACE_URL, uuid5

from mimicus.claims.models import Claim
from mimicus.providers.base import Provider, ProviderRequest, ProviderResponse


class ScriptedProvider(Provider):
    def generate(self, request: ProviderRequest) -> ProviderResponse:
        fixture = request.fixture
        statement = str(fixture.get("claim_statement", request.task))
        probability = float(fixture.get("probability", 0.8))
        claim_type = str(fixture.get("claim_type", "other"))
        allowed = {"numeric", "factual", "causal", "temporal", "comparative", "other"}
        if claim_type not in allowed:
            claim_type = "other"
        claim = Claim(statement=statement, domain=request.domain, probability=probability, claim_type=claim_type)  # type: ignore[arg-type]
        trace_id = str(uuid5(NAMESPACE_URL, f"{request.sealed_context_id}:{request.phenotype}:{request.task}"))
        return ProviderResponse(claim=claim, cost=float(fixture.get("agent_cost", 0.0)), latency_ms=float(fixture.get("agent_latency_ms", 1.0)), trace_id=trace_id)
