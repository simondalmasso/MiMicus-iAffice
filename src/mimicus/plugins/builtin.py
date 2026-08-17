from __future__ import annotations

from dataclasses import dataclass

from mimicus.canonical import sha256_text
from mimicus.plugins.api import Plugin, PluginContext
from mimicus.plugins.manifests import PluginManifest, PluginKind


@dataclass
class BuiltinPlugin(Plugin):
    manifest: PluginManifest
    service: object

    def mount(self, context: PluginContext) -> list[str]:
        mounted: list[str] = []
        for capability in self.manifest.capabilities:
            context.services[capability] = self.service
            mounted.append(capability)
        return mounted

    def unmount(self, context: PluginContext) -> None:
        for capability in self.manifest.capabilities:
            context.services.pop(capability, None)


def builtin_manifest(plugin_id: str, kind: PluginKind, capabilities: tuple[str, ...], *, dependencies: tuple[str, ...] = ()) -> PluginManifest:
    source_hash = sha256_text(f"mimicus-builtin:{plugin_id}:0.1.0:{kind}:{','.join(capabilities)}")
    return PluginManifest(
        id=plugin_id,
        version="0.1.0",
        kind=kind,
        capabilities=capabilities,
        dependencies=dependencies,
        config_schema={},
        provenance="source-controlled builtin",
        source_hash=source_hash,
    )
