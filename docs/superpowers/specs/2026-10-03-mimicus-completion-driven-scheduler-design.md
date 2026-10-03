# Mimicus Completion-Driven DAG Scheduler V1 — Design

**Date:** 2026-10-03
**Branch:** `aud-arq/mimicus-scheduler-v1`
**Base:** `aud-arq/mimicus-live-observer-v1@9c01f0403eb19608686f6f3ada3ec888bc93c52a`

## Problem

The current `DagExecutor` has real asyncio concurrency but executes ready nodes in barriered batches:

1. compute all currently ready nodes;
2. start up to `max_concurrency`;
3. wait for the whole TaskGroup batch;
4. commit outputs;
5. recompute readiness.

This delays a newly eligible descendant behind an unrelated slow sibling.

Example with concurrency 2:

```text
root
├── A (fast) -> A1
└── B (blocked/slow)
```

Current: `A1` cannot start until `B` finishes.

Target: when `A` completes successfully, commit A, release A1 immediately and schedule it if capacity exists while B remains in flight.

## Invariants

- LAYA / MiMicusEngine authority unchanged.
- MorphologyPlan / node prerequisites remain canonical.
- max_concurrency remains 1..8.
- Fatal node failure still cancels all in-flight siblings and awaits their cancellation before returning.
- A child cannot run before every prerequisite has completed successfully.
- Timeout semantics remain node-local fatal failures.
- Precompleted nodes keep current semantics.
- Output hashes remain canonical.
- Schedule/evidence includes every started node exactly once.
- No arbitrary retry.
- No new dependency.
- No timing-sensitive correctness test.

## Algorithm

Maintain:
- `pending`: nodes not started;
- `in_flight`: node_id -> asyncio.Task;
- `outputs`: successful results;
- deterministic ready selection sorted by node_id.

Loop:

1. Fill spare capacity with sorted ready nodes whose prerequisites are in outputs.
2. If no in-flight tasks and pending remains: stalled DAG error.
3. Wait with `asyncio.wait(..., return_when=FIRST_COMPLETED)`.
4. Take all tasks already done in that scheduler turn and process them in stable node_id order.
5. If any completed task failed/timed out:
   - cancel every remaining in-flight task;
   - await all cancellations;
   - capture statuses;
   - raise one `DagExecutionError`.
6. Otherwise commit successful outputs immediately.
7. Re-enter fill step; newly-ready descendants may use capacity immediately.

Stable node ordering makes admission deterministic for an identical observed completion set. It does NOT claim asynchronous completion order is deterministic.

## Scheduler metric

Replace the structurally dead interpretation of `avoidable_serialization_count` with an observable scheduler metric:

Count a scheduler turn when:
- at least one node is ready;
- spare capacity exists;
- the scheduler leaves that ready node waiting.

A correct completion-driven scheduler should normally report zero.

The metric is diagnostic; correctness does not depend on it.

## Falsifier

Use events, not sleep duration:

- A and B become ready together.
- max_concurrency=2.
- A returns after an explicit release event.
- B waits on a separate blocker.
- A1 depends only on A.
- After A completes and before B is released, wait for A1's `started` event.

Pass condition: A1 starts while B is still blocked.

Failure conditions:
- A1 waits for B;
- A1 starts before A succeeds;
- more than max_concurrency tasks run;
- fatal failure fails to cancel siblings;
- any advertised morphology regresses.

## Non-goals

- causal replay redesign;
- effect authorization;
- new orchestration framework;
- changing MorphologyPlan compiler;
- changing LAYA;
- deterministic wall-clock timings.
