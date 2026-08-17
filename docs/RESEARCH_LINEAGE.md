# Research lineage

MiMicus V0.2 keeps one native orchestration control plane. ORDER-003 reviewed external projects for concepts and implemented the adopted mechanisms clean-room in this repository; no source code from the projects below was copied into MiMicus.

## ORDER-003 concept lineage

### The Swarm Corporation / PARL
Reference: `https://github.com/The-Swarm-Corporation/PARL`

Adopted concept: parallel decomposition and critical-path/serial-collapse measurement. MiMicus implements execution-time `work_steps`, `critical_steps`, measured critical path, serial-work estimate, peak concurrency, finish rate, speedup/efficiency and avoidable-serialization telemetry. Not adopted: PARL training runtime, RL, PyTorch or `open-parl` dependency.

### AdvancedResearch
Reference: `https://github.com/The-Swarm-Corporation/AdvancedResearch`

Adopted concept: real fan-out/fan-in. MiMicus represents it in its own executable Morphology DAG and bounded async executor. No `advanced-research` or `swarms` runtime dependency was added.

### AI-CoScientist
Reference: `https://github.com/The-Swarm-Corporation/AI-CoScientist`

Adopted concept: proximity/diversity control. MiMicus uses deterministic token/claim-feature and provenance/evidence overlap, while preserving useful contradiction. Fixed scientific-role topologies and Elo-as-truth were not adopted.

### Agent Bazaar
Reference: `https://github.com/The-Swarm-Corporation/agent-bazaar-implementation`

Adopted threat model: identity whitewashing. MiMicus separates exact fingerprints from declared/known lineages and puts a new fingerprint from a domain-bankrupt known lineage into PROBATION until recovery audition succeeds. Positive trust never transfers automatically.

### swarm-models
Reference: `https://github.com/The-Swarm-Corporation/swarm-models`

Adopted concept: provider adapter normalization. The package itself was not added. MiMicus retains its own typed provider protocol and OpenAI Agents SDK adapter.

### swarms-memory
Reference: `https://github.com/The-Swarm-Corporation/swarms-memory`

Adopted concept: backend replaceability only. Authority, provenance, retrieval and cross-agent gates remain MiMicus policy and are not delegated to a vector-memory package.

### swarms-core
Reference: `https://github.com/The-Swarm-Corporation/swarms-core`

Decision: no Rust migration in V0.2. The Python executor/provider boundaries remain explicit so a later measured bottleneck could justify an alternate backend.

## K3 lineage

ORDER-002 K3 compatibility artifacts, contract hashes and fossil lineage remain preserved under `evidence/ORDER-002/` and the K3-specific documentation. ORDER-003 does not rewrite the trusted primitive model: mutation stays declarative and limited to trusted primitive parameters/metadata.

## Evidence discipline

Research references explain design inspiration, not benchmark results. Measured ORDER-003 properties come from repository tests, process E2E artifacts and the execution-derived benchmark under `evidence/ORDER-003/`.
