## Contract

- ROLE:
- BASE_SHA:
- HEAD_SHA:
- OBJECTIVE:
- OWNS:
- MUST_NOT_TOUCH:
- INTEGRATION_OWNER:

## Change

Describe the bounded behavior changed and why.

## Truth / evidence

- Evidence class: `VERIFIED_AT_HEAD | LIVE_OBSERVED | HISTORICAL | UNVERIFIED | SIMULATED_FIXTURE | UNKNOWN`
- CI/run:
- Deployment impact: `NONE | PREVIEW | PRODUCTION`
- Simulation used: `NO | YES (must be explicitly labeled)`

## Verification

- [ ] Focused tests pass on this HEAD.
- [ ] Affected integration tests pass.
- [ ] Ruff passes when Python source changed.
- [ ] mypy passes when typed Python contracts changed.
- [ ] Package build passes when package/runtime changed.
- [ ] Cockpit JS syntax passes when `public/` changed.
- [ ] Wrangler dry-run passes when Worker/deploy config changed.
- [ ] No secret or private fixture data was added.
- [ ] No real-world effect authority was expanded unintentionally.
- [ ] Main drift was checked before merge.
- [ ] Evidence still applies to the final HEAD.

## Findings / residual risk

List unresolved risks. Write `NONE` only when verified.
