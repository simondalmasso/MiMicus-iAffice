# MiMicus iAffice — System architecture

## Product boundary

MiMicus iAffice is one product with two runtime surfaces:

1. **Python control plane in `core/`**
   - LAYA / `MiMicusEngine`
   - Morphology DAG compiler
   - completion-driven `DagExecutor`
   - memory trust and retrieval gates
   - falsification and evidence
   - commercial decision gate
   - effect authorization
   - causal replay

2. **Cloudflare cockpit at repository root**
   - `worker.js`
   - `public/`
   - `wrangler.toml`
   - health/runtime metadata and observational UI

The Worker does not execute the Python engine and does not receive LAYA authority.

## Control flow

```text
inputs / evidence / operator context
              |
              v
        LAYA / MiMicusEngine
              |
              v
        Morphology compiler
              |
              v
         canonical DAG
              |
              v
          DagExecutor
       /       |        \
      v        v         v
  memory   falsifiers   agents
      \        |        /
              v
         synthesis
              |
              v
 evidence ledger + causal replay
```

## Commercial flow

```text
setter/source ledger
       |
       v
normalize prospect
       |
       v
DeterministicLeadDecisionService
       |
       v
LAYA authoritative queue
       |
       +--> WORK_NOW ----> CommercialActionTicket
       |                        |
       |                        v
       |                  closer / human review
       |                        |
       |                        v
       |                 EffectApprovalReceipt
       |                        |
       |                        v
       |                  optional dispatch
       |
       +--> HOLD
       +--> REPAIR_DATA
       +--> COMPLETE
       +--> REJECT
```

Setter ranking is an input signal, not authority. Elevated commercial stages require matching structured evidence before they can gain priority. The gate remains deterministic and free of network/model calls.

A `CommercialActionTicket` is emitted only for `WORK_NOW`. It binds buyer/title/contact target, stage, `next_action`, rank and authoritative `decision_hash`. It is a handoff artifact, not effect authority: `requires_human_approval=true` and an actual external mutation still requires the separate EffectApprovalReceipt boundary.

## Effects

A real external mutation requires an exact canonical action envelope and a durable one-use approval receipt.

```text
action envelope
     |
     v
EffectApprovalReceipt
     |
     v
atomic consume + intent
     |
     v
adapter dispatch
  |         |
success   exception after invocation
  |         |
  v         v
SUCCEEDED  UNKNOWN
             |
             +--> no blind retry
```

No real-world effect adapter is enabled by default.

## Replay

Replay verifies semantic truth rather than incidental timing.

Bound into causal replay:

- plan hash;
- node identity and kind;
- prerequisites;
- declared input hash;
- prerequisite output hashes;
- output hash;
- semantic terminal state;
- effect-policy evidence when applicable.

Excluded from semantic equivalence:

- run/event UUIDs;
- wall-clock timestamps;
- node duration;
- scheduler turn number;
- incidental completion order among independent nodes.

The causal semantic hash is anchored in the append-only event ledger.

## Extension policy

A new framework or service is added only when it provides a separable primitive that:

- MiMicus does not already have;
- preserves LAYA as the sole orchestration authority;
- has a mandatory-$0 path or removable fallback;
- can be benchmarked;
- can be removed without breaking evidence, memory or effect authority.
