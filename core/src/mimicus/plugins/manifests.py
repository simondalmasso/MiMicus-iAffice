from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from mimicus.canonical import sha256_obj

PluginKind = Literal[
    "model_provider",
    "agent_factory",
    "falsifier",
    "memory_backend",
    "storage_backend",
    "coalition_policy",
    "communication_policy",
    "sandbox",
    "telemetry",
    "decision_policy",
    "effect_policy",
]


class PluginManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    kind: PluginKind
    capabilities: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    config_schema: dict[str, object] = Field(default_factory=dict)
    provenance: str = "builtin"
    source_hash: str = Field(min_length=64, max_length=64)

    @property
    def manifest_hash(self) -> str:
        return sha256_obj(self)
