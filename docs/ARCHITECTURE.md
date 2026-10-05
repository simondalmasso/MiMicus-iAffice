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
       +--> WORK_NOW --> CommercialActionTicket --> human/effect approval boundary
       +--> HOLD
       +--> REPAIR_DATA
       +--> COMPLETE
       +--> REJECT

same normalized candidates + authoritative batch
       |
       v
read-only CommercialFunnelSnapshot
       |
       +--> stage counts / transition rates / latency
       +--> terminal win rate
       +--> sanitized calibration rows
```

Setter ranking is an input signal, not authority. The gate remains deterministic and free of network/model calls. A `CommercialActionTicket` is not an effect approval: it is an auditable handoff record for the human/closer layer, while real external mutation still requires the exact-envelope `EffectApprovalReceipt`. Funnel analytics are read-only and cannot alter LAYA decisions.

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


## Optional provider profiles

The control plane can use provider adapters without changing orchestration authority. The NVIDIA profile uses the generic OpenAI-compatible provider against NVIDIA NIM and defaults to `deepseek-ai/deepseek-v4.1-flash`. It is optional: no NVIDIA credential is required for offline operation, and zero-cost status is fail-closed unless explicitly confirmed by operator configuration. NVIDIA's hosted Free Endpoint is treated as development/prototyping scope; production entitlement remains an external prerequisite and is surfaced by `doctor`.
