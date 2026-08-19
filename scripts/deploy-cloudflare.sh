#!/usr/bin/env bash
set -Eeuo pipefail
: "${ARIA_HEAD_SHA:?ARIA_HEAD_SHA required}"
: "${CLOUDFLARE_D1_DATABASE_ID:?CLOUDFLARE_D1_DATABASE_ID required}"
node scripts/cloudflare-preflight.mjs
node scripts/render-wrangler.mjs
npx --yes wrangler@4.122.0 d1 migrations apply ariaos-v1 --remote --config wrangler.core.generated.jsonc
npx --yes wrangler@4.122.0 deploy --config wrangler.models.generated.jsonc
npx --yes wrangler@4.122.0 deploy --config wrangler.effects.generated.jsonc
npx --yes wrangler@4.122.0 deploy --config wrangler.core.generated.jsonc
