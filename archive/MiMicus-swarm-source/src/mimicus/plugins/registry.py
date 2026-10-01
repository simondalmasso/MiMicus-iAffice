from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from mimicus.plugins.api import Plugin, PluginContext


class ServiceRegistry:
    def __init__(self) -> None:
        self._services: dict[str, tuple[str, Any]] = {}

    def register(self, capability: str, owner: str, service: Any) -> None:
        if capability in self._services:
            existing = self._services[capability][0]
            raise ValueError(f"capability conflict: {capability} already owned by {existing}")
        self._services[capability] = (owner, service)

    def get(self, capability: str) -> Any:
        return self._services[capability][1]

    def unregister_owner(self, owner: str) -> None:
        for capability in [k for k, (registered_owner, _) in self._services.items() if registered_owner == owner]:
            del self._services[capability]

    def snapshot(self) -> dict[str, str]:
        return {capability: owner for capability, (owner, _) in sorted(self._services.items())}


class PluginKernel:
    def __init__(self) -> None:
        self.plugins: dict[str, Plugin] = {}
        self.context = PluginContext()
        self.services = ServiceRegistry()
        self._mounted: list[str] = []

    def add(self, plugin: Plugin) -> None:
        pid = plugin.manifest.id
        if pid in self.plugins:
            raise ValueError(f"duplicate plugin id: {pid}")
        self.plugins[pid] = plugin

    def dependency_order(self) -> list[str]:
        indegree = {pid: 0 for pid in self.plugins}
        outgoing: dict[str, list[str]] = defaultdict(list)
        for pid, plugin in self.plugins.items():
            for dep in plugin.manifest.dependencies:
                if dep not in self.plugins:
                    raise ValueError(f"missing dependency {dep} for {pid}")
                indegree[pid] += 1
                outgoing[dep].append(pid)
        queue = deque(sorted(pid for pid, degree in indegree.items() if degree == 0))
        order: list[str] = []
        while queue:
            pid = queue.popleft()
            order.append(pid)
            for nxt in sorted(outgoing[pid]):
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    queue.append(nxt)
        if len(order) != len(self.plugins):
            raise ValueError("plugin dependency cycle detected")
        return order

    def mount_all(self) -> None:
        for pid in self.dependency_order():
            plugin = self.plugins[pid]
            mounted_caps = plugin.mount(self.context)
            declared = set(plugin.manifest.capabilities)
            if not set(mounted_caps).issubset(declared):
                raise ValueError(f"plugin {pid} mounted undeclared capability")
            for capability in mounted_caps:
                self.services.register(capability, pid, self.context.services[capability])
            self._mounted.append(pid)

    def unmount_all(self) -> None:
        for pid in reversed(self._mounted):
            plugin = self.plugins[pid]
            plugin.unmount(self.context)
            self.services.unregister_owner(pid)
        self._mounted.clear()
