# Mimicus external capability review — 2026-10-03

Rule: adopt only a **separable primitive** that preserves LAYA/MiMicusEngine authority, has a mandatory-$0 or removable fallback, is license-safe, benchmarkable, and removable.

| Candidate | Verdict | Why |
|---|---|---|
| msitarzewski/agency-agents | SELECTIVE PATTERN | MIT prompt/persona library. Extract only Deal Strategist, Discovery Coach, Sales Outreach/objection handling and Proposal Strategist. Do not install a 230-agent runtime. |
| Panniantong/Agent-Reach | OPTIONAL ProspectSource / DEFER | MIT read/search router over web/social tooling. Discovery is not the current bottleneck; browser/login state adds risk. Read-only only if later needed. |
| vllm-sr Decision 2.0 | HIGH-VALUE SHADOW EXPERIMENT | Apache-2.0 compact decision models (Kai/Eos/Sol family) with structured probabilistic decision outputs. Test Kai/Eos as subordinate lead-priority classifiers. Never override hard policy without benchmark evidence. |
| Cloudflare Clef / Clef-Flash | DEFER | Apache-2.0 typed probabilistic decision models, but 27B/9B is too heavy for current text lead triage baseline. |
| LangGraph | REJECT CORE | Strong MIT orchestration framework, but duplicates Morphology DAG + DagExecutor + LAYA. |
| PydanticAI agent loop | REJECT CORE | Mimicus already has Pydantic, OpenAI Agents and its own engine. |
| Pydantic Evals | OPTIONAL DEV ADAPTER | Good Python/Pydantic fit if current internal benchmark proves insufficient. |
| Mastra | REJECT CORE | Duplicate TS agent/workflow platform; no missing primitive justifies the platform switch. |
| Agno / AgentOS | REJECT CORE | Adds another runtime/control plane. |
| Cognee | DEFER | Graph-memory retriever only if SQLite/governed-memory benchmark proves a retrieval gap. |
| Graphiti | DEFER | Temporal graph retrieval is useful in principle, but must remain subordinate to governed memory authority. |
| Browser Use | EXPERIMENT ONLY | Compare direct Playwright first. Do not embed Browser Use's autonomous loop as a second orchestrator. |
| E2B | OPTIONAL SandboxService LATER | Real isolation primitive. Local allowlist/Docker baseline first; cloud is never mandatory. |
| NVIDIA OpenShell | ADOPT PATTERN NOW | Apache-2.0. Its deny-by-default filesystem/process/network policy, endpoint-bound credentials and reviewable authority expansion directly inform Mimicus EffectPolicy. Do not import its gateway/control plane. |
| Langfuse | OPTIONAL TELEMETRY SINK LATER | Useful traces/evals, but self-host footprint is heavier than current ledger. OTel seam first. |
| DeepEval | DEFER / DEV-ONLY | Useful pytest agent/trajectory evals, but overlaps existing benchmark; Pydantic Evals is a smaller stack fit first. |
| Prism Legal OS | REJECT | AGPL legal platform, wrong domain and large infra footprint. |
| Weber-GeoML/Choir | PATTERN ONLY | Deterministic trust-gate idea is relevant; runtime itself is domain-specific/pre-alpha. |
| cc-thinking-skills | SELECTIVE PATTERN ONLY | Use a few review methods (pre-mortem, theory of constraints, reversibility), not the whole catalog as runtime machinery. |
| 300+ AI-agent ecosystem lists | RESEARCH INDEX ONLY | Useful anti-rebuild index; never a runtime dependency. |
| “Dots” responsibility pattern | PRODUCT PATTERN | Persistent responsibility ownership + surfacing urgent decisions + ask-before-shared-system-change maps cleanly to LAYA/effect approval. |

## Immediate actions

1. **Effect authorization:** absorb OpenShell-style policy semantics into Mimicus' own boundary:
   deny by default; bind adapter/operation/destination/resource/payload/scope; credentials outside unrestricted adapter payloads; authority expansion requires explicit approval.

2. **Commercial closing:** use only a compact subset of Agency Agents as research material for a future bounded LAYA commercial advisor. Current problem is conversion/closing, not prospect discovery.

3. **Decision 2.0:** do not integrate a model yet. First add outcome labels:
   replied, qualified, proposal, won/lost, reason, time-to-reply, time-to-close.

   Then benchmark deterministic Mimicus policy vs Kai-0.6B / Eos-0.8B (Sol-2B only if local resource measurements justify it):
   macro-F1, Brier/calibration, false-priority rate, regret, latency, peak RAM/VRAM, mandatory monetary cost. Any hard-policy violation = automatic failure.

## No integration now

Do not add LangGraph, Mastra, Agno/AgentOS, Cognee/Graphiti, Langfuse self-host, Browser Use agent loop, E2B cloud, Clef local baseline, or Prism Legal OS.

## Canonical Mimicus architecture

`Evidence/Context -> LAYA Decision -> Morphology DAG -> Governed Memory/Retrieval -> Tools/Effects -> Evidence Ledger -> Evaluation/Falsification`

Cross-cutting:
`Authority Policy + Budget + Causal Replay + Human Approval`.

No reviewed candidate justifies replacing that structure.

## Primary sources checked

- https://github.com/msitarzewski/agency-agents
- https://github.com/Panniantong/Agent-Reach
- https://huggingface.co/collections/vllm-sr/decision-20
- https://huggingface.co/Cloudflare/clef
- https://github.com/langchain-ai/langgraph
- https://github.com/pydantic/pydantic-ai
- https://github.com/mastra-ai/mastra
- https://github.com/agno-agi/agno
- https://github.com/topoteretes/cognee
- https://github.com/getzep/graphiti
- https://github.com/browser-use/browser-use
- https://github.com/e2b-dev/E2B
- https://github.com/langfuse/langfuse
- https://github.com/confident-ai/deepeval
- https://github.com/FuturixAI-and-Quantum-Works/Prism-Legal-OS
- https://github.com/NVIDIA/OpenShell
- https://github.com/Weber-GeoML/Choir
- https://github.com/tjboudreaux/cc-thinking-skills

Checked: 2026-10-03.
