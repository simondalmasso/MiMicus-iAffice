# Divergent branch audit — 2026-10-06

Canonical comparison base: `main@2fafc150a3d2341fd562e3754a417ad20e7c8d8b`.

Purpose: make branch state explicit without deleting history or treating divergent historical branches as integration sources.

## Superseded implementation branches

These branches contain unique commits relative to current `main`, but their semantic work has been implemented, hardened, or superseded on canonical `main`. They are **not integration sources**:

- `arq/commercial-action-goal-v1`
- `aud-arq/mimicus-capability-review-v1`
- `aud-arq/mimicus-closer-brief-v1`
- `aud-arq/mimicus-closer-handoff-v1`
- `aud-arq/mimicus-conversion-gate-v1`
- `aud-arq/mimicus-nvidia-guardrails-v1`
- `docs/mimicus-commercial-diagnosis-contract`
- `fix/commercial-diagnosis-aud-v1`

Examples of canonical replacements include the current measurable commercial action-goal contract, the fail-closed funnel diagnosis, the current NVIDIA cost/output guardrails and the consolidated CI/security documentation.

## Historical / proposal branches to preserve

These branches are intentionally historical, experimental, or proposal-era material. Their unique commits should not be merged wholesale into the current architecture:

- `grokbot/mimicus-zero-cost-architecture`
- `sonnet55/mimicus-zero-cost-architecture`
- `legacy/main-setters-radar-2026-10-03`
- `order-001-readonly-radar`
- `order-002-ariaos-business-os-v1`
- `order-003-zero-cost-compute-market-v1`
- `order-004-sniper-autonomous-business-engine-v1`
- `order-004-sniper-autonomous-revenue-engine-v1`

The `order-004-sniper-autonomous-revenue-engine-v1` branch includes an old production-deploy workflow for a different runtime topology. Its self-hosted runner, D1 and secret contract do not match current Mimicus and must not be copied wholesale. Only the safe pattern of an explicit manual confirmation + exact-SHA deployment gate was retained for the current Worker workflow.

## Deletion policy

No branch is deleted by this audit.

Deletion remains a separate owner-authorized hygiene action. If deletion is later authorized, only branches proven fully contained and non-historical should be candidates; `legacy/`, `order-*`, release references and research/proposal branches should be preserved unless the owner explicitly chooses otherwise.

## Result

No reviewed divergent branch is a missing canonical runtime blocker. The remaining release blocker is production drift: repository Worker code is newer than the live Workers deployment.
