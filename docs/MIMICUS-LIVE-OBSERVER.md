# Mimicus Live Commercial Observer V1

This mode is local, read-only and zero-mandatory-cost.

It shows the real commercial decision trace:

`lead_ingested -> laya_reading -> decision_emitted -> batch_complete`

The browser does not decide. LAYA / `MiMicusEngine` remains authoritative.

## Windows / PowerShell

From the repository root:

```powershell
py -3.12 -m pip install -e ".\core[dev]"

$env:MIMICUS_DATABASE_URL = "sqlite:///:memory:"

mimicus observe `
  --ledger-url "https://raw.githubusercontent.com/simondalmasso/MiMicus-iAffice/main/data/gpt-prospectos.json" `
  --policy-file ".\core\config\commercial-policy-v1.json" `
  --cockpit-dir ".\public" `
  --host 127.0.0.1 `
  --port 8788 `
  --poll-seconds 5
```

Open:

`http://127.0.0.1:8788/`

The observer binds only to loopback. V1 intentionally rejects `0.0.0.0`.

## Local-file mode

If the canonical ledger is already present locally:

```powershell
mimicus observe `
  --ledger-file ".\data\gpt-prospectos.json" `
  --policy-file ".\core\config\commercial-policy-v1.json" `
  --cockpit-dir ".\public"
```

## What the Activity Stream shows

- **SETTER / lead_ingested** — lane, prospect ID, outreach state, setter score.
- **LAYA / laya_reading** — commercial stage, evidence count/match, policy version, risk and active state. Evidence content and source references are not emitted.
- **LAYA / decision_emitted** — `WORK_NOW`, `HOLD`, `REPAIR_DATA` or `REJECT`, stage and explicit reasons.
- **SISTEMA / batch_complete** — batch hash and work/hold/repair/reject counts.
- **SISTEMA / observer_error** — observer/source degradation only.

The trace is sanitized structured telemetry. It is not hidden chain-of-thought.

## Authority and side effects

V1 has no endpoint that can command LAYA.

It has no POST/PUT/PATCH/DELETE API.

It does not:
- send a Facebook/Reddit message;
- modify the canonical setter ledger;
- trigger browser automation;
- deploy the Worker;
- expose the Python core publicly.

The observer fails open with respect to decision authority: if the viewer breaks, the LAYA decision remains unchanged.

## Source freshness

Remote URL mode performs read-only polling. CDN/network caching may add some delay relative to the exact Git commit time. The decision engine only emits a new batch when the canonical JSON payload hash changes.

Local-file mode reflects file changes on the next poll and is the lowest-latency path.

## Stop

Use `Ctrl+C`.

No external state needs cleanup.
