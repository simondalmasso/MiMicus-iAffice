# Memory model

D1 is canonical. The migration creates all ORDER-002 entities: events/event_sources/entities/leads/content/campaign metrics/facts/claims/evidence/knowledge/decisions/tasks/runs/agent runs/scores/model/tool calls/approvals/actions/connectors/cursors/budget/incidents/compactions/audit findings/daily snapshots plus ledger, `action_intents`, `effect_receipts`, and the credential-free `safe_outbound` reference sink.

Lifecycle: `RAW_EVENT → FACT_CANDIDATE → CLAIM → AUDITED → VERIFIED_KNOWLEDGE → SUPERSEDED|EXPIRED|REVOKED`. LLMs do not write verified knowledge directly. Conflicting statements remain separate and become `CONFLICT` rather than overwriting one another. Freshness/expiry is explicit.

`D1StateStore` keeps a restart snapshot for fast reconstruction and also writes normalized projections; immutable source events use `INSERT OR IGNORE`. D1 remains authoritative over Notion mirrors.
