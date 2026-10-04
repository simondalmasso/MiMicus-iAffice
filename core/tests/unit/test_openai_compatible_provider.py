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
