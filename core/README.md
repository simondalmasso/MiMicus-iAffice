# MiMicus Core

`core/` is the authoritative Python runtime for MiMicus iAffice.

Package: `mimicus-swarm`  
Current package version: `0.2.2`  
Python: `>=3.12,<3.15`

## Runtime guarantees

- one LAYA / `MiMicusEngine` control plane;
- executable Morphology DAGs: `solo`, `paired_verify`, `parallel_fanout`, `sparse_graph`, `hierarchical_fanout_fanin`;
- completion-driven DAG scheduling with bounded concurrency and structured cancellation;
- typed evidence, deterministic falsification and provenance-bound synthesis;
- governed memory whose authority is policy-driven rather than similarity-driven;
- deterministic commercial lead triage subordinate to LAYA;
- deny-by-default effect authorization with exact-envelope, one-use receipts;
- causal replay anchored to the append-only event ledger;
- offline/scripted operation with no mandatory model API key.

No autonomous real-world effect adapter is enabled by default.

## Install and verify

```bash
python -m pip install -e ".[dev]"
pytest --cov=mimicus --cov-report=term-missing
ruff check src tests
mypy src/mimicus
python -m build
```

Coverage gate: **90%**.

## Zero-key quick start

```bash
export MIMICUS_DATABASE_URL="sqlite:///mimicus.db"
mimicus db upgrade
mimicus doctor --profile offline
mimicus run \
  --profile offline \
  --task-file fixtures/order008_quickstart.json \
  --budget-usd 0 \
  --max-agents 1 \
  --max-concurrency 1 \
  --depth deep
```

## Commercial triage

```bash
mimicus triage \
  --profile offline \
  --ledger-file /path/to/prospects.json \
  --policy-file config/commercial-policy-v1.json \
  --as-of "2026-10-03T22:00:00-03:00"
```

Live local observer:

```bash
mimicus observe \
  --ledger-file /path/to/prospects.json \
  --policy-file config/commercial-policy-v1.json \
  --cockpit-dir ../public \
  --host 127.0.0.1 \
  --port 8788
```

The observer is read-only and loopback-only. It does not create a second decision engine.

## Security

MiMicus does not execute arbitrary LLM/database-provided source code. Trusted mutation remains declarative. Real effects require a matching durable approval receipt and are denied by default.

See:

- [Architecture](docs/ARCHITECTURE.md)
- [Threat model](docs/THREAT_MODEL.md)
- [Memory trust model](docs/MEMORY_TRUST_MODEL.md)
- [Plugin system](docs/PLUGIN_SYSTEM.md)
- [MCP](docs/MCP.md)

## Evidence

Historical ORDER evidence is retained under `evidence/` for provenance. Current release readiness is determined by exact-head CI plus the root repository release gates.

## License

MIT.
