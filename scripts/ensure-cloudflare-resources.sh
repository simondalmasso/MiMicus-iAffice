#!/usr/bin/env bash
set -Eeuo pipefail

: "${CLOUDFLARE_D1_DATABASE_ID:?CLOUDFLARE_D1_DATABASE_ID required}"

WRANGLER_VERSION="${WRANGLER_VERSION:-4.122.0}"
CORE=".generated/wrangler.agent-os.jsonc"
MAIN_QUEUE="ariaos-events-v1"
DLQ="ariaos-events-v1-dlq"

test -f "$CORE" || { echo "GENERATED_CORE_CONFIG_REQUIRED:$CORE" >&2; exit 50; }

D1_JSON="$(npx --yes "wrangler@$WRANGLER_VERSION" d1 list --json --config "$CORE")"
printf '%s' "$D1_JSON" | node --input-type=module -e '
let raw="";
for await (const chunk of process.stdin) raw+=chunk;
const parsed=JSON.parse(raw);
const rows=Array.isArray(parsed)?parsed:(parsed.result??parsed.databases??[]);
const expected=process.env.CLOUDFLARE_D1_DATABASE_ID;
const row=rows.find(x=>String(x.uuid??x.id??x.database_id??"")===expected);
if(!row){console.error("D1_DATABASE_ID_NOT_FOUND:"+expected);process.exit(51)}
const name=String(row.name??row.database_name??"");
if(name!=="ariaos-v1"){console.error("D1_NAME_MISMATCH:"+name);process.exit(52)}
console.log("D1_OK:"+name);
'

ensure_queue(){
  local name="$1"
  if npx --yes "wrangler@$WRANGLER_VERSION" queues info "$name" --config "$CORE" >/dev/null 2>&1; then
    echo "QUEUE_OK:$name"
  else
    npx --yes "wrangler@$WRANGLER_VERSION" queues create "$name" --message-retention-period-secs 86400 --config "$CORE"
    echo "QUEUE_CREATED:$name"
  fi
}

ensure_queue "$DLQ"
ensure_queue "$MAIN_QUEUE"

echo "CLOUDFLARE_RESOURCES_READY"
