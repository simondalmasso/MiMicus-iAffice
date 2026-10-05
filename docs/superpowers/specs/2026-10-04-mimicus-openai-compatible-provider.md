# MiMicus OpenAI-Compatible Provider V1

## Goal

Add one reusable provider adapter for OpenAI-compatible Chat Completions endpoints, then expose NVIDIA NIM DeepSeek-V4.1-Flash as the first profile.

## Constraints

- LAYA / MiMicusEngine remains the only orchestration authority.
- No new Python dependency: use the OpenAI Agents SDK already installed.
- Do not change global OpenAI client/model defaults.
- Disable Agents SDK tracing per run for non-OpenAI endpoints.
- API keys must never appear in repr/capabilities/evidence.
- Base URL must be HTTPS and must not contain embedded credentials.
- Network provider is opt-in.
- The NVIDIA profile is not assumed to be free forever.
- NVIDIA hosted free endpoint access is development/prototyping scope; production entitlement is external and mandatory under NVIDIA's published terms.

## Cost policy

NVIDIA currently exposes DeepSeek-V4.1-Flash through an OpenAI-compatible trial endpoint.

MiMicus defaults the profile to:
- `known_zero_cost = false`
- no authoritative token pricing
- no estimated max cost unless operator config supplies one

Therefore a run with budget USD 0 fail-closes before provider work.

The operator may explicitly assert the current free tier for a run with:

`MIMICUS_NVIDIA_KNOWN_ZERO_COST=1`

That opt-in makes budget accounting record zero cost. This is an operator assertion for a development/prototyping session, not a baked-in vendor guarantee and not a production-license assertion.

## NVIDIA defaults

- profile: `nvidia`
- provider ID: `nvidia_nim`
- base URL: `https://integrate.api.nvidia.com/v1`
- model: `deepseek-ai/deepseek-v4.1-flash`
- API key env: `NVIDIA_API_KEY`

## Future providers

Groq, Cerebras, OpenRouter and similar OpenAI-compatible services can reuse the same adapter later. They should be profiles/config only, not new provider implementations.

## Non-goals

- automatic provider fallback/routing;
- silently claiming a vendor is free;
- live external calls in CI;
- changing decision/memory/effect authority;
- adding LiteLLM or another gateway.
