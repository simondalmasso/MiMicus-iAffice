# Operations

Four idempotent schedules: `business_tick` every 15 minutes, `daily_ceo` at 14:00 UTC weekdays, `nightly_memory` at 06:00 UTC daily, and `weekly_security` at 10:00 UTC Sunday. Tasks receive deterministic IDs from job+slot, so duplicate scheduled delivery does not create duplicate work.

Queue consumers retry failures with a 30-second delay and a five-retry DLQ boundary. Durable Workflows checkpoint steps; protected flows can wait up to 15 minutes for a human approval event. Quota pressure must mark/defer work before dropping it.

Health surfaces: `/api/health`, `/api/system/budget`, `/api/system/policy`, `/api/state`. A readiness health 200 requires admin/approval/webhook secrets plus Coordinator, Workflow, and private `EFFECTS` Service Binding. No secret value is returned.
