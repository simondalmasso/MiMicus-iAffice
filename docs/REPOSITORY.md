# Repository layout

```text
MiMicus-iAffice/
├── core/                 # authoritative Python runtime
│   ├── src/mimicus/
│   ├── tests/
│   ├── alembic/
│   ├── config/
│   ├── docs/
│   └── evidence/
├── public/               # static cockpit
├── worker.js             # Cloudflare Worker edge shell
├── wrangler.toml
├── package.json
├── docs/                 # product/release architecture, plans, research
├── evidence/             # repository-level deployment/integration evidence
├── .github/workflows/    # active CI only
├── STATUS.md
└── README.md
```

## Conventions

- `core/` is active source, not an archive.
- `core/evidence/` preserves historical ORDER evidence.
- `docs/superpowers/` contains approved design and implementation records.
- `docs/research/` contains candidate evaluations; research does not imply adoption.
- root `evidence/` is reserved for combined-repository deployment/integration truth.
- active workflows describe current product behavior; one-time migration workflows do not stay active indefinitely.
- the Worker and UI may observe runtime state but do not duplicate LAYA decision logic.
