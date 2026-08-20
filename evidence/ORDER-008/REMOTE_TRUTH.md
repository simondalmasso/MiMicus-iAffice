# ORDER-008 Remote Truth

- Repository: `simonkey888/MiMicus-swarm`
- Authority issue: `#10` / ORDER-008.
- Pull request: `#3`, branch `order-002-mimicus-v01`, remains open and unmerged.
- Binding latest AUD reviewed for this closure: comment `5359208502`.
- Baseline `main`: `2d50fd91f4346618acfa87928987e131f54159c7`; ORDER-008 does not write to `main`.
- Functional proof candidate before evidence materialization: `ae6a1dc913412a2ba5ae12c65d49bf5589bac767`.
- Exact-head run `32398665327` proved the regenerated ORDER-008 evidence, MCP restart/revocation chain, F038-F044 gates, security/history, migrations/package, and benchmark; its committed-evidence comparison intentionally rejected the older evidence bytes.
- The committed evidence bundle is accepted only when a subsequent exact-head CI regenerates the same generated evidence byte-for-byte and `sha256sum -c MANIFEST.sha256` succeeds.

`ATM_WORK=DEFERRED_OUT_OF_SCOPE`

`OPENAI_LIVE=DEFERRED_OUT_OF_SCOPE`
