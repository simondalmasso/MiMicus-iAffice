# Repository layout

```text
MiMicus-iAffice/
├── AGENTS.md             # binding multi-agent operating contract
├── core/                 # authoritative Python runtime
│   ├── src/mimicus/
│   ├── tests/
│   ├── alembic/
│   ├── config/
│   ├── docs/
│   └── evidence/         # historical ORDER evidence/provenance
├── public/               # static cockpit
├── worker.js             # Cloudflare Worker edge shell
├── wrangler.toml
├── package.json
├── docs/                 # product architecture/governance/plans/research
├── evidence/             # current combined-repo integration/deployment evidence
├── .github/
│   ├── workflows/        # active CI only
│   └── pull_request_template.md
├── STATUS.md
└── README.md
```

## Sources of truth

- product source: `main`;
- runtime orchestration: `core/`;
- repository governance: `AGENTS.md` + `docs/GOVERNANCE.md`;
- architecture: `docs/ARCHITECTURE.md` and deeper `core/docs/` contracts;
- current checkpoint: `STATUS.md`;
- deployment/release gates: `docs/DEPLOYMENT.md`.

## Conventions

- `core/` is active source, not an archive.
- `core/evidence/` is provenance by default; old ORDER artifacts do not prove current HEAD.
- `docs/superpowers/` contains design/implementation records, not runtime authority.
- `docs/research/` contains candidate evaluations; research does not imply adoption.
- root `evidence/` is reserved for current combined-repository deployment/integration truth.
- active workflows describe current product behavior; one-time migration workflows do not stay active indefinitely.
- the Worker and UI may observe runtime state but do not duplicate LAYA decision logic.
- synthetic datasets and simulated runtime activity must be tagged `SIMULATED_FIXTURE` and kept distinct from live observations.
- generated build output/logs stay out of git unless intentionally retained as durable, exact-head evidence.
