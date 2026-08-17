from __future__ import annotations

import asyncio
import sys
import types

from mimicus.claims.models import Claim
from mimicus.providers.openai_agents import OpenAIAgentsProvider


def test_openai_agents_provider_contract_without_live_key(monkeypatch) -> None:
    module = types.ModuleType("agents")

    class Agent:
        def __init__(self, **kwargs):
            self.kwargs = kwargs
            self.name = kwargs["name"]

    class Result:
        final_output = Claim(statement="structured", domain="test", probability=0.7)
        last_agent = types.SimpleNamespace(name="mimicus-numerical_verifier")
        context_wrapper = types.SimpleNamespace(usage=types.SimpleNamespace(total_tokens=12))

    class Runner:
        @staticmethod
        async def run(agent, task, max_turns):
            assert agent.kwargs["output_type"] is Claim
            assert max_turns == 3
            assert task == "task"
            return Result()

    module.Agent = Agent
    module.Runner = Runner
    monkeypatch.setitem(sys.modules, "agents", module)
    provider = OpenAIAgentsProvider("gpt-test")
    built = provider.build_agent("numerical_verifier", "test")
    assert built.kwargs["model"] == "gpt-test"
    claim, metadata = asyncio.run(provider.generate_async("task", "numerical_verifier", "test"))
    assert claim.statement == "structured"
    assert metadata["last_agent"] == "mimicus-numerical_verifier"
    assert "12" in str(metadata["usage"])
