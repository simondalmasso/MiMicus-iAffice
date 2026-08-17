from __future__ import annotations

import os
from dataclasses import dataclass

from mimicus.plugins.builtin import BuiltinPlugin, builtin_manifest
from mimicus.plugins.registry import PluginKernel
from mimicus.providers.openai_agents import OpenAIAgentsProvider
from mimicus.providers.scripted import ScriptedProvider


@dataclass(frozen=True)
class Profile:
    name: str
    network_allowed: bool
    provider: str
    database_kind: str


PROFILES = {
    "offline": Profile("offline", False, "scripted", "sqlite"),
    "openai": Profile("openai", True, "openai_agents", "sqlite"),
    "test": Profile("test", False, "scripted", "sqlite-temp"),
}


def build_kernel(profile_name: str) -> PluginKernel:
    if profile_name not in PROFILES:
        raise ValueError(f"unknown profile: {profile_name}")
    kernel = PluginKernel()
    provider = ScriptedProvider() if profile_name != "openai" else OpenAIAgentsProvider(os.getenv("MIMICUS_OPENAI_MODEL", "gpt-5-mini"))
    plugins = [
        BuiltinPlugin(builtin_manifest("storage.sqlite", "storage_backend", ("storage",)), object()),
        BuiltinPlugin(builtin_manifest(f"model.{PROFILES[profile_name].provider}", "model_provider", ("model_provider",), dependencies=("storage.sqlite",)), provider),
        BuiltinPlugin(builtin_manifest("falsifiers.safe", "falsifier", ("falsifiers",)), object()),
        BuiltinPlugin(builtin_manifest("memory.immune", "memory_backend", ("memory",)), object()),
        BuiltinPlugin(builtin_manifest("coalition.mimicus", "coalition_policy", ("coalition",)), object()),
        BuiltinPlugin(builtin_manifest("communication.sparse", "communication_policy", ("communication",)), object()),
        BuiltinPlugin(builtin_manifest("sandbox.local", "sandbox", ("sandbox",)), object()),
        BuiltinPlugin(builtin_manifest("telemetry.ledger", "telemetry", ("telemetry",)), object()),
        BuiltinPlugin(builtin_manifest("agents.phenotypes", "agent_factory", ("agent_factory",)), object()),
    ]
    for plugin in plugins:
        kernel.add(plugin)
    return kernel
