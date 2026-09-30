#!/usr/bin/env bash
set -Eeuo pipefail

: "${ARIA_HEAD_SHA:?ARIA_HEAD_SHA required}"
: "${CLOUDFLARE_D1_DATABASE_ID:?CLOUDFLARE_D1_DATABASE_ID required}"

CURRENT_SHA="$(git rev-parse HEAD)"
if [[ "$CURRENT_SHA" != "$ARIA_HEAD_SHA" ]]; then
  echo "HEAD_SHA_MISMATCH expected=$ARIA_HEAD_SHA actual=$CURRENT_SHA" >&2
  exit 44
fi

node scripts/cloudflare-preflight.mjs
node scripts/render-deploy-config.mjs
bash scripts/ensure-cloudflare-resources.sh

WRANGLER_VERSION="4.122.0"
CORE=".generated/wrangler.agent-os.jsonc"
MODELS=".generated/wrangler.models.jsonc"
EFFECTS=".generated/wrangler.effects.jsonc"

npx --yes "wrangler@$WRANGLER_VERSION" d1 migrations apply ariaos-v1 --remote --config "$CORE"
npx --yes "wrangler@$WRANGLER_VERSION" deploy --config "$MODELS"
npx --yes "wrangler@$WRANGLER_VERSION" deploy --config "$EFFECTS"
npx --yes "wrangler@$WRANGLER_VERSION" deploy --config "$CORE"

echo "DEPLOYED_HEAD=$ARIA_HEAD_SHA"
echo "PUBLIC_WORKER=agent-os"