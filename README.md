# MiMicus Swarm

MiMicus V0.2 is a research implementation of an **agentic immune swarm runtime**. It persists authority-bearing immune state, compiles a task-specific coalition into a hashable executable Morphology DAG, executes independent work concurrently under bounded capacity, performs structured sparse challenges, and records replayable provenance for claims, tests, memory and learning transitions.

The repository does **not** claim that MiMicus is the world's first immune swarm or that it dominates every multi-agent baseline. Those are empirical questions. ORDER-003 replaces the historical ORDER-002 architecture-scripted benchmark methodology with actual A/B/C/D/E runners and one common post-run grader.

## Core thesis

> MiMicus learns which verified tests expose which classes of error, persists that immune knowledge, selects the smallest useful task-specific coalition, runs independent work concurrently, challenges only where information value justifies communication, and prevents unverified memory, identity whitewashing, correlated consensus, or self-mutations from acquiring authority.

## V0.2 properties

- Python 3.12 reference runtime with a synchronous CLI wrapper over an async-first engine.
- Plugin-composed `RuntimeServices` for storage, provider access, agent factory, falsifiers, memory, coalition, communication, sandbox and telemetry; no placeholder `object()` services.
- Executable Morphology DAGs with `solo`, `parallel_fanout`, `paired_verify`, `sparse_graph`, and justified `hierarchical_fanout_fanin` plans.
- Bounded concurrent execution with measured critical-path, serial-work, peak-concurrency, efficiency, finish-rate and avoidable-serialization metrics.
- Persistent exact-fingerprint/domain calibration, bankruptcy, lineage/probation and dedicated recovery audition handling.
- Persistent memory with WRITE, RETRIEVAL, PROMOTION and CROSS-AGENT gates reapplied across process restarts.
- Structured sparse challenge/rebuttal provider calls with bounded rounds, claim/evidence hashes and no raw hidden chain-of-thought exchange.
- Deterministic semantic proximity/marginal novelty signals that suppress redundancy while retaining useful contradiction.
- Declarative `FalsifierSpec` primitives only; database/model text is never executed as Python or another generated programming language.
- Integrated germinal learning: confirmed evasion -> persisted candidate -> frozen fossil regression -> deterministic PROMOTE/REJECT/QUARANTINE -> later restart reuse.
- Hash-chained event ledger and replay/tamper detection.
- SQLite by default; SQLAlchemy schema compiles for PostgreSQL.
- OpenAI Agents SDK provider plus credential-free scripted provider behind the same typed adapter boundary.
- Official MCP Python SDK Streamable HTTP endpoint at `/mcp`, including process-restart continuity tests.

## Locked install

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
mimicus doctor --profile offline
```

`requirements.lock` is verified in CI and direct dependencies are pinned in project metadata.

## Offline reference run

```bash
mimicus db upgrade
mimicus run --profile offline --task-file fixtures/tam_12x.json --budget-usd 0 --max-agents 4 --max-concurrency 4 --depth normal --learn
mimicus replay <run_id>
python -m mimicus.validation.order003_e2e evidence/ORDER-003
mimicus benchmark --profile offline --episodes 200 --output-dir evidence/ORDER-003
```

Offline mode requires no model API key and is the normative reproducibility path.

## OpenAI profile

Set `OPENAI_API_KEY` in the environment and run with `--profile openai`. The OpenAI Agents SDK is the model-facing adapter; MiMicus still owns coalition selection, falsification, memory authority, identity state, sparse communication, DAG execution and germinal policy. Missing live credentials do not invalidate the offline ORDER-003 gate; the reported status is `NOT_RUN_NO_CREDENTIAL` unless a live smoke is actually executed.

## MCP

```bash
mimicus serve --profile offline --host 0.0.0.0 --port 8765
```

The server exposes `run_mimicus(...)` and `get_mimicus_run(run_id)` over Streamable HTTP `/mcp`. See `docs/MCP.md`.

## Validation

```bash
ruff format --check .
ruff check .
mypy src/mimicus
pytest tests/unit tests/integration --cov=mimicus --cov-report=term-missing --cov-fail-under=90
python scripts/check_security.py
python scripts/check_ledger.py
python -m mimicus.validation.order003_e2e evidence/ORDER-003
mimicus benchmark --profile offline --episodes 200 --output-dir evidence/ORDER-003
```

The ORDER-003 process runner verifies restart persistence, verified-memory reuse with quarantined-memory rejection, bankruptcy/lineage whitewash defense and recovery, real sparse provider challenges, bounded parallelism, semantic proximity, germinal restart reuse, and MCP server restart continuity.

## Security boundary

MiMicus does not execute code generated by an LLM or stored in its database. Runtime falsifier mutations are validated data structures composed only from trusted source-controlled primitives. Out-of-tree plugins require an explicit allow-listed path plus SHA-256 match. See `SECURITY.md`, `docs/THREAT_MODEL.md`, `docs/K3_SEED_LINEAGE.md`, `docs/AGENT_IDENTITY.md`, and `docs/RESEARCH_LINEAGE.md`.

## Evidence

ORDER-002 evidence remains committed under `evidence/ORDER-002/` as historical provenance. Its architecture-scripted benchmark is explicitly superseded for comparative claims. ORDER-003 evidence is committed under `evidence/ORDER-003/`; exact-head CI reruns the required gates after the evidence commit so evidence is not treated as a substitute for current execution.

## License

MIT. See `LICENSE` and `THIRD_PARTY_NOTICES.md`.
