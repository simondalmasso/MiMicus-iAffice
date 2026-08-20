# MiMicus Swarm

MiMicus is a Python 3.12 research runtime for a persistent **agentic immune swarm**. The current ORDER-008 production core profiles a task, selects a bounded coalition and executable morphology, runs sealed provider work, executes claim-bound deterministic falsifiers against typed assertions and exact evidence projections, synthesizes a provenance-bound decision, and admits learned state only through authenticated verification authority.

The repository does not claim universal superiority or world-first status. Comparative claims are limited to committed benchmark evidence.

## Current production-runtime guarantees

- Normal CLI/MCP requests are core-locked to `source_mode=runtime`; task wording cannot activate fixture or legacy semantics.
- Deterministic F1..F5 falsifiers test the exact target claim assertion plus exact scoped evidence. Missing or incompatible typed assertions fail closed as `INCONCLUSIVE`.
- Canonical caller evidence is immutable; hierarchical workers receive immutable derived projections with their own identities and parent provenance.
- Provider evidence refs are validated against the exact material supplied to that provider call; unknown refs are rejected rather than auto-attached.
- Five executable morphologies remain reachable when justified: `solo`, `paired_verify`, `parallel_fanout`, `sparse_graph`, and `hierarchical_fanout_fanin`.
- Hierarchical fan-in composes complementary subtask decisions instead of treating different required propositions as disagreement.
- Verification authority is authenticated and run/claim/proof-bound. Contradictory same-origin adjudication requires explicit supersession, and revocation cascades through authority-derived learning, memory, removal attribution and promoted falsifier eligibility.
- `learn=False` is mutation-inert. With `learn=True`, authenticated verified outcomes can enter governed memory/learning; eligible state survives restart and revoked/superseded state is excluded.
- Normal runtime persists task/progress state and bounded communication; no-progress work replans or terminates inconclusive rather than looping indefinitely.
- Offline/scripted runtime supports semantic re-execution. Replay reports ledger/integrity verification separately from semantic re-execution truth; nondeterministic providers never claim semantic replay without a replayable record.
- MCP uses the official Python SDK Streamable HTTP transport at `/mcp` and exposes runtime evidence, not hidden fixture switches.

## Locked install

```bash
python3.12 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
mimicus doctor --profile offline
```

`requirements.lock` is checked in CI and the package is also built/installed from a wheel in the exact-head gate.

## Zero-key production quickstart

This path uses the normal production core with explicit structured evidence. It requires no model API key and does not infer facts from task words.

```bash
export MIMICUS_DATABASE_URL="sqlite:///mimicus-quickstart.db"
mimicus db upgrade
mimicus run \
  --profile offline \
  --task-file fixtures/order008_quickstart.json \
  --budget-usd 0 \
  --max-agents 1 \
  --max-concurrency 1 \
  --depth deep > /tmp/mimicus-order008-run.json

RUN_ID="$(python -c 'import json; print(json.load(open("/tmp/mimicus-order008-run.json"))["run_id"])')"
mimicus replay "$RUN_ID"
```

The task file contains caller-supplied `evidence` with numeric fields. CI executes this documented `run -> replay` path from a clean SQLite database.

For deterministic offline runs, replay should report `verified: true`, `integrity_verified: true`, and `semantic_reexecution_verified: true`. These are distinct claims: integrity means persisted material/ledger is intact; semantic re-execution means the deterministic core reproduced the relevant semantic hashes. A nondeterministic/live provider can legitimately be integrity-verified without being semantically re-executable.

## Public runtime evidence

A runtime task file may include bounded evidence items such as:

```json
{
  "task": "Verify the annual amount from explicit evidence.",
  "domain": "finance",
  "evidence": [
    {
      "origin": "caller://report",
      "independence_cluster": "publisher-a",
      "content": "Annual price is 100 and users are 12.",
      "extracted_facts": {
        "price": 100.0,
        "users": 12.0,
        "price_period": "annual",
        "claimed": 1200.0
      }
    }
  ]
}
```

Caller-supplied provenance authority is normalized by MiMicus. Supplying no evidence to an evidence-dependent task does not create hidden fixture facts; deterministic falsifiers remain `INCONCLUSIVE` where their required material is absent.

## MCP

```bash
export MIMICUS_DATABASE_URL="sqlite:///mimicus.db"
mimicus db upgrade
mimicus serve --profile offline --host 127.0.0.1 --port 8765
```

The server exposes `run_mimicus(...)`, `get_mimicus_run(run_id)` and verification surfaces over Streamable HTTP `/mcp`. Public `run_mimicus` accepts bounded structured evidence and does not expose `fixture`, `source_mode`, or `core_semantics` escape fields. See `docs/MCP.md`.

## Validation

```bash
ruff format --check .
ruff check .
mypy src/mimicus
pytest tests/unit tests/integration --cov=mimicus --cov-report=term-missing --cov-fail-under=90
python scripts/check_security.py
python scripts/check_ledger.py
python scripts/order008_evidence.py /tmp/ORDER-008
python scripts/order008_mcp_e2e.py /tmp/ORDER-008
mimicus benchmark --profile offline --episodes 200 --output-dir /tmp/benchmark
```

The PR workflow additionally verifies migrations, PostgreSQL schema compilation, wheel installation, F001..F037 runtime regression mapping, claim-bound F1..F5 kills, F038..F044 closure, MCP restart/revocation, semantic replay/tamper behavior, >=200 episodes per architecture with all five MiMicus morphologies, and the committed ORDER-008 manifest against freshly regenerated evidence bytes.

## Security boundary

MiMicus does not execute LLM- or database-generated Python/JavaScript/SQL. Runtime falsifier mutations are validated declarative data over trusted source-controlled primitives. Out-of-tree plugins require an explicit allow-listed path and SHA-256 match. See `SECURITY.md`, `docs/THREAT_MODEL.md`, `docs/K3_SEED_LINEAGE.md`, `docs/AGENT_IDENTITY.md`, and `docs/RESEARCH_LINEAGE.md`.

## Evidence history

Historical ORDER-002 through ORDER-007 evidence remains committed under `evidence/ORDER-00X/` for provenance. ORDER-008 acceptance is based on the normal production core and current exact-head CI/evidence under `evidence/ORDER-008/`; a legacy/fixture compatibility test is not treated as production-runtime proof.

## License

MIT. See `LICENSE` and `THIRD_PARTY_NOTICES.md`.
