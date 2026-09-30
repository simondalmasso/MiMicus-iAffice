# iAffice — Cloudflare deployment

Status: prepared; live deploy still requires an authorized Cloudflare credential path.

## Canonical topology

Deploy order:
1. D1 migrations `0001..0011`
2. `aria-models` private Worker
3. `aria-effects` private Worker
4. Queue / DLQ / Durable Objects / Workflow bindings
5. `agent-os` public Worker + `apps/cockpit`
6. live exact-head acceptance

Public:
- `agent-os.simondalmasso44.workers.dev`

Private:
- `aria-models` with `workers_dev=false`
- `aria-effects` with `workers_dev=false`

## Canonical config files

Source templates:
- `wrangler.core.template.jsonc`
- `wrangler.models.template.jsonc`
- `wrangler.effects.template.jsonc`

Generated, ignored files:
- `.generated/wrangler.agent-os.jsonc`
- `.generated/wrangler.models.jsonc`
- `.generated/wrangler.effects.jsonc`

There is no second generic Wrangler template.

## Required deployment environment

Required:
- `CLOUDFLARE_API_TOKEN` or `CF_API_TOKEN`
- `CLOUDFLARE_ACCOUNT_ID` or `CF_ACCOUNT_ID`
- `CLOUDFLARE_D1_DATABASE_ID`
- `ARIA_HEAD_SHA`

Runtime secrets are installed through Wrangler/Cloudflare secret bindings, never committed:
- `ADMIN_TOKEN_HASH`
- `APPROVAL_SIGNING_KEY`
- `WEBHOOK_SECRET`
- `EXECUTOR_SIGNING_KEY`

External model-provider keys are optional at deploy time. A provider route remains disabled until its independent zero-cost/privacy/evidence gates pass.

## Commands

```bash
npm run deploy:preflight
npm run deploy:config
npm run deploy:cloudflare
```

`deploy:preflight` checks topology and Cloudflare deployment authorization without printing secret values.

`deploy:config` renders configs under `.generated/`.

`deploy:cloudflare`:
- verifies the exact Git SHA;
- applies remote D1 migrations;
- deploys private model/effect Workers first;
- deploys `agent-os` last.

## Live acceptance

After deploy verify:
- `GET /api/health` returns 200, `service=iAffice`, `worker=agent-os`, exact SHA;
- cockpit HTML loads instead of the old text placeholder;
- Global Core, Operations, Discovery, Demos, Executors, Telemetry APIs answer;
- desktop/mobile smoke passes;
- internal Workers have no public workers.dev endpoints;
- no billable execution attempt occurred.

Compute-provider live acceptance is a separate gate from basic application deployment.

Do not call deployment PASS if credentials are missing, migrations are unapplied, exact SHA differs, or the hostname still serves a placeholder.
