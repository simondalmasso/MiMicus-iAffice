# Commercial data contract

This contract defines the boundary between prospect sources/setters and the authoritative MiMicus commercial decision path.

Sources report **observations**. They do not decide priority, disposition, next action, approvals or external effects.

## Ledger envelope

The input document is:

```json
{
  "findings": []
}
```

Each finding is normalized into a frozen `LeadCandidate`.

## Required prospect fields

A usable row includes:

- `id` — stable prospect identifier;
- `title`;
- `sourceName` — currently `Facebook` or `Reddit`;
- `publishedAt` — timezone-aware;
- `verifiedAt` — timezone-aware;
- `active` — required boolean;
- `scamRisk` — `low|medium|high`;
- `rank.score` — source/setter signal in `0..100`;
- `outreach.status`;
- `outreach.channel`.

For actionable closer work, the row should also contain:

- `buyer`;
- `sourceUrl`;
- `directUrl`;
- `argentinaEligible`;
- `workerFee`.

Missing decision-critical metadata can produce `REPAIR_DATA`.

## Outreach state

Supported operational states include:

- `prepared`;
- `contacted`;
- `replied`;
- `closed`.

A contacted row must include timezone-aware `outreach.contactedAt`. LAYA determines whether follow-up is due from the explicit policy threshold. Sources do not set `CONTACTED_DUE` themselves.

## Commercial stage

Optional object:

```json
{
  "commercial": {
    "stage": "proposal",
    "updatedAt": "2026-10-05T03:00:00-03:00",
    "evidence": [
      {
        "stage": "proposal",
        "observedAt": "2026-10-05T02:55:00-03:00",
        "sourceRef": "thread-or-crm-reference",
        "summary": "Optional short operator note."
      }
    ]
  }
}
```

Stages:

- `unknown`;
- `discovery`;
- `qualified`;
- `proposal`;
- `won`;
- `lost`.

### Evidence rule

The elevated stages `qualified`, `proposal`, `won` and `lost` require at least one matching evidence row whose `stage` equals the asserted current stage and whose `observedAt` is not later than the decision `as_of`.

Missing, mismatched or future-dated evidence fails closed to `REPAIR_DATA`; it does not gain priority.

Evidence is bound into the candidate/decision hashes.

## Authority boundary

Source/setter fields are observations only.

A source/setter must **not** provide or manufacture:

- `LeadDisposition`;
- `LeadStage`;
- `LeadNextAction`;
- `rank_position`;
- `decision_hash`;
- `batch_hash`;
- `CommercialActionTicket`;
- `CommercialActionGoal`;
- `EffectApprovalReceipt`;
- effect intent/outcome state.

LAYA / `DeterministicLeadDecisionService` derives decision state.

## Closer source brief

MiMicus preserves a bounded subset of source observations so the human/closer receives enough context to act on a `WORK_NOW` decision:

- `company`;
- `location`;
- `description` → `source_brief.need`;
- `category`;
- `applicationMode`;
- `salary.raw` → `source_brief.compensation_raw`;
- `rank.reason` → `source_brief.setter_reason`.

These values are **context, not authority**.

They do not change `LeadStage`, `CommercialStage`, `LeadDisposition`, `LeadNextAction`, rank precedence or effect approval. They are bounded/frozen observations carried into the deterministic `CommercialActionTicket` and are included in its hash so later mutation is detectable.

The live sanitized LAYA trace does not emit this brief. Future model-assisted drafting must continue to treat it as untrusted source content rather than system instructions.

## Closer handoff

For every authoritative `WORK_NOW` decision, MiMicus creates one deterministic `CommercialActionTicket`.

The ticket carries the contact target, authoritative `next_action`, and one deterministic `goal` describing the observable transition that counts as success.

Goal mapping is derived only by `DeterministicLeadDecisionService`:

- `CONTACT` / pre-proposal `FOLLOW_UP` → obtain a reply;
- `QUALIFY` → reach `qualified` with matching stage evidence;
- `PROPOSE` → reach `proposal` with matching stage evidence;
- proposal `FOLLOW_UP` → resolve to `won` or `lost` with matching outcome evidence.

The goal is included in `ticket_hash` and therefore in the batch hash. Source/setter input cannot supply it.

The ticket remains a handoff contract, not action authority:

- it is **not** permission to send;
- it always declares `requires_human_approval=true`;
- success criteria do not grant stage authority;
- any real external mutation still requires the independent exact-envelope effect approval boundary.

## Funnel measurement

`mimicus funnel` consumes the same ledger + policy + explicit `as_of` and returns a read-only `CommercialFunnelSnapshot`.

It measures:

- current commercial stages;
- dispositions and next actions;
- qualified → proposal progression;
- proposal → terminal progression;
- median transition latency;
- won/lost counts and terminal win rate.

Calibration rows are deliberately sanitized: buyer names, titles, URLs, evidence references/summaries and commercial free text are excluded.

## Example lifecycle

```text
setter/source observation
        |
        v
prepared
        |
        v
LAYA: CONTACT
        |
        v
contacted ---- wait/due policy ----> FOLLOW_UP
        |
        v
replied
        |
        v
LAYA: QUALIFY
        |
        v
qualified + matching evidence
        |
        v
LAYA: PROPOSE
        |
        v
proposal + matching evidence
        |
        v
LAYA: FOLLOW_UP
        |
        +--> won + evidence
        |
        +--> lost + evidence
```

The system does not infer a successful commercial stage merely from free text.
