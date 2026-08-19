# ARTICLE_REFERENCE benchmark baseline

This file freezes the benchmark baseline before the final benchmark is executed.

The replaced architecture is modeled as six independent specialist chats. For every incoming business episode it sends the full episode through all six business specialist transformations (Research, CMO, Sales, Data, Dev and Planner), regardless of whether SQL/rules already determine the answer. It has no minimal-coalition routing and no deterministic deduplication before LLM work. AUD is excluded from both model-call denominators so the comparison does not penalize the governed design for adding a safety role.

For the same 100 checked-in deterministic episodes, ARTICLE_REFERENCE therefore performs 600 model calls. Expected outputs are the golden action classes in `scripts/benchmark.mjs`; baseline correctness is measured by the same evaluator. Its unsupported-claim and protected-action behavior are evaluated, not assumed.

This baseline must not be changed in response to benchmark results. AriaOS may improve by deterministic preprocessing, idempotency, batching and minimal routing, while using the same expected business outputs.
