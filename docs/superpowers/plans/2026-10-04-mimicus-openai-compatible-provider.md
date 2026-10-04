# MiMicus OpenAI-Compatible Provider V1 — Plan

1. RED tests for provider security, identity, cost semantics and per-run tracing.
2. Refactor OpenAIAgentsProvider with small protected seams for model object and Runner config.
3. Add OpenAICompatibleProvider using AsyncOpenAI + OpenAIChatCompletionsModel per provider instance.
4. Add `nvidia` profile with explicit key and free-tier opt-in.
5. Add doctor/profile tests; no network live test in default CI.
6. Full CI: tests/coverage, Ruff, mypy, build, cockpit dry-run.
