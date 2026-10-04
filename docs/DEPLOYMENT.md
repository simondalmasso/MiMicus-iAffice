# Deployment and release gates

MiMicus separates **release readiness** from **deployment**. A green core does not automatically authorize production.

## Gate A — Python core

From `core/`:

```bash
python -m pip install -e ".[dev]"
pytest --cov=mimicus --cov-report=term-missing
ruff check src tests
mypy src/mimicus
python -m build
```

Required:

- all tests pass;
- coverage >= 90%;
- Ruff PASS;
- mypy PASS;
- build PASS.

## Gate B — cockpit

From repository root:

```bash
node --check public/app.js
npx wrangler deploy --dry-run
```

The Worker remains observational. No production route may provide command ingress into LAYA.

## Gate C — local live observer

Use a representative prospect ledger and explicit policy.

Required flow:

```text
lead_ingested
-> laya_reading
-> decision_emitted
-> batch_complete
```

The same authoritative decision path must be used by CLI and observer.

Observer failure must not alter LAYA decisions.

## Gate D — effects

Before any real effect adapter is enabled:

- adapter identity must match the approved envelope;
- destination/resource/operation/payload/scope tampering must deny;
- approval must be active, unexpired and unconsumed;
- concurrent use must permit at most one dispatch;
- uncertain outcome must become UNKNOWN and must not blind-retry.

The current release contains the boundary, not autonomous effect adapters.

## Gate E — release

Only after A-D pass:

1. review branch diff;
2. confirm no unrelated historical files are introduced;
3. update the default branch;
4. optional preview deployment;
5. production deployment only after preview health/UI verification.

## Rollback

The existing deployed cockpit can remain unchanged while this release branch is audited. Repository consolidation does not require an immediate Worker deployment.
