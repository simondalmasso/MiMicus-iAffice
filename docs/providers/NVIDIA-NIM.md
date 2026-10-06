# NVIDIA NIM provider

MiMicus can use NVIDIA-hosted NIM endpoints through the generic OpenAI-compatible provider adapter.

## Default profile

- profile: `nvidia`
- provider ID: `nvidia_nim`
- endpoint: `https://integrate.api.nvidia.com/v1`
- model: `deepseek-ai/deepseek-v4.1-flash`
- credential: `NVIDIA_API_KEY`

The adapter does not gain orchestration authority. LAYA / `MiMicusEngine` remains the control plane.

## Official usage boundary

NVIDIA currently labels DeepSeek V4.1 Flash as a **Free Endpoint** and documents free NIM API access for Developer Program members for prototyping, research, development and testing.

NVIDIA also documents that production use requires an NVIDIA AI Enterprise entitlement/license.

Therefore MiMicus treats the NVIDIA profile as:

- `provider_usage_scope = development_prototyping`
- `production_entitlement_required = true`

This is reported by `mimicus doctor --profile nvidia`.

## Cost fail-closed behavior

MiMicus does not bake vendor promotional pricing into runtime truth.

Default:

```text
MIMICUS_NVIDIA_KNOWN_ZERO_COST unset
=> known_zero_cost = false
=> USD 0 multi-call execution fail-closes without authoritative cost metadata
```

For a development/prototyping session where the operator has verified that the hosted endpoint is currently free:

```bash
export MIMICUS_NVIDIA_KNOWN_ZERO_COST=1
```

This flag is a **cost assertion for that run only**. It is not a production-license assertion and does not override NVIDIA terms.

## Security

- API key is required explicitly and is never exposed in provider capabilities/repr.
- endpoint must be HTTPS and cannot embed credentials.
- Agents SDK tracing is disabled for the non-OpenAI endpoint.
- no global OpenAI SDK defaults are mutated.
- provider replacement does not alter memory, evidence, effect or orchestration authority.

## Official references checked

- https://docs.api.nvidia.com/nim/reference/nvidia-deepseek-v4_1-flash
- https://docs.api.nvidia.com/nim/reference/nvidia-deepseek-v4_1-flash-infer
- https://docs.api.nvidia.com/nim/docs/run-anywhere
- https://docs.api.nvidia.com/nim/docs/product
- https://build.nvidia.com/models?q=deepseek

Checked 2026-10-05.


## Output bound

NVIDIA's DeepSeek V4.1 Flash Chat Completions API currently documents a vendor default of 262,144 output tokens when `max_tokens` is omitted.

MiMicus therefore sets an explicit development-safe default:

```bash
MIMICUS_NVIDIA_MAX_OUTPUT_TOKENS=8192
```

Override with a positive integer up to the endpoint's documented maximum of 1,048,576.

The resolved bound is:

- applied to both generation and challenge model calls through Agents SDK `ModelSettings(max_tokens=...)`;
- exposed by `mimicus doctor --profile nvidia` as `provider_max_output_tokens`;
- included in the provider runtime version, so exact agent fingerprints change when the bound changes.

This is a safety/latency bound, not a claim about NVIDIA quotas or billing.
