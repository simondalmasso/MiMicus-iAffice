# Mimicus Causal Replay V1 — Design

**Date:** 2026-10-03
**Branch:** `aud-arq/mimicus-causal-replay-v1`
**Base:** `aud-arq/mimicus-effects-v1@d8814b88295a36ab8bc2b86a5ca6ad3098f56a39`

## Goal

Extend the existing semantic replay contract so Mimicus can prove the causal execution contract of a successful Morphology DAG without requiring byte-identical runs.

## Principle

Replay equivalence is semantic, not incidental.

The causal hash MUST bind:
- exact `plan_hash`;
- node identity and kind;
- declared DAG prerequisites;
- declared node `input_hash`;
- exact prerequisite output hashes observed for that node;
- exact node output hash;
- semantic completion state;
- policy/effect decisions when such decisions are part of the run.

The causal hash MUST NOT bind:
- run UUID;
- event UUID;
- wall-clock timestamps;
- node duration;
- scheduler turn number;
- observed wall time;
- incidental completion order between causally independent nodes.

## Causal record

A successful execution stores:

```text
causal_execution
  semantic
    version
    plan_hash
    nodes[]
    effect_decisions[]
  semantic_hash
  incidental
    run_id
    scheduler_schedule
```

Each node semantic record contains:

- `node_id`
- `kind`
- `prerequisites`
- `declared_input_hash`
- `prerequisite_output_hashes`
- `causal_input_hash`
- `output_hash`
- `status = COMPLETED | PRECOMPLETED`

`causal_input_hash` is the canonical hash of the declared input hash plus exact prerequisite output hashes.

## Verification

`verify_causal_execution(record)` fails when:

- semantic hash differs;
- node IDs are duplicated;
- prerequisite references are missing;
- DAG contains a cycle;
- a prerequisite output hash differs from the parent node's recorded output hash;
- a node output hash is absent/invalid;
- causal input hash does not recompute;
- required V1 fields are malformed.

Incidental material is ignored by the verifier.

## Existing semantic replay integration

The production semantic snapshot becomes V2 and includes only the **semantic** causal projection plus its expected hash.

Existing semantic replay continues to verify:
- ledger chain;
- semantic input hash;
- evidence projections;
- claim identities;
- falsifier re-execution;
- synthesis decision hash;
- plan hash.

It additionally returns `causal_contract_verified`.

V1 persisted semantic snapshots remain readable: causal verification is reported unavailable but does not retroactively invalidate the older contract.

## Effect decisions

V1 execution has no autonomous external effects. The causal schema nevertheless includes `effect_decisions: []`.

Future effect integration must insert sanitized semantic policy evidence such as envelope/policy hashes and authorization/outcome state. Raw credentials and incidental approval IDs must not become required for semantic equivalence.

## Clock / ID seam

`EventLedger` receives injectable:
- `clock: Callable[[], datetime]`
- `id_source: Callable[[], str]`

Production defaults remain current UTC time + uuid4.

This seam exists to test incidental metadata explicitly. It does not claim a full run is byte-identical.

## Non-goals

- new event platform;
- event sourcing rewrite;
- deterministic provider re-execution for live providers;
- remote effects;
- retries;
- replacing current semantic replay;
- forcing identical timing/scheduler completion order.
