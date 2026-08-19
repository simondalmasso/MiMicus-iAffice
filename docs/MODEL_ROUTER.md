# Model router

Tiers: T0 no model; T1 cheap/fast Free-compatible; T2 normal Free reasoning; T3 strongest Free-compatible for CEO/AUD/high risk; T4 external provider disabled by default.

Verified 2026-08-19 selection baseline: T1 `@cf/zai-org/glm-4.7-flash`; T2 `@cf/qwen/qwen3-30b-a3b-fp8` (Dev uses `@cf/openai/gpt-oss-20b`); T3 `@cf/openai/gpt-oss-120b` (Dev uses `@cf/nvidia/nemotron-3-120b-a12b`). Paid-only GLM-5.2 and Kimi K2.6/K2.7-code are hard-denied.

Every successful call records role, task, model/tier, token usage when returned, estimated neurons, latency, selection reason, result hash and quota state. Cloudflare quota/403 errors normalize to fail-closed states. AI soft/hard caps are 7,500/8,500 neurons/day.
