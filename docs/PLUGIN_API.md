# Plugin API

MiMicus capabilities are provided through a small source-controlled Python plugin kernel. `PluginManifest` is immutable and contains the plugin id/version/kind, provided capabilities, dependencies, config schema, provenance and source SHA-256. The canonical manifest hash is included in run provenance.

A plugin implements `mount(context)` and `unmount(context)`. Mounting registers typed capabilities into `ServiceRegistry`; unmounting reverses those registrations. `PluginKernel` computes deterministic dependency order, rejects missing dependencies/cycles, rejects duplicate capability ownership, and unmounts in reverse order.

```python
from mimicus.plugins.api import Plugin, PluginContext
from mimicus.plugins.manifests import PluginManifest


class ExamplePlugin(Plugin):
    manifest = PluginManifest(
        id="example.telemetry",
        version="1.0.0",
        kind="telemetry",
        capabilities=("example_telemetry",),
        dependencies=(),
        config_schema={},
        provenance="source controlled",
        source_hash="<sha256-of-reviewed-source>",
    )

    def mount(self, context: PluginContext) -> list[str]:
        context.services["example_telemetry"] = object()
        return ["example_telemetry"]

    def unmount(self, context: PluginContext) -> None:
        context.services.pop("example_telemetry", None)
```

Out-of-tree loading is fail-closed: the file must be contained by an explicitly allowed root and its bytes must match the expected SHA-256. There is no remote auto-install and no database-to-code load path. See `docs/PLUGIN_SYSTEM.md` for profiles and lifecycle rules.
