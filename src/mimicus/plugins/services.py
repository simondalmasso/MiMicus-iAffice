from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from mimicus.agents.identity import AgentIdentity, make_identity
from mimicus.canonical import sha256_obj, sha256_text
from mimicus.coalition.selector import AgentCandidate, select_coalition
from mimicus.coalition.threat_profile import ThreatProfile
from mimicus.falsifiers.builtins import builtin_specs
from mimicus.falsifiers.primitives import execute_primitive
from mimicus.falsifiers.spec import FalsifierExecution, FalsifierSpec
from mimicus.memory.gates import cross_agent_gate, retrieval_gate
from mimicus.memory.models import MemoryItem
from mimicus.orchestration.communication import CommunicationCandidate, select_sparse_edges
from mimicus.providers.base import Provider
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


@dataclass
class RepositoryStorage:
    repository: Repository


@dataclass
class BuiltinAgentFactory:
    def candidates(self) -> list[AgentCandidate]:
        rows = [
            ("numeric-1", {"numeric", "synthesize"}, "provider-a", "math-v2"),
            ("source-1", {"source", "freshness", "independence"}, "provider-b", "research-v2"),
            ("counterexample-1", {"counterexample", "source"}, "provider-c", "hunt-v2"),
            ("critic-1", {"critic", "entailment"}, "provider-d", "critic-v2"),
            ("synth-1", {"synthesize"}, "provider-e", "synth-v2"),
        ]
        return [
            AgentCandidate(
                fingerprint=sha256_obj({"provider": provider, "model": model, "name": name, "policy": "mimicus-v0.2"}),
                name=name,
                capabilities=frozenset(caps),
                provider=provider,
                model=model,
                prompt_hash=sha256_text(f"{name}:v2"),
                tool_hash=sha256_text(f"tools:{name}"),
            )
            for name, caps, provider, model in rows
        ]

    def identity_for(self, candidate: AgentCandidate) -> AgentIdentity:
        return make_identity(
            fingerprint=candidate.fingerprint,
            provider=candidate.provider,
            model_family=candidate.model,
            phenotype=candidate.name,
            tool_policy_hash=candidate.tool_hash,
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

    @property
    def repository(self) -> Repository:
        return self.storage.repository
