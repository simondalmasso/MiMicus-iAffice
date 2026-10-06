# Deployment and release gates

MiMicus separates **repository readiness**, **release readiness** and **deployment**.

A green core does not automatically authorize production.

## Gate A — Python core

From `core/`:

```bash
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
python -m pip check
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
npx --yes wrangler@4.134.0 deploy --dry-run
```

The Worker remains observational. No production route may provide command ingress into LAYA.

## Gate C — local live observer

Use the sanitized `core/fixtures/commercial-observer-demo.json` first, then a representative current setter ledger supplied explicitly at runtime.

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

## Gate E — repository transition

Completed:

- active runtime promoted to `core/`;
- obsolete migration workflows retired;
- canonical `main` replaced with the verified product state;
- previous `main` preserved under `legacy/main-setters-radar-2026-10-03`.

## Gate F — deployment

Still intentionally pending:

1. exact-head CI on canonical `main`;
2. optional preview deployment;
3. preview health/UI verification;
4. explicit production release decision;
5. production deployment.

## Rollback

The earlier deployed cockpit remains unchanged until an explicit production deployment occurs.

Repository consolidation by itself does not alter the live Worker.
