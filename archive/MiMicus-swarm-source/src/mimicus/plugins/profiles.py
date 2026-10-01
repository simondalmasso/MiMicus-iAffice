from __future__ import annotations

import os
from dataclasses import dataclass
from typing import cast

from mimicus.commercial.decision import DeterministicLeadDecisionService
from mimicus.plugins.builtin import BuiltinPlugin, builtin_manifest
from mimicus.plugins.registry import PluginKernel
from mimicus.plugins.services import (
    BuiltinAgentFactory,
    ImmuneMemoryService,
    LeadDecisionService,
    LedgerTelemetryService,
    LocalSandboxService,
    MimicusCoalitionService,
    RepositoryStorage,
    RuntimeServices,
    SafeFalsifierService,
    SparseCommunicationService,
)
from mimicus.providers.base import Provider
from mimicus.providers.openai_agents import OpenAIAgentsProvider
from mimicus.providers.scripted import ScriptedProvider
from mimicus.storage.repository import Repository


@dataclass(frozen=True)
class Profile:
    name: str
    network_allowed: bool
    provider: str
    database_kind: str


def _env_float(name: str) -> float | None:
    value = os.getenv(name)
    if value is None or not value.strip():
        return None
    parsed = float(value)
    if parsed < 0:
        raise ValueError(f"{name} must be non-negative")
    return parsed


PROFILES = {
    "offline": Profile("offline", False, "scripted", "sqlite"),
    "openai": Profile("openai", True, "openai_agents", "sqlite"),
    "test": Profile("test", False, "scripted", "sqlite-temp"),
}


def build_kernel(profile_name: str, database_url: str | None = None, *, provider_override: Provider | None = None) -> PluginKernel:
    if profile_name not in PROFILES:
        raise ValueError(f"unknown profile: {profile_name}")
    db_url = database_url or os.environ.get("MIMICUS_DATABASE_URL") or "sqlite:///mimicus.db"
    repository = Repository(db_url)
    provider: Provider = provider_override or (
        ScriptedProvider()
        if profile_name != "openai"
        else OpenAIAgentsProvider(
            os.getenv("MIMICUS_OPENAI_MODEL", "gpt-5-mini"),
            input_usd_per_million_tokens=_env_float("MIMICUS_OPENAI_INPUT_USD_PER_MILLION_TOKENS"),
            output_usd_per_million_tokens=_env_float("MIMICUS_OPENAI_OUTPUT_USD_PER_MILLION_TOKENS"),
            max_cost_per_call_usd=_env_float("MIMICUS_OPENAI_MAX_COST_PER_CALL_USD"),
        )
    )
    storage = RepositoryStorage(repository)
    factory = BuiltinAgentFactory(provider.capabilities)
    plugins = [
        BuiltinPlugin(builtin_manifest("storage.sqlite", "storage_backend", ("storage",)), storage),
        BuiltinPlugin(builtin_manifest(f"model.{PROFILES[profile_name].provider}", "model_provider", ("model_provider",), dependencies=("storage.sqlite",)), provider),
        BuiltinPlugin(builtin_manifest("falsifiers.safe", "falsifier", ("falsifiers",), dependencies=("storage.sqlite",)), SafeFalsifierService()),
        BuiltinPlugin(builtin_manifest("memory.immune", "memory_backend", ("memory",), dependencies=("storage.sqlite",)), ImmuneMemoryService(repository)),
        BuiltinPlugin(builtin_manifest("coalition.mimicus", "coalition_policy", ("coalition",)), MimicusCoalitionService()),
        BuiltinPlugin(builtin_manifest("communication.sparse", "communication_policy", ("communication",)), SparseCommunicationService()),
        BuiltinPlugin(builtin_manifest("sandbox.local", "sandbox", ("sandbox",)), LocalSandboxService()),
        BuiltinPlugin(builtin_manifest("telemetry.ledger", "telemetry", ("telemetry",)), LedgerTelemetryService()),
        BuiltinPlugin(builtin_manifest("decision.commercial", "decision_policy", ("lead_decision",)), DeterministicLeadDecisionService()),
        BuiltinPlugin(builtin_manifest("agents.phenotypes", "agent_factory", ("agent_factory",)), factory),
    ]
    kernel = PluginKernel()
    for plugin in plugins:
        kernel.add(plugin)
    return kernel


def build_runtime_services(profile_name: str, database_url: str, *, provider_override: Provider | None = None) -> tuple[RuntimeServices, list[str], PluginKernel]:
    kernel = build_kernel(profile_name, database_url, provider_override=provider_override)
    kernel.mount_all()
    services = RuntimeServices(
        storage=cast(RepositoryStorage, kernel.services.get("storage")),
        provider=cast(Provider, kernel.services.get("model_provider")),
        agent_factory=cast(BuiltinAgentFactory, kernel.services.get("agent_factory")),
        falsifiers=cast(SafeFalsifierService, kernel.services.get("falsifiers")),
        memory=cast(ImmuneMemoryService, kernel.services.get("memory")),
        coalition=cast(MimicusCoalitionService, kernel.services.get("coalition")),
        communication=cast(SparseCommunicationService, kernel.services.get("communication")),
        sandbox=cast(LocalSandboxService, kernel.services.get("sandbox")),
        telemetry=cast(LedgerTelemetryService, kernel.services.get("telemetry")),
        lead_decision=cast(LeadDecisionService, kernel.services.get("lead_decision")),
    )
    hashes = [plugin.manifest.manifest_hash for plugin in kernel.plugins.values()]
    return services, hashes, kernel
