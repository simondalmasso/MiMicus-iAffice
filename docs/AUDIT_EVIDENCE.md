# Audit evidence

All ORDER-002 artifacts live in `evidence/ORDER-002/` and include a taxonomy, timestamp and exact code HEAD used for deterministic validation. No `ASSUMPTION` or `UNKNOWN` artifact can satisfy a DONE gate.

Gate mapping:

- G0 legacy cleanup: `legacy-cleanup.json`.
- G1 build/reproducibility: `run-metadata.json`, `tests.json`, `migrations.json`.
- G2 zero cost: `platform-baseline.json`, `model-baseline.json`, `cost-guard.json`, `quota-simulation.json`.
- G3 memory/ledger: `ledger-verification.json`, `replay.json`, `tamper-test.json`.
- G4 agent system and G5 policy: reference E2E + `policy-matrix.json`.
- G6 autonomy: tests/migrations/config plus scheduler/workflow evidence.
- G7 cockpit: `ui-smoke.json`.
- G8 connectors: test evidence/security suite.
- G9 reference E2E: `reference-e2e.json`.
- G10 live E2E: `live-deploy.json`, `live-e2e.json` only when truly deployed.
- G11 security: `security.json`.
- G12 10x: `benchmark.json`.
- G13 exact head: `final-gates.json`, with no subsequent code-changing commit.

A blocked live gate is recorded as blocked, not converted to PASS.

## Amendment A1 hard evidence

`tests/effects.test.mjs`, `scripts/architecture-guard.mjs`, `action_intents` / `effect_receipts`, and the reference E2E prove the binding amendment: no agent direct write, no agent write credentials, no effect path outside the gateway, digest-bound approvals, stale-policy/precondition denial, replay denial, duplicate-delivery exact-once behavior, crash recovery and quota retry without paid fallback. `aria-core` and `aria-effects` configs are independently inspected by preflight/security evidence.
