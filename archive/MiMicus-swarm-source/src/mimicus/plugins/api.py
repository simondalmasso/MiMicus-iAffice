from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from mimicus.plugins.manifests import PluginManifest


@dataclass
class PluginContext:
    services: dict[str, Any] = field(default_factory=dict)
    state: dict[str, Any] = field(default_factory=dict)


class Plugin(ABC):
    manifest: PluginManifest

    @abstractmethod
    def mount(self, context: PluginContext) -> list[str]:
        return []

    @abstractmethod
    def unmount(self, context: PluginContext) -> None:
        return None
