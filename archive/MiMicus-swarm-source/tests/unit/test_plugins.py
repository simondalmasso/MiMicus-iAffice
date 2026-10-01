from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from mimicus.plugins.builtin import BuiltinPlugin, builtin_manifest
from mimicus.plugins.loader import verify_allowlisted_plugin
from mimicus.plugins.profiles import PROFILES, build_kernel
from mimicus.plugins.registry import PluginKernel, ServiceRegistry


def test_profiles_mount_reversible() -> None:
    assert set(PROFILES) == {"offline", "openai", "test"}
    kernel = build_kernel("offline")
    order = kernel.dependency_order()
    assert order.index("storage.sqlite") < order.index("model.scripted")
    kernel.mount_all()
    assert "falsifiers" in kernel.services.snapshot()
    assert "lead_decision" in kernel.services.snapshot()
    kernel.unmount_all()
    assert kernel.services.snapshot() == {}
    with pytest.raises(ValueError):
        build_kernel("bogus")


def test_cycle_dependency_and_capability_conflict() -> None:
    kernel = PluginKernel()
    a = BuiltinPlugin(builtin_manifest("a", "telemetry", ("shared",), dependencies=("b",)), object())
    b = BuiltinPlugin(builtin_manifest("b", "sandbox", ("other",), dependencies=("a",)), object())
    kernel.add(a)
    kernel.add(b)
    with pytest.raises(ValueError, match="cycle"):
        kernel.dependency_order()

    registry = ServiceRegistry()
    registry.register("x", "a", object())
    with pytest.raises(ValueError, match="conflict"):
        registry.register("x", "b", object())
    assert registry.get("x") is not None
    registry.unregister_owner("a")
    assert registry.snapshot() == {}


def test_loader_allowlist_and_hash(tmp_path: Path) -> None:
    plugin = tmp_path / "plugin.py"
    plugin.write_text("value = 1\n", encoding="utf-8")
    digest = hashlib.sha256(plugin.read_bytes()).hexdigest()
    assert verify_allowlisted_plugin(plugin, [tmp_path], digest) == plugin.resolve()
    with pytest.raises(ValueError, match="hash"):
        verify_allowlisted_plugin(plugin, [tmp_path], "0" * 64)
    with pytest.raises(PermissionError):
        verify_allowlisted_plugin(plugin, [tmp_path / "other"], digest)
