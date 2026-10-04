from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from mimicus.plugins.builtin import BuiltinPlugin, builtin_manifest
from mimicus.plugins.loader import verify_allowlisted_plugin
from mimicus.plugins.profiles import PROFILES, build_kernel
from mimicus.plugins.registry import PluginKernel, ServiceRegistry


def test_profiles_mount_reversible() -> None:
    assert set(PROFILES) == {"offline", "openai", "nvidia", "test"}
    kernel = build_kernel("offline")
    order = kernel.dependency_order()
    assert order.index("storage.sqlite") < order.index("model.scripted")
    kernel.mount_all()
    assert "falsifiers" in kernel.services.snapshot()
    assert "lead_decision" in kernel.services.snapshot()
    assert "effect_dispatch" in kernel.services.snapshot()
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



def test_nvidia_profile_is_explicit_and_fail_closed_on_cost(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("NVIDIA_API_KEY", raising=False)
    monkeypatch.delenv("MIMICUS_NVIDIA_KNOWN_ZERO_COST", raising=False)

    with pytest.raises(ValueError, match="NVIDIA_API_KEY"):
        build_kernel("nvidia", "sqlite:///:memory:")

    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test-key")
    kernel = build_kernel("nvidia", "sqlite:///:memory:")
    kernel.mount_all()
    provider = kernel.services.get("model_provider")
    assert provider is not None
    assert provider.capabilities.provider_id == "nvidia_nim"
    assert provider.capabilities.model_id == "deepseek-ai/deepseek-v4.1-flash"
    assert provider.capabilities.known_zero_cost is False
    kernel.unmount_all()


def test_nvidia_profile_requires_explicit_free_tier_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test-key")
    monkeypatch.setenv("MIMICUS_NVIDIA_KNOWN_ZERO_COST", "1")

    kernel = build_kernel("nvidia", "sqlite:///:memory:")
    kernel.mount_all()
    provider = kernel.services.get("model_provider")
    assert provider is not None
    assert provider.capabilities.known_zero_cost is True
    assert provider.capabilities.estimated_max_cost_per_call == 0.0
    kernel.unmount_all()


def test_nvidia_free_tier_flag_rejects_ambiguous_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test-key")
    monkeypatch.setenv("MIMICUS_NVIDIA_KNOWN_ZERO_COST", "maybe")

    with pytest.raises(ValueError, match="boolean"):
        build_kernel("nvidia", "sqlite:///:memory:")
