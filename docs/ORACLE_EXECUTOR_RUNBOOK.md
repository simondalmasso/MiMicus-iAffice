# ORDER-004 — Oracle Free Tier executor / runner runbook

Status: **PREPARED / NOT YET CONNECTED / DO NOT USE SIMON'S PC**

This runbook is the exact cloud-only continuation for the existing Oracle target.

## Existing Oracle target

Known prior infrastructure:
- host label: `senex-order076-collector`
- public IP: `163.176.62.212`
- private IP: `10.240.1.248`
- internal FQDN: `senex-order076-collector.trial.senex015.oraclevcn.com`
- region: `sa-saopaulo-1`
- known shape from prior work: `VM.Standard.E2.1.Micro`
- SSH access had already been verified with the existing identity/key named `ORDER076`.

Hard constraints:
- do **not** generate another SSH key;
- do **not** create another remote-control account/control plane;
- do **not** use Simon's Windows PC as runner/executor;
- SentinelX remains break-glass only for this Oracle path;
- do not guess the SSH username: resolve it from the existing `ORDER076` SSH configuration/history.

## Roles

Cloudflare remains canonical:
- D1 = canonical business state/memory;
- Queue = job dispatch;
- `agent-os` = public control plane;
- `aria-models` = internal model boundary;
- `aria-effects` = internal external-write boundary.

Oracle is non-canonical:
- typed job executor;
- optional GitHub self-hosted verification runner;
- local artifact/cache/replay state only;
- no business-state authority;
- no direct business external-write credentials;
- no model/provider billing credentials unless separately authorized later.

## Repository

Repository:
`https://github.com/simondalmasso/the-iAffice`

Branch:
`order-004-sniper-autonomous-revenue-engine-v1`

Always fetch the current branch HEAD before installing. Never reuse a stale SHA from this document.

## 1. Obtain an authorized shell on the existing Oracle VM

Use the existing `ORDER076` identity and existing SSH configuration.

Do not create a new key.

Before mutation, confirm:
```bash
hostname
uname -a
id
python3 --version
git --version
df -h
```

Expected hostname:
`senex-order076-collector`

If the hostname/identity does not match, stop.

## 2. Check out the exact ORDER-004 branch

Use a clean dedicated checkout such as `/opt/iaffice`.

```bash
sudo mkdir -p /opt/iaffice
sudo chown "$USER":"$USER" /opt/iaffice
git clone https://github.com/simondalmasso/the-iAffice /opt/iaffice
cd /opt/iaffice
git fetch --all --prune
git checkout order-004-sniper-autonomous-revenue-engine-v1
git pull --ff-only
git rev-parse HEAD
```

Record the exact HEAD as evidence.

## 3. Run executor self-test before installing a service

```bash
cd /opt/iaffice
python3 scripts/oracle_executor_selftest.py
```

Required:
- exit 0;
- `ok=true`;
- `arbitraryShell=false`;
- private artifacts generated;
- HMAC artifact auth self-test passes.

Do not start the service on failure.

## 4. Install the hardened executor service

```bash
cd /opt/iaffice
sudo bash scripts/install_oracle_executor.sh
```

This:
- creates a dedicated `iaffice` service user if needed;
- creates `/var/lib/iaffice-executor`;
- installs the hardened systemd unit;
- creates `/etc/iaffice/executor.env` only if absent;
- enables but does not start the service.

It intentionally does not invent or persist secrets.

## 5. Configure the shared executor HMAC secret

Generate one strong random secret in an authorized secure environment.

The exact same value must be installed:
- in Cloudflare `agent-os` as secret `EXECUTOR_SIGNING_KEY`;
- on Oracle as `IAFFICE_EXECUTOR_SIGNING_KEY`.

Never commit or print it in logs/checkpoints.

Oracle file:
`/etc/iaffice/executor.env`

Also set:
```
IAFFICE_CORE_CALLBACK_URL=https://agent-os.simondalmasso44.workers.dev/api/sniper/executor/result
```

Keep:
```
IAFFICE_EXECUTOR_BIND=127.0.0.1
IAFFICE_EXECUTOR_PORT=8788
IAFFICE_EXECUTOR_ROOT=/var/lib/iaffice-executor
```

## 6. Provide a stable HTTPS origin for Oracle

The executor itself listens only on localhost.

Use an authorized hostname you control and terminate valid HTTPS in front of:
`127.0.0.1:8788`

A Caddy template exists:
`apps/oracle-executor/Caddyfile.example`

Requirements:
- valid HTTPS certificate;
- stable hostname;
- request body cap <= 512 KiB;
- no public artifact directory/listing;
- only the executor HTTP service is proxied;
- network/firewall does not expose unrelated Oracle services.

Do not register the executor in D1 until this HTTPS endpoint is working.

## 7. Start and verify Oracle executor

```bash
sudo systemctl start iaffice-executor
sudo systemctl status iaffice-executor --no-pager
curl --fail --silent http://127.0.0.1:8788/health
curl --fail --silent https://EXECUTOR_HOSTNAME/health
```

Required health facts:
- `ok=true`;
- `executorId=ORACLE_FREE_EXECUTOR`;
- `canonicalState=false`;
- `arbitraryShell=false`;
- `artifactAccess=HMAC_TIME_BOUND`;
- `discoveryAdapter=DISABLED_FAIL_CLOSED`.

`heavy3dToolchain` may be false. That is not a failure; it means heavy 3D remains fail-closed until Blender is installed and verified.

## 8. Verify zero-cost eligibility before enabling

Do not trust a request field claiming "$0".

Collect evidence that this exact Oracle resource is within the user's legitimate free allocation and not accruing billable overage.

Then call the protected core API:

```http
POST /api/sniper/executors/verify
Authorization: Bearer <ADMIN TOKEN>
Content-Type: application/json
```

Body:
```json
{
  "executorId": "ORACLE_FREE_EXECUTOR",
  "endpoint": "https://EXECUTOR_HOSTNAME",
  "costClass": "FREE_USER_CONFIRMED",
  "zeroCostVerified": true,
  "health": "HEALTHY",
  "evidenceRefs": [
    "oracle:free-tier:<evidence-id>",
    "executor-health:<evidence-id>"
  ],
  "lastHealthAt": "<ISO8601>"
}
```

The endpoint must be the HTTPS origin root with no credentials/query/fragment/path.

Admission must become:
`ENABLED`

## 9. Bootstrap Oracle as the only ORDER-004 CI runner

The workflow is restricted to:
```yaml
runs-on: [self-hosted, linux, oracle-free, iaffice]
```

Therefore Simon's Windows self-hosted machine cannot receive ORDER-004 verification jobs.

Obtain a short-lived GitHub runner registration token through an authorized GitHub UI/API path.

Do not commit it.

On Oracle:
```bash
cd /opt/iaffice
sudo env GITHUB_RUNNER_TOKEN='<EPHEMERAL TOKEN>' \
  bash scripts/bootstrap_oracle_runner.sh
```

The bootstrap:
- detects x64 vs arm64;
- resolves latest GitHub Actions runner release;
- requires GitHub's SHA-256 asset digest;
- rejects missing/mismatched digest;
- registers labels `oracle-free,iaffice`;
- installs/starts the runner service.

## 10. Run exact-head ORDER-004 verification

Dispatch the existing workflow only after the Oracle runner is online.

Required commands/gates:
- `npm ci --offline --ignore-scripts`
- `npm run typecheck`
- `npm test`
- `npm run test:coverage`
- `npm run e2e`
- `npm run e2e:compute`
- `npm run benchmark`
- `npm run benchmark:compute`
- `npm run chaos:compute`
- `npm run security`
- `python3 scripts/oracle_executor_selftest.py`
- `npm run doctor:004`
- `python scripts/ui_smoke_order004.py`

Do not claim PASS until workflow evidence exists for the exact current HEAD.

## 11. Cloudflare deployment order after exact-head PASS

1. Render generated configs:
```bash
CLOUDFLARE_D1_DATABASE_ID='<id>' \
ARIA_HEAD_SHA="$(git rev-parse HEAD)" \
npm run deploy:config
```

2. Apply D1 migrations `0001..0012`.

3. Verify/create Queue + DLQ.

4. Verify Durable Objects:
- `AriaCoordinator`
- `ComputeGovernorDO`

5. Verify Workflow:
- `BusinessWorkflow`

6. Install core secrets without committing values:
- `ADMIN_TOKEN_HASH`
- `APPROVAL_SIGNING_KEY`
- `WEBHOOK_SECRET`
- `EXECUTOR_SIGNING_KEY`

7. Deploy internal services first:
- `aria-effects`
- `aria-models`

8. Deploy public:
- `agent-os` + `apps/cockpit`

9. Verify live exact SHA and APIs.

## 12. Live acceptance after deployment

Required:
- `GET /api/health` → 200 and exact SHA;
- `GET /api/sniper/global`;
- `GET /api/sniper/operations`;
- `GET /api/sniper/discovery/sources`;
- `GET /api/sniper/demos`;
- `GET /api/sniper/executors`;
- `GET /api/sniper/telemetry`;
- desktop 1440x900;
- mobile 390x844;
- console errors = 0;
- no billable execution attempt.

Then run exactly one real private demo job through Oracle:
`CASE → Demo Job → Queue → signed Oracle job → signed callback → artifact manifest → private artifact proxy → AUD`

The private artifact path is:
`GET /api/sniper/executor/artifact/:runId/:name`

It requires admin bearer auth. The core:
- validates D1 ownership;
- signs a 5-minute Oracle artifact GET;
- enforces 15 MB proxy cap;
- verifies SHA-256 against the durable demo manifest;
- returns `no-store`.

## Stop conditions

Stop and mark BLOCKED instead of weakening controls if:
- Oracle is not the expected existing VM;
- access would require a new key/account/control plane;
- free-tier status cannot be evidenced;
- executor health is degraded/unknown;
- HTTPS is not valid;
- shared HMAC secret is missing;
- exact-head tests fail;
- Cloudflare credentials/bindings are unavailable;
- any path would require Simon's PC.

## Commercial action gate remains in Cloudflare

Oracle builds private demo artifacts only. It does not send prospect messages, create payment requests, deploy customer work or own contact policy.

All CASE-linked external commercial actions remain:
`agent-os commercial guard → ActionIntent → action-bound approval → aria-effects commercial revalidation → adapter`.

The Oracle executor receives no business-write credentials.
