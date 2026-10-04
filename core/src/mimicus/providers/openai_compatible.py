from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any
from urllib.parse import urlsplit

from mimicus.providers.base import ProviderCapabilities
from mimicus.providers.openai_agents import OpenAIAgentsProvider


@dataclass
class OpenAICompatibleProvider(OpenAIAgentsProvider):
    """OpenAI-compatible Chat Completions provider with no global SDK mutation."""

    base_url: str = ""
    api_key: str = field(default="", repr=False)
    provider_id: str = "openai_compatible"
    provider_version: str = "configured"
    known_zero_cost: bool = False
    _chat_model: Any = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        parsed = urlsplit(self.base_url)
        if parsed.scheme.lower() != "https":
            raise ValueError("OpenAI-compatible base URL must use HTTPS")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("OpenAI-compatible base URL must not contain credentials")
        if not parsed.hostname:
            raise ValueError("OpenAI-compatible base URL must include a hostname")
        if not self.api_key.strip():
            raise ValueError("OpenAI-compatible provider requires an API key")
        if not self.provider_id.strip():
            raise ValueError("provider_id must be non-empty")

    @property
    def capabilities(self) -> ProviderCapabilities:
        base = super().capabilities
        return replace(
            base,
            provider_id=self.provider_id,
            version=self.provider_version,
            adapter_version="openai-compatible-chat-completions/mimicus-v1",
            known_zero_cost=self.known_zero_cost,
            estimated_max_cost_per_call=0.0 if self.known_zero_cost else base.estimated_max_cost_per_call,
            pricing_metadata_authoritative=self.known_zero_cost or base.pricing_metadata_authoritative,
        )

    def _agent_model(self) -> Any:
        if self._chat_model is None:
            from agents import AsyncOpenAI, OpenAIChatCompletionsModel

            client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
            self._chat_model = OpenAIChatCompletionsModel(
                model=self.model,
                openai_client=client,
            )
        return self._chat_model

    def _run_config(self) -> Any:
        from agents import RunConfig

        return RunConfig(tracing_disabled=True)

    def _monetary_cost(self, usage: Any) -> float | None:
        if self.known_zero_cost:
            return 0.0
        return super()._monetary_cost(usage)
