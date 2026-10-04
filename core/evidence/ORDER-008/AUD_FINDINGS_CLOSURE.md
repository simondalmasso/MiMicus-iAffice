# ORDER-008 AUD Findings Closure

Binding AUD: issue #10 comment `5359208502`.

## Latest required closures

1. **F038 claim-bound F1..F5 proof — CLOSED.**
   `tests/unit/test_order008_f038_claim_bound.py` adds typed claim-bound kills for freshness/F2, source-independence/F3, entailment/F4, and counterexample/F5. Together with the existing numeric/F1 runtime kill, the generated `CLAIM_BOUND_FALSIFIERS.json` executes all five. The tests prove exact single-target claim binding, typed assertion binding, divergent snapshot identity under the same evidence context, and fail-closed `INCONCLUSIVE` behavior for missing/wrong assertion types.

2. **F044 documentation/quickstart — CLOSED.**
   `README.md` now documents the ORDER-008 production runtime, explicit structured evidence, authority/learning boundaries, and the distinction between integrity replay and semantic re-execution. `fixtures/order008_quickstart.json` is explicit caller evidence. `tests/integration/test_order008_quickstart_cli.py` executes the documented zero-key chain `db upgrade -> run --profile offline --task-file -> replay` and requires runtime source plus verified integrity and semantic re-execution.

3. **F001..F037 production regression evidence — CLOSED without legacy overclaim.**
   `docs/ORDER008_RUNTIME_MAPPING.txt` contains exactly F001 through F037 with each row classified as production runtime, production contract, provider-contract mock, or exact-head system gate. The generator validates the complete sequence, executes applicable ORDER-005/006/007 evidence and normal-core tests, and labels ORDER-003 / fixture-oriented ORDER-004 checks as `COMPATIBILITY_ONLY` rather than production proof.

4. **PR metadata — CONTROL-PLANE FINALIZATION.**
   PR #3 remains the sole PR and stays unmerged. Its title/body are updated after the final exact-head green run so they can cite the exact immutable final HEAD, CI run, evidence path and manifest result without creating another code HEAD.

## Preserved closure

- F038..F044 semantics remain executable.
- MCP restart, authenticated verification, verified-memory reuse, supersession/revocation, revoked-memory exclusion and semantic replay remain executable.
- Security/ledger, historical compatibility, migration/package and benchmark gates remain required.
- No test weakening, synthetic acceptance evidence, new PR, merge, or direct `main` write was introduced.
