# Benchmark

The frozen `ARTICLE_REFERENCE` baseline is specified in `docs/ARTICLE_REFERENCE.md` before final measurement. It models fixed specialist routing with six model calls per episode over the same 100 reference episodes: 600 model calls.

AriaOS batches/deterministically resolves duplicate, stale, metric and policy events; model inference is reserved for research/content episodes. The checked-in benchmark measures model calls, normalized inference consumption, deterministic-work share, duplicate work, expected-output correctness, unsupported verified claims, policy violations, replay and tamper behavior.

`TEN_X_EFFICIENCY=PASS` requires >=10.0x fewer model calls or inference units, >=95% correctness, <=1 percentage-point quality regression versus baseline, zero unauthorized protected actions, zero unsupported claims promoted, 100% untampered replay, tamper detection and zero paid resource. The baseline is not changed after results.
