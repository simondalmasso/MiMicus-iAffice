# Mimicus Commercial Conversion Gate V1 — Plan

1. Add commercial stage/context + next-action/domain enums.
2. Extend ingest with optional backward-compatible `commercial`.
3. Rank explicit proposal/qualified stages above raw replies.
4. Add COMPLETE terminal outcome and completed_ids.
5. Emit next_action and commercial_stage in decisions/traces.
6. Add regression tests proving old ledgers keep previous ordering.
7. Run full core + cockpit CI; no deploy.
