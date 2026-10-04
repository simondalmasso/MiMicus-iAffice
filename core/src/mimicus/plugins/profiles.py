from __future__ import annotations

import os
from dataclasses import dataclass
from typing import cast

from mimicus.commercial.decision import DeterministicLeadDecisionService
from mimicus.effects.dispatcher import EffectDispatcher
from mimicus.effects.store import EffectStore
from mimicus.plugins.builtin import BuiltinPlugin, builtin_manifest
from mimicus.plugins.registry import PluginKernel
from mimicus.plugins.services import (
    BuiltinAgentFactory,
    EffectDispatchService,
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
from mimicus.providers.openai_compatible import OpenAICompatibleProvider
from mimicus.providers.scripted import ScriptedProvider
from mimicus.storage.repository import Repository


@dataclass(frozen=True)
class Profile:
    name: str
    network_allowed: bool
    provider: str
    database_kind: str


def _env_bool(name: str, *, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"{name} must be a boolean value")


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or not value.strip():
        raise ValueError(f"{name} is required for this profile")
    return value.strip()


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
    "nvidia": Profile("nvidia", True, "nvidia_nim", "sqlite"),
    "test": Profile("test", False, "scripted", "sqlite-temp"),
}


def _build_provider(profile_name: str) -> Provider:
    if profile_name in {"offline", "test"}:
        return ScriptedProvider()
    if profile_name == "openai":
        return OpenAIAgentsProvider(
            os.getenv("MIMICUS_OPENAI_MODEL", "gpt-5-mini"),
            input_usd_per_million_tokens=_env_float("MIMICUS_OPENAI_INPUT_USD_PER_MILLION_TOKENS"),
            output_usd_per_million_tokens=_env_float("MIMICUS_OPENAI_OUTPUT_USD_PER_MILLION_TOKENS"),
            max_cost_per_call_usd=_env_float("MIMICUS_OPENAI_MAX_COST_PER_CALL_USD"),
        )
    if profile_name == "nvidia":
        return OpenAICompatibleProvider(
            model=os.getenv("MIMICUS_NVIDIA_MODEL", "deepseek-ai/deepseek-v4.1-flash"),
            base_url="https://integrate.api.nvidia.com/v1",
            api_key=_require_env("NVIDIA_API_KEY"),
            provider_id="nvidia_nim",
            provider_version="nvidia-nim/deepseek-v4.1",
            known_zero_cost=_env_bool("MIMICUS_NVIDIA_KNOWN_ZERO_COST"),
            input_usd_per_million_tokens=_env_float("MIMICUS_NVIDIA_INPUT_USD_PER_MILLION_TOKENS"),
            output_usd_per_million_tokens=_env_float("MIMICUS_NVIDIA_OUTPUT_USD_PER_MILLION_TOKENS"),
            max_cost_per_call_usd=_env_float("MIMICUS_NVIDIA_MAX_COST_PER_CALL_USD"),
        )
    raise ValueError(f"unsupported provider profile: {profile_name}")


def build_kernel(profile_name: str, database_url: str | None = None, *, provider_override: Provider | None = None) -> PluginKernel:
    if profile_name not in PROFILES:
        raise ValueError(f"unknown profile: {profile_name}")
    db_url = database_url or os.environ.get("MIMICUS_DATABASE_URL") or "sqlite:///mimicus.db"
    repository = Repository(db_url)
    provider: Provider = provider_override or _build_provider(profile_name)
    storage = RepositoryStorage(repository)
    factory = BuiltinAgentFactory(provider.capabilities)
    effect_dispatch = EffectDispatcher(store=EffectStore(repository))
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
        BuiltinPlugin(
            builtin_manifest(
                "effects.approval",
                "effect_policy",
                ("effect_dispatch",),
                dependencies=("storage.sqlite",),
            ),
            effect_dispatch,
        ),
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
        effect_dispatch=cast(EffectDispatchService, kernel.services.get("effect_dispatch")),
    )
    hashes = [plugin.manifest.manifest_hash for plugin in kernel.plugins.values()]
    return services, hashes, kernel
