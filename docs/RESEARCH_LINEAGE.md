# Research lineage

MiMicus owns its orchestration semantics. The references below are conceptual lineage; no cited framework is used as a second orchestration control plane and no paper text is source code.

## Framework patterns

- OpenAI Agents SDK — model-facing agents, structured outputs, hooks/guardrails, tracing and bounded model execution. Runtime dependency: `openai-agents`; MiMicus retains coalition/trust/memory/falsification/mutation authority. Primary: https://github.com/openai/openai-agents-python
- DeepSeek Harness — capability/plugin composition, ordered bundles, typed services/events and reversible registrations. Pattern only; no DeepSeek Harness/Cordis/Node runtime or copied source. Primary: https://github.com/deepseek-ai/deepseek-harness
- Microsoft Agent Framework / Magentic-One — task/progress ledgers, explicit workflows, stagnation/replanning and replay concepts. Pattern only. Primary: https://github.com/microsoft/agent-framework
- LangGraph / Deep Agents — durable state/checkpoint and isolated subagent context concepts. Pattern only. Primary: https://github.com/langchain-ai/langgraph
- Google ADK — deterministic workflow boundaries, routing and fan-out/fan-in concepts. Pattern only. Primary: https://github.com/google/adk-python
- CrewAI — autonomy/control split. Pattern only. Primary: https://github.com/crewAIInc/crewAI
- Swarms — independent mixture/dynamic routing/topology concepts. Pattern only. Primary: https://github.com/kyegomez/swarms
- AgentScope — permissions/middleware/team-runtime separation and governed memory. Pattern only. Primary: https://github.com/agentscope-ai/agentscope
- CAMEL — evolvability tied to verifiable evaluation rather than self-scoring. Pattern only. Primary: https://github.com/camel-ai/camel
- MetaGPT — critical SOPs as executable/versioned policy rather than fixed role-play. Pattern only. Primary: https://github.com/FoundationAgents/MetaGPT

## 2025–2026 research concepts required by ORDER-002

- Skill-conditional trust / laundering: https://arxiv.org/abs/2606.14200
- Dynamic trust-aware sparse communication: https://arxiv.org/abs/2606.01828
- Removal-based agent attribution: https://arxiv.org/abs/2605.27621
- Dynamic role assignment: https://arxiv.org/abs/2601.17152
- Dynamic coalition formation / communication pricing: https://arxiv.org/abs/2608.07532
- Canary tool-selection diagnosis: https://arxiv.org/abs/2608.04719
- Correlated LLM errors: https://arxiv.org/abs/2506.07962
- Agent continual-learning evaluation: https://arxiv.org/abs/2606.02461
- Verified executable-evidence memory / error attribution: https://arxiv.org/abs/2604.17658
- Memory lifecycle poisoning defenses: https://arxiv.org/abs/2608.00426
- Systematic memory poisoning: https://arxiv.org/abs/2606.04329
- Persistent memory threats: https://arxiv.org/abs/2607.14651

Implementation synthesis is direct-evidence domain calibration, verified falsifier persistence, declarative falsifier contracts, domain bankruptcy, mutation only after confirmed evasion, fossil-regressed germinal promotion, origin-bound memory authority, correlated-error penalties and task-dependent morphology.
