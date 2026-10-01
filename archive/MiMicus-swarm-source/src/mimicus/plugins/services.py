from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Protocol

from mimicus.agents.identity import AgentIdentity, exact_fingerprint, make_identity
from mimicus.canonical import sha256_obj, sha256_text
from mimicus.coalition.selector import AgentCandidate, select_coalition
from mimicus.coalition.threat_profile import ThreatProfile
from mimicus.commercial.models import LeadCandidate, LeadDecisionBatch, LeadDecisionPolicy
from mimicus.falsifiers.builtins import builtin_specs
from mimicus.falsifiers.primitives import execute_primitive
from mimicus.falsifiers.spec import FalsifierExecution, FalsifierSpec
from mimicus.memory.gates import cross_agent_gate, retrieval_gate
from mimicus.memory.models import MemoryItem
from mimicus.orchestration.communication import CommunicationCandidate, select_sparse_edges
from mimicus.providers.base import Provider, ProviderCapabilities
from mimicus.storage.repository import Repository


class StorageService(Protocol):
    repository: Repository


class AgentFactoryService(Protocol):
    def candidates(self) -> list[AgentCandidate]: ...
    def identity_for(self, candidate: AgentCandidate) -> AgentIdentity: ...


class FalsifierService(Protocol):
    def specs(self, domain: str) -> dict[str, FalsifierSpec]: ...
    def run(self, spec: FalsifierSpec, context: dict[str, object]) -> FalsifierExecution: ...


class MemoryService(Protocol):
    def retrieve(self, domain: str) -> list[MemoryItem]: ...
    def injectable(self, item: MemoryItem, target_fingerprint: str, domain: str) -> bool: ...


class LeadDecisionService(Protocol):
    def decide(
        self,
        candidates: list[LeadCandidate],
        policy: LeadDecisionPolicy,
        *,
        as_of: datetime,
    ) -> LeadDecisionBatch: ...


@dataclass
class RepositoryStorage:
    repository: Repository


@dataclass
class BuiltinAgentFactory:
    provider_capabilities: ProviderCapabilities = field(
        default_factory=lambda: ProviderCapabilities(provider_id="scripted", model_id="fixture-v2", version="2", known_zero_cost=True)
    )
    policy_version: str = "mimicus-v0.2.2-policy"

    _PHENOTYPES = (
        ("numeric-1", frozenset({"numeric", "synthesize"}), "numeric-verifier-v2.1"),
        ("source-1", frozenset({"source", "freshness", "independence"}), "source-investigator-v2.1"),
        ("counterexample-1", frozenset({"counterexample", "source"}), "counterexample-hunter-v2.1"),
        ("critic-1", frozenset({"critic", "entailment"}), "adversarial-critic-v2.1"),
        ("synth-1", frozenset({"synthesize"}), "synthesizer-v2.1"),
    )

    def candidates(self) -> list[AgentCandidate]:
        caps = self.provider_capabilities
        policy_hash = sha256_text(self.policy_version)
        rows: list[AgentCandidate] = []
        for name, capabilities, role_version in self._PHENOTYPES:
            prompt_hash = sha256_text(f"mimicus:{role_version}:{name}")
            tool_hash = sha256_obj({"phenotype": role_version, "declared_capabilities": sorted(capabilities), "provider_tool_manifest_hash": caps.tool_manifest_hash})
            fingerprint = exact_fingerprint(
                provider=caps.provider_id,
                model=caps.model_id,
                model_version=caps.version,
                phenotype=name,
                phenotype_version=role_version,
                system_prompt_hash=prompt_hash,
                tool_manifest_hash=tool_hash,
                policy_hash=policy_hash,
                provider_adapter_version=caps.adapter_version,
            )
            rows.append(
                AgentCandidate(
                    fingerprint=fingerprint,
                    name=name,
                    capabilities=capabilities,
                    provider=caps.provider_id,
                    model=caps.model_id,
                    prompt_hash=prompt_hash,
                    tool_hash=tool_hash,
                    phenotype_version=role_version,
                    policy_hash=policy_hash,
                    provider_adapter_version=caps.adapter_version,
                    runtime_model_version=caps.version,
                )
            )
        return rows

    def identity_for(self, candidate: AgentCandidate) -> AgentIdentity:
        return make_identity(
            fingerprint=candidate.fingerprint,
            provider=candidate.provider,
            model_family=candidate.model,
            phenotype=candidate.name,
            tool_policy_hash=candidate.tool_hash,
            runtime_model_version=candidate.runtime_model_version,
            phenotype_version=candidate.phenotype_version,
            system_prompt_hash=candidate.prompt_hash,
            tool_manifest_hash=candidate.tool_hash,
            policy_hash=candidate.policy_hash,
            provider_adapter_version=candidate.provider_adapter_version,
        )


@dataclass
class SafeFalsifierService:
    def specs(self, domain: str) -> dict[str, FalsifierSpec]:
        return builtin_specs(domain)

    def run(self, spec: FalsifierSpec, context: dict[str, object]) -> FalsifierExecution:
        return execute_primitive(spec, context)


@dataclass
class ImmuneMemoryService:
    repository: Repository

    def retrieve(self, domain: str) -> list[MemoryItem]:
        return [item for item in self.repository.eligible_memory(domain) if retrieval_gate(item, domain=domain)]

    def injectable(self, item: MemoryItem, target_fingerprint: str, domain: str) -> bool:
        return retrieval_gate(item, domain=domain) and cross_agent_gate(item, target_fingerprint)


@dataclass
class MimicusCoalitionService:
    def select(self, profile: ThreatProfile, candidates: list[AgentCandidate], max_agents: int) -> tuple[list[AgentCandidate], dict[str, object]]:
        return select_coalition(profile, candidates, max_agents)


@dataclass
class SparseCommunicationService:
    def select(self, candidates: list[CommunicationCandidate], k: int = 2) -> list[CommunicationCandidate]:
        return select_sparse_edges(candidates, k=k)


@dataclass
class LocalSandboxService:
    allowed: frozenset[str] = frozenset({"numeric_invariant", "freshness", "source_independence", "citation_entailment", "counterexample_search"})

    def permits(self, primitive: str) -> bool:
        return primitive in self.allowed


@dataclass
class LedgerTelemetryService:
    counters: dict[str, int] = field(default_factory=dict)

    def increment(self, key: str, amount: int = 1) -> None:
        self.counters[key] = self.counters.get(key, 0) + amount

    def snapshot(self) -> dict[str, int]:
        return dict(sorted(self.counters.items()))


@dataclass(frozen=True)
class RuntimeServices:
    storage: RepositoryStorage
    provider: Provider
    agent_factory: BuiltinAgentFactory
    falsifiers: SafeFalsifierService
    memory: ImmuneMemoryService
    coalition: MimicusCoalitionService
    communication: SparseCommunicationService
    sandbox: LocalSandboxService
    telemetry: LedgerTelemetryService
    lead_decision: LeadDecisionService

    @property
    def repository(self) -> Repository:
        return self.storage.repository
