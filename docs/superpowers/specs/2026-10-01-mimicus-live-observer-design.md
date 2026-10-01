# Mimicus Live Commercial Observer V1 — Design

**Date:** 2026-10-01
**Branch:** `aud-arq/mimicus-live-observer-v1`
**Base checkpoint:** `aud-arq/mimicus-lead-decision-v1@8cd1d3e90c4ee27fcbae059ad67c24a068bd3fa4`

## Goal

Show, in real time and in the existing Mimicus cockpit:

`lead_ingested -> laya_reading -> decision_emitted -> batch_complete`

without giving the UI, Worker, browser, or observer any authority over LAYA.

## Authority

- LAYA / `MiMicusEngine` remains the only decision authority.
- The observer is read-only.
- Trace events expose structured factors and decisions, never hidden chain-of-thought.
- Observer failure must not alter or block authoritative decisions.
- No external outreach or setter-ledger mutation is allowed.

## V1 topology

```text
Facebook / Reddit setters
          |
          v
canonical JSON ledger
  local file OR public HTTPS URL
          |
          v
CommercialObserver (local)
          |
          v
MiMicusEngine.triage_prospects()
          |
          +--> sanitized trace buffer
          |
          +--> authoritative LeadDecisionBatch
                    |
                    v
        localhost /api/activity
                    |
                    v
          existing Mimicus cockpit
```

## Runtime

A new CLI mode:

```bash
mimicus observe \
  --ledger-url <public HTTPS JSON> \
  --policy-file policy.json \
  --cockpit-dir public \
  --host 127.0.0.1 \
  --port 8788 \
  --poll-seconds 1
```

Alternative:
`--ledger-file <path>`.

Exactly one ledger source is required.

## Security / effects

- Bind only to loopback in V1: `127.0.0.1`, `localhost`, or `::1`.
- URL source must be HTTPS.
- No credentials are accepted.
- No POST/PUT/DELETE endpoints.
- No command endpoint to LAYA.
- No browser automation.
- No Worker-to-LAYA ingress.
- Remote ledger fetch is read-only.
- The observer never writes canonical setter state.

## Activity API

`GET /api/activity?since=<cursor>`

Returns:

```json
{
  "cursor": 7,
  "events": [...]
}
```

Events:
- `lead_ingested`
- `laya_reading`
- `decision_emitted`
- `batch_complete`

The API is append-only in memory and capped to a bounded recent history.

Additional compatibility endpoints:
- `GET /api/health`
- `GET /api/runtime`

Everything else is static cockpit content from `--cockpit-dir`.

## Poll behavior

- Poll source on an explicit interval.
- Canonicalize/hash the ledger payload.
- If content hash is unchanged, emit nothing.
- If changed, use a timezone-aware runtime clock and invoke LAYA once for that snapshot.
- Trace sequence is monotonically increasing inside the observer process.
- Source fetch/parse errors become non-authoritative `observer_error` diagnostics and do not mutate decisions.

## UI behavior

`public/app.js` first probes `/api/runtime`.

If runtime mode is `local-live-observer`:
- disable simulated activity generation;
- poll `/api/activity`;
- render live setter/LAYA events;
- show `LIVE LAYA` status.

Otherwise:
- preserve current simulation-safe fallback.

The JavaScript never recreates decision rules.

## Non-goals

- production cloud stream;
- D1/KV;
- Worker write endpoints;
- remote commands;
- effect authorization;
- autonomous outreach;
- replacing the Cloudflare deployment.

A cloud read-model can be a later adapter only after the effect boundary is implemented.
