# Memory and trust model

## Origin-bound authority

Authority belongs to evidence lineage, not to fluent restatement. A paraphrase or peer repetition inherits at most the minimum authority of its parents. It cannot reset provenance or create a new independent source cluster.

## Four gates

1. **WRITE** — new content becomes `private_verified` only after deterministic verification; otherwise it is quarantined.
2. **RETRIEVAL** — only non-expired, same-domain private/shared verified items are eligible.
3. **PROMOTION** — shared authority requires deterministic verification or at least two verified independent provenance clusters. Repetition of one cluster does not count.
4. **CROSS-AGENT** — private verified memory is visible only to its owner; peers receive only shared verified memory.

States are explicit: `candidate → quarantined | private_verified → shared_verified`, with terminal/restrictive `rejected` and `expired` states.

## Calibration

Calibration is keyed by `agent_fingerprint × domain` and updated only from direct verified outcomes. Cross-domain reputation starts neutral and cannot be laundered into another domain. Three consecutive verified domain canary failures trigger epistemic bankruptcy. Re-entry requires a fresh recovery audition.

## Correlated-error penalty

Provider, model, system-prompt hash and tool-manifest hash define lineage similarity; empirical co-failure can add to it. Correlated agents have lower marginal voting/selection value. A clone is therefore not treated as independent corroboration.
