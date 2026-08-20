from __future__ import annotations

import asyncio
from time import perf_counter
from typing import Any, Literal
from uuid import NAMESPACE_URL, uuid5

from mimicus.claims.models import (
    Claim,
    CounterexampleAssertion,
    EntailmentAssertion,
    NumericAssertion,
    SourceIndependenceAssertion,
    TemporalAssertion,
)
from mimicus.orchestration.communication import ChallengeRequest, ChallengeResponse
from mimicus.providers.base import AuditionRequest, Provider, ProviderAuditionResponse, ProviderCapabilities, ProviderRequest, ProviderResponse
from mimicus.types import ClaimStatus

_DEFAULT_AUDITION_COMPETENCE: dict[str, frozenset[str]] = {
    "numeric-1": frozenset({"numeric", "synthesize"}),
    "source-1": frozenset({"source", "freshness", "independence"}),
    "counterexample-1": frozenset({"counterexample", "source"}),
    "critic-1": frozenset({"critic", "entailment"}),
    "synth-1": frozenset({"synthesize"}),
}


class ScriptedProvider(Provider):
    def __init__(
        self,
        provider_id: str = "scripted",
        model_id: str = "fixture-v2",
        *,
        default_cost: float = 0.0,
        challenge_cost: float = 0.0,
        audition_competence: dict[str, frozenset[str]] | None = None,
    ) -> None:
        self.provider_id = provider_id
        self.model_id = model_id
        self.default_cost = max(0.0, float(default_cost))
        self.challenge_cost = max(0.0, float(challenge_cost))
        self.audition_competence = dict(audition_competence or _DEFAULT_AUDITION_COMPETENCE)
        self.generate_calls = 0
        self.challenge_calls = 0
        self.audition_calls = 0
        self.call_ids: list[str] = []

    @property
    def capabilities(self) -> ProviderCapabilities:
        known_zero = self.default_cost == 0.0 and self.challenge_cost == 0.0
        return ProviderCapabilities(
            supports_structured_output=True,
            supports_async=True,
            supports_tools=False,
            supports_auditions=True,
            provider_id=self.provider_id,
            model_id=self.model_id,
            version="fixture-v2",
            adapter_version="scripted-adapter-v2.3-order008",
            usage_metadata_available=True,
            cancellation="asyncio-native",
            known_zero_cost=known_zero,
            estimated_max_cost_per_call=max(self.default_cost, self.challenge_cost),
            pricing_metadata_authoritative=True,
        )

    @property
    def total_calls(self) -> int:
        return self.generate_calls + self.challenge_calls + self.audition_calls

    @staticmethod
    def _value_for(mapping: Any, phenotype: str, default: Any) -> Any:
        return mapping.get(phenotype, default) if isinstance(mapping, dict) else default

    @staticmethod
    def _facts(request: ProviderRequest) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        conflicts: set[str] = set()
        for row in request.evidence:
            raw = row.get("extracted_facts", {})
            if not isinstance(raw, dict):
                continue
            for key, value in raw.items():
                if key in conflicts:
                    continue
                if key in merged and merged[key] != value:
                    merged.pop(key, None)
                    conflicts.add(key)
                else:
                    merged[key] = value
        return merged

    @staticmethod
    def _typed_assertion(claim_type: str, facts: dict[str, Any], fixture: dict[str, Any], phenotype: str) -> Any | None:
        asserted_values = fixture.get("agent_asserted_values")
        asserted_value = ScriptedProvider._value_for(asserted_values, phenotype, fixture.get("asserted_value"))
        if claim_type == "numeric" and asserted_value is None:
            raw_asserted = facts.get("asserted_values")
            asserted_value = ScriptedProvider._value_for(raw_asserted, phenotype, facts.get("claimed"))
        if claim_type == "numeric" and asserted_value is not None:
            try:
                return NumericAssertion(asserted_value=float(asserted_value))
            except (TypeError, ValueError):
                return None
        if claim_type == "temporal" and facts.get("as_of") is not None:
            try:
                return TemporalAssertion(as_of=facts["as_of"], max_age_days=facts.get("max_age_days"))
            except (TypeError, ValueError):
                return None
        if facts.get("claim_figure") is not None and isinstance(facts.get("evidence_spans"), list):
            return EntailmentAssertion(claim_figure=str(facts["claim_figure"]))
        if isinstance(facts.get("absence_key"), str) and isinstance(facts.get("registry"), dict):
            return CounterexampleAssertion(absence_key=str(facts["absence_key"]))
        if isinstance(facts.get("clusters"), list) and len(facts["clusters"]) >= 2:
            return SourceIndependenceAssertion(required_independent=int(facts.get("required_independent", 2)))
        return None

    async def audition_async(self, request: AuditionRequest) -> ProviderAuditionResponse:
        self.audition_calls += 1
        await asyncio.sleep(0)
        competent = request.capability in self.audition_competence.get(request.phenotype, frozenset())
        prompt = request.prompt.lower()
        if competent and "annualization" in prompt:
            answer = "Use the supplied parameter exactly."
        elif competent and "as-of" in prompt:
            answer = "Choose the fresh evidence valid at the as-of date."
        elif competent and "topical decoy" in prompt:
            answer = "Choose relevant evidence and reject the decoy."
        elif competent and "city-level" in prompt:
            answer = "Require granular city-level support."
        elif competent and "missing prerequisite" in prompt:
            answer = "The prerequisite is missing."
        elif competent and "cannot perform" in prompt:
            answer = "Reject the unsupported tool claim."
        else:
            answer = "I cannot establish the requested canary condition."
        call_id = str(uuid5(NAMESPACE_URL, f"audition:{request.sealed_context_id}:{request.phenotype}:{request.capability}:{self.audition_calls}"))
        self.call_ids.append(call_id)
        return ProviderAuditionResponse(
            answer=answer,
            supported=True,
            cost=0.0,
            latency_ms=0.0,
            trace_id=call_id,
            usage={"simulated": True, "audition": True, "calls": 1, "monetary_cost_status": "KNOWN", "monetary_cost_usd": 0.0},
        )

    async def generate_request_async(self, request: ProviderRequest) -> ProviderResponse:
        fixture = request.fixture
        facts = self._facts(request)
        delay_ms = float(self._value_for(fixture.get("agent_delay_ms"), request.phenotype, fixture.get("default_agent_delay_ms", 0.0)))
        started = perf_counter()
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000.0)
        statement = str(self._value_for(fixture.get("agent_statements"), request.phenotype, fixture.get("claim_statement", request.task)))
        probability = float(self._value_for(fixture.get("agent_probabilities"), request.phenotype, fixture.get("probability", 0.8)))
        explicit_type = fixture.get("claim_type")
        if explicit_type is None:
            if all(facts.get(key) is not None for key in ("price", "users", "claimed")):
                claim_type_value = "numeric"
            elif facts.get("evidence_date") is not None and facts.get("as_of") is not None:
                claim_type_value = "temporal"
            elif any(key in facts for key in ("claim_figure", "absence_key", "clusters")):
                claim_type_value = "factual"
            else:
                claim_type_value = "other"
        else:
            claim_type_value = str(explicit_type)
        allowed: set[str] = {"numeric", "factual", "causal", "temporal", "comparative", "other"}
        if claim_type_value not in allowed:
            claim_type_value = "other"
        claim_type: Literal["numeric", "factual", "causal", "temporal", "comparative", "other"] = claim_type_value  # type: ignore[assignment]
        assertion = self._typed_assertion(claim_type, facts, fixture, request.phenotype)
        evidence_refs = [str(row["evidence_hash"]) for row in request.evidence if isinstance(row, dict) and isinstance(row.get("evidence_hash"), str)]
        claim = Claim(
            statement=statement,
            domain=request.domain,
            probability=probability,
            claim_type=claim_type,
            assertion=assertion,
            evidence_refs=list(dict.fromkeys(evidence_refs)),
        )
        self.generate_calls += 1
        trace_id = str(uuid5(NAMESPACE_URL, f"{request.sealed_context_id}:{request.phenotype}:{request.task}:generate:{self.generate_calls}"))
        self.call_ids.append(trace_id)
        latency_ms = max(delay_ms, (perf_counter() - started) * 1000.0)
        cost = float(fixture.get("agent_cost", self.default_cost))
        return ProviderResponse(
            claim=claim,
            cost=cost,
            latency_ms=latency_ms,
            trace_id=trace_id,
            usage={
                "simulated": True,
                "calls": 1,
                "verified_memory_items": len(request.verified_memory),
                "typed_assertion": assertion is not None,
                "monetary_cost_status": "KNOWN",
                "monetary_cost_usd": cost,
            },
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
            cost=self.challenge_cost,
            usage={"simulated": True, "calls": 1, "monetary_cost_status": "KNOWN", "monetary_cost_usd": self.challenge_cost},
        )
