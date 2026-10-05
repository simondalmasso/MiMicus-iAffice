# MiMicus iAffice

MiMicus iAffice is a governed multi-agent runtime with a monochrome operator cockpit.

The repository has two product surfaces:

- **`core/`** — authoritative Python runtime: LAYA / `MiMicusEngine`, Morphology DAG execution, governed memory, evidence/provenance, commercial lead triage, effect authorization and causal replay.
- **Cockpit** — Cloudflare Worker + static UI at the repository root (`worker.js`, `wrangler.toml`, `public/`).

## Architecture

```text
Evidence / context
      |
      v
LAYA / MiMicusEngine
      |
      v
Morphology DAG
      |
      v
DagExecutor
      |
      +--> governed memory
      +--> falsification / verification
      +--> commercial decision gate
      +--> effect authorization boundary
      |
      v
canonical evidence + causal replay
```

External systems may provide retrieval, model or tool capabilities, but they do not receive orchestration, memory-authority or evidence-authority.

## Current checkpoint

`main` is now the canonical product branch.

The previous default-branch content is preserved intact at:

`legacy/main-setters-radar-2026-10-03`

Current release gates include:

- 243 tests passing
- coverage >= 90%
- Ruff passing
- mypy passing
- Python package build passing
- cockpit JavaScript syntax passing
- Cloudflare Worker dry-run passing
- commercial closer handoff + read-only funnel analytics verified
- optional NVIDIA NIM provider profile available without becoming a mandatory dependency
- no autonomous real-world effect adapter enabled

See [STATUS.md](STATUS.md) for the live checkpoint and [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for release gates.

## Core quick start

```bash
cd core
python -m pip install -e ".[dev]"
pytest --cov=mimicus --cov-report=term-missing
```

Local commercial observer:

```bash
mimicus observe \
  --ledger-file /path/to/prospects.json \
  --policy-file config/commercial-policy-v1.json \
  --cockpit-dir ../public \
  --host 127.0.0.1 \
  --port 8788
```

## Cockpit

```bash
npx wrangler dev
```

The public Worker is observational. It is not a second LAYA control plane.

## Documentation

- [System architecture](docs/ARCHITECTURE.md)
- [Core architecture](core/docs/ARCHITECTURE.md)
- [Threat model](core/docs/THREAT_MODEL.md)
- [Memory trust model](core/docs/MEMORY_TRUST_MODEL.md)
- [Deployment / release gates](docs/DEPLOYMENT.md)
- [Repository layout](docs/REPOSITORY.md)
- [Branch map](docs/BRANCHES.md)
- [Commercial data contract](docs/COMMERCIAL-DATA-CONTRACT.md)
- [Current status](STATUS.md)

## History

The original `MiMicus-swarm` source history was absorbed without squashing from exact source HEAD:

`565407eb1296eae617f5b14b512d2e0cf08c6c02`

Historical ORDER evidence remains under `core/evidence/`.
