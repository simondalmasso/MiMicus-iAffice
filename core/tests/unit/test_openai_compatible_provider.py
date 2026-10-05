from __future__ import annotations

import asyncio

import pytest

from mimicus.orchestration.budget import BudgetLedger
from mimicus.providers.openai_compatible import OpenAICompatibleProvider


def test_openai_compatible_provider_is_fail_closed_on_cost_by_default() -> None:
    provider = OpenAICompatibleProvider(
        model="deepseek-ai/deepseek-v4.1-flash",
        provider_id="nvidia_nim",
        base_url="https://integrate.api.nvidia.com/v1",
        api_key="nvapi-secret",
    )

    caps = provider.capabilities
    assert caps.provider_id == "nvidia_nim"
    assert caps.model_id == "deepseek-ai/deepseek-v4.1-flash"
    assert caps.known_zero_cost is False
    assert caps.estimated_max_cost_per_call is None
    assert caps.pricing_metadata_authoritative is False
    assert "nvapi-secret" not in repr(provider)


def test_openai_compatible_provider_validates_endpoint() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        OpenAICompatibleProvider(
            model="x",
            provider_id="bad",
            base_url="http://example.test/v1",
            api_key="secret",
        )
    with pytest.raises(ValueError, match="credentials"):
        OpenAICompatibleProvider(
            model="x",
            provider_id="bad",
            base_url="https://user:pass@example.test/v1",
            api_key="secret",
        )
    with pytest.raises(ValueError, match="API key"):
        OpenAICompatibleProvider(
            model="x",
            provider_id="bad",
            base_url="https://example.test/v1",
            api_key="",
        )


def test_openai_compatible_provider_disables_sdk_tracing_per_run() -> None:
    provider = OpenAICompatibleProvider(
        model="x",
        provider_id="compatible",
        base_url="https://example.test/v1",
        api_key="secret",
    )

    config = provider._run_config()

    assert config is not None
    assert config.tracing_disabled is True


def test_explicit_zero_cost_opt_in_integrates_with_budget() -> None:
    unknown = OpenAICompatibleProvider(
        model="x",
        provider_id="compatible",
        base_url="https://example.test/v1",
        api_key="secret",
    )
    confirmed_free = OpenAICompatibleProvider(
        model="x",
        provider_id="compatible",
        base_url="https://example.test/v1",
        api_key="secret",
        known_zero_cost=True,
    )

    async def run() -> None:
        unknown_ledger = BudgetLedger(0.0)
        assert await unknown_ledger.reserve(
            "provider",
            unknown.capabilities.estimated_max_cost_per_call,
            known_zero_cost=unknown.capabilities.known_zero_cost,
        ) is None

        free_ledger = BudgetLedger(0.0)
        reservation = await free_ledger.reserve(
            "provider",
            confirmed_free.capabilities.estimated_max_cost_per_call,
            known_zero_cost=confirmed_free.capabilities.known_zero_cost,
        )
        assert reservation is not None
        assert reservation.estimated_max_usd == 0.0

    asyncio.run(run())


def test_explicit_zero_cost_reports_known_zero_cost() -> None:
    provider = OpenAICompatibleProvider(
        model="x",
        provider_id="compatible",
        base_url="https://example.test/v1",
        api_key="secret",
        known_zero_cost=True,
    )

    caps = provider.capabilities
    assert caps.known_zero_cost is True
    assert caps.estimated_max_cost_per_call == 0.0
    assert caps.pricing_metadata_authoritative is True
    assert provider._monetary_cost(None) == 0.0


def test_openai_compatible_output_cap_reaches_agent_model_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys
    import types

    module = types.ModuleType("agents")

    class ModelSettings:
        def __init__(self, *, max_tokens: int | None = None):
            self.max_tokens = max_tokens

    class Agent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class AsyncOpenAI:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class OpenAIChatCompletionsModel:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    module.ModelSettings = ModelSettings
    module.Agent = Agent
    module.AsyncOpenAI = AsyncOpenAI
    module.OpenAIChatCompletionsModel = OpenAIChatCompletionsModel
    monkeypatch.setitem(sys.modules, "agents", module)

    provider = OpenAICompatibleProvider(
        model="deepseek-ai/deepseek-v4.1-flash",
        provider_id="nvidia_nim",
        provider_version="nvidia-nim:deepseek-ai/deepseek-v4.1-flash",
        base_url="https://integrate.api.nvidia.com/v1",
        api_key="nvapi-secret",
        max_output_tokens=8192,
    )

    agent = provider.build_agent("critic", "test")

    assert agent.kwargs["model_settings"].max_tokens == 8192
    assert provider.capabilities.max_output_tokens == 8192
    assert "maxout=8192" in provider.capabilities.version


def test_compatible_output_cap_changes_agent_fingerprint() -> None:
    from mimicus.plugins.services import BuiltinAgentFactory

    low = OpenAICompatibleProvider(
        model="deepseek-ai/deepseek-v4.1-flash",
        provider_id="nvidia_nim",
        provider_version="nvidia-nim:deepseek-ai/deepseek-v4.1-flash",
        base_url="https://integrate.api.nvidia.com/v1",
        api_key="nvapi-secret",
        max_output_tokens=4096,
    )
    high = OpenAICompatibleProvider(
        model="deepseek-ai/deepseek-v4.1-flash",
        provider_id="nvidia_nim",
        provider_version="nvidia-nim:deepseek-ai/deepseek-v4.1-flash",
        base_url="https://integrate.api.nvidia.com/v1",
        api_key="nvapi-secret",
        max_output_tokens=8192,
    )

    low_fp = BuiltinAgentFactory(low.capabilities).candidates()[0].fingerprint
    high_fp = BuiltinAgentFactory(high.capabilities).candidates()[0].fingerprint

    assert low_fp != high_fp
