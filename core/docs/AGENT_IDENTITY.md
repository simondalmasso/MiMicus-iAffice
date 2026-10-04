# Agent identity, lineage and probation

MiMicus separates an exact `agent_fingerprint` from `agent_lineage_id`.

The exact fingerprint identifies one concrete provider/model/prompt/tool-policy identity. Direct calibration and positive trust are attached to the exact fingerprint plus domain. Positive reputation is never copied automatically to a new fingerprint.

A lineage groups declared/known revisions with provider, model family, phenotype, tool-policy descriptor, optional parent fingerprint and revision provenance. Lineage is not a global provider ban: an unrelated identity starts neutral and must earn direct evidence.

Negative unresolved safety state cannot be erased by a cosmetic revision. If a predecessor in a known lineage is BANKRUPT in a domain, a new declared fingerprint in that lineage enters PROBATION before coalition selection. PROBATION excludes it from normal routing. Recovery requires a dedicated verified recovery audition; only a passed recovery audition returns the exact fingerprint to ACTIVE.

The repository persists fingerprint manifests, lineage records, membership/ancestry, direct domain calibration, bankruptcy/probation state and timestamps. Stable identity manifest hashes exclude creation wall time so reopening the same identity in a later process does not create false tamper alarms.

This policy protects against known-lineage whitewashing while avoiding unsupported guilt by association across an entire provider or model family.
