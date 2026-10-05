# MiMicus NVIDIA NIM output-bound V1

ROLE=ARQ
BASE_SHA=ba37eb338d28f7cbbfbd7cfb80d28fc850f6d75a
BRANCH=arq/provider-nvidia-output-cap-v1
INTEGRATION_OWNER=ARQ provider output-bound

## Problem

NVIDIA's DeepSeek V4.1 Flash Chat Completions endpoint currently defaults `max_tokens` to 262144 when the caller does not specify one. MiMicus uses structured Claim / ChallengeResponse outputs that do not require an unbounded vendor default.

A provider-level timeout bounds wall time but does not make output-token intent explicit and does not make the cap part of runtime identity.

## Goal

Bound OpenAI-compatible output generation explicitly, make the bound visible in capabilities/doctor, and bind it into exact runtime model identity without changing LAYA authority.

## Contract

- `ProviderCapabilities.max_output_tokens: int | None`.
- `OpenAIAgentsProvider.max_output_tokens: int | None`; None preserves provider default.
- Agent and challenge paths apply `ModelSettings(max_tokens=...)` when configured.
- NVIDIA profile default: 8192 output tokens.
- Override: `MIMICUS_NVIDIA_MAX_OUTPUT_TOKENS`.
- NVIDIA accepts positive integer values only, capped at the endpoint's documented maximum 1048576.
- NVIDIA compatible provider version includes the resolved output cap, so agent exact fingerprints change when the cap changes.
- No change to commercial decisions, memory authority, effects, cockpit or deployment.

## Falsifiers

- NVIDIA default does not leave model max_tokens unset.
- override 4096 reaches Agent model settings.
- zero/negative/above-endpoint-limit values fail closed.
- two NVIDIA providers with different caps produce different candidate fingerprints.
- OpenAI profile with no configured cap keeps existing provider-default behavior.

## Evidence

NVIDIA API reference checked 2026-10-05:
- OpenAI-compatible POST /v1/chat/completions.
- documented max_tokens range 1..1048576.
- endpoint default max_tokens 262144.


## Implementation note

The resolved output-token cap is material runtime configuration. It is exposed through `ProviderCapabilities.max_output_tokens` and included in the OpenAI-compatible provider version string so agent exact fingerprints cannot silently reuse calibration across different output bounds.
