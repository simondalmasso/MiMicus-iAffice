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


## Additional candidate audit — user batch 2026-10-03

Constraint applied: do **not** install or absorb an agent platform merely because it is interesting. A candidate must add a missing, separable primitive with a mandatory-$0/local fallback, clear rights, and no competing orchestration authority.

| Candidate | License / cost reality | Mimicus verdict | Exact value, if any |
|---|---|---|---|
| Panniantong/Agent-Reach | MIT. Local/read-only paths can be $0; authenticated social channels depend on browser state/cookies and may carry account-risk. | **DEFER — optional ProspectSource pattern only** | Its ordered channel backends + real health probes/doctor are useful for future source discovery. Do not install it into LAYA now; discovery is not the active bottleneck and Facebook/Reddit setters are separate workstreams. |
| CopilotKit/OpenMuse | MIT. Local sample exists, but full live use expects CopilotKit Intelligence/model configuration; its documented Render production shape uses paid Standard services. | **PATTERN ONLY / DEFER** | Durable task receipts, pause/resume/cancel/retry, lease recovery and human browser takeover are good reference patterns for a future long-running worker. Current Mimicus does not need the whole personal-agent stack. |
| CopilotKit/OpenBot | MIT. Self-hostable, but full stack brings Docker/Postgres/CopilotKit/model infrastructure. | **HIGH-VALUE PATTERN; NO PLATFORM IMPORT** | Keep three patterns for a future BrowserActuator: central action barrier during human takeover; one central classification of acting vs read-only paths; deny-by-default/allowlist egress with metadata/link-local hard-deny. Do not replace Mimicus EffectPolicy or DagExecutor. |
| CopilotKit/OpenDots | MIT. Self-hostable template, but conversation/model/Intelligence/computer features introduce a large stack. | **REJECT CORE; UX REFERENCE ONLY** | Review-before-save cards and per-agent permission surfaces are useful UI references. Its Spaces/Dots/background/calls/Slack/computer stack duplicates product layers, not a missing Mimicus primitive. |
| CopilotKit/OpenTag | MIT. Quick start expects CopilotKit/OpenAI/Slack; self-host alternatives exist but are not a zero-complexity dependency. | **ADOPT ONE SAFETY PATTERN** | Unknown/unclassifiable mutating tool effects must fail safe as destructive and require approval. Approval UI should show bounded, human-readable action fields. This complements the existing exact-envelope, one-time Mimicus EffectApprovalReceipt; no OpenTag runtime dependency. |
| gawkbot | Sustainable Use License, not MIT/Apache. Internal/non-commercial use is allowed; hosted/commercial redistribution is restricted. Local runtime can be $0 aside from chosen model/provider. | **PATTERN ONLY; DO NOT COPY CODE** | Per-action approvals, expiring permission grants, per-bot tool allowlists and local audit logs align with Mimicus. Mimicus already has one-time expiring receipts, so no new runtime is justified. License is an additional reason not to absorb implementation. |
| b-nnett/grok-bot-0.18-reconstructed | No upstream source-code license is asserted; repo is an unofficial binary reconstruction and is archived. | **REJECT** | Local Docker sandbox/router ideas are already available from cleaner MIT/Apache sources. Rights/provenance uncertainty alone blocks integration. |
| hr98w/jev-visual | MIT original code; Qwen3.5/MLX local inference. Requires Apple Silicon + Metal and ~596 MiB model download in documented setup. | **REJECT RUNTIME; KEEP ALGORITHM IDEA** | Shared-prefix candidate scoring is an interesting future DecisionProvider optimization. Current Windows/Intel Mimicus baseline cannot use this MLX implementation, and its candidate probabilities are not correctness estimates. |
| 0xNyk/council-of-high-intelligence | MIT. Uses host/provider model calls; cost depends on selected providers. | **PATTERN ONLY / MOSTLY DUPLICATE** | Evidence labels, predeclared decision criteria, dissent/kill criteria and outcome review are useful documentation patterns. Multi-persona council execution duplicates paired_verify/sparse_graph/falsification and would add token/cost overhead. |
| volotat/mini-AGI | MIT, but documented target is an 8 GB VRAM GPU and continual training; project explicitly describes current model as toy-level. | **REJECT** | No production Mimicus gap is solved. It adds training/GPU/storage complexity and does not fit the mandatory-$0 current hardware baseline. |

### Net integration decision from this batch

**No new framework/runtime dependency is justified.**

The only net-new rules worth carrying forward are:

1. **Effect classification fails dangerous.** Unknown/unclassifiable tool effect => require approval; never assume harmless.
2. **Human takeover closes action admission centrally.** Future browser/computer actuator gets one action barrier, not scattered per-handler checks.
3. **Network egress is policy, not convenience.** Future remote/browser actuator must support `deny_all` / allowlist semantics and hard-deny cloud metadata/link-local destinations before dispatch.
4. **Action review must be legible.** Approval payloads should show bounded human-readable fields while the canonical receipt remains bound to the exact hashed envelope.
5. **Source adapters stay subordinate.** Agent-Reach-style source routing, if ever used, is a read-only `ProspectSource`/retrieval adapter; it cannot become a second orchestrator.
6. **Candidate scoring is an experiment, not a dependency.** Jev-style shared-prefix scoring may be benchmarked later only on a portable backend and against the deterministic Mimicus baseline.

### Explicit non-adoptions

Do not add:
- OpenMuse/OpenBot/OpenDots/OpenTag as application frameworks;
- gawkbot source code;
- reconstructed Grok Bot code/assets;
- Council as a second deliberation runtime;
- mini-AGI training/runtime;
- Jev Visual MLX/Qwen runtime on the current Windows baseline;
- Agent-Reach credentialed social tooling inside core Mimicus.

### Sources checked for this batch

Primary repository files were read through GitHub, including:
- Agent-Reach `README.md`, `LICENSE`, `agent_reach/core.py`;
- OpenMuse `README.md`, `LICENSE`;
- OpenBot `README.md`, `LICENSE`, `agent-computer/src/action-barrier.ts`, `authorisation.ts`, `egress.ts`;
- OpenDots `README.md`, `LICENSE`, page review / learning selectors;
- OpenTag `README.md`, `LICENSE`, `write_confirmation.py`, `composio_tools/effects.py`;
- gawkbot `LICENSE`, `ARCHITECTURE.md` and public site;
- grok-bot reconstruction `README.md`, `NOTICE.md`, `PROVENANCE.md`;
- Jev Visual `README.md`, `LICENSE`, `scoring.py`;
- Council `README.md`, `LICENSE`, `SKILL.md`;
- mini-AGI `README.md`, `LICENSE`.

Checked: 2026-10-03.
