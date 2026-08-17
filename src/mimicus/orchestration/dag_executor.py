from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from time import perf_counter

from mimicus.canonical import sha256_obj
from mimicus.orchestration.morphology import DagNode, MorphologyPlan, NodeKind

NodeHandler = Callable[[DagNode], Awaitable[object]]


@dataclass(frozen=True)
class ExecutionMetrics:
    work_steps: int
    critical_steps: int
    critical_path_ms: float
    observed_wall_ms: float
    serial_work_ms: float
    peak_concurrency: int
    parallel_speedup_estimate: float
    parallel_efficiency: float
    subtask_finish_rate: float
    avoidable_serialization_count: int

    def as_dict(self) -> dict[str, float | int]:
        return {
            "work_steps": self.work_steps,
            "critical_steps": self.critical_steps,
            "critical_path_ms": self.critical_path_ms,
            "observed_wall_ms": self.observed_wall_ms,
            "serial_work_ms": self.serial_work_ms,
            "peak_concurrency": self.peak_concurrency,
            "parallel_speedup_estimate": self.parallel_speedup_estimate,
            "parallel_efficiency": self.parallel_efficiency,
            "subtask_finish_rate": self.subtask_finish_rate,
            "avoidable_serialization_count": self.avoidable_serialization_count,
        }


@dataclass(frozen=True)
class DagExecution:
    outputs: dict[str, object]
    output_hashes: dict[str, str]
    metrics: ExecutionMetrics
    schedule: list[dict[str, object]]


class DagExecutor:
    def __init__(self, max_concurrency: int = 4) -> None:
        if not 1 <= max_concurrency <= 8:
            raise ValueError("max_concurrency must be in 1..8")
        self.max_concurrency = max_concurrency

    async def execute(
        self,
        plan: MorphologyPlan,
        handler: NodeHandler,
        *,
        precompleted: dict[str, object] | None = None,
        executable_kinds: set[NodeKind] | None = None,
    ) -> DagExecution:
        plan.validate()
        pre = dict(precompleted or {})
        allowed = executable_kinds or set(NodeKind)
        nodes = {node.node_id: node for node in plan.nodes}
        outputs: dict[str, object] = dict(pre)
        output_hashes = {node_id: sha256_obj(value) for node_id, value in pre.items()}
        pending = {node_id for node_id in nodes if node_id not in pre}
        schedule: list[dict[str, object]] = []
        active = 0
        peak = 0
        avoidable_serialization = 0
        wall_started = perf_counter()

        async def invoke(node: DagNode) -> tuple[object, float, str]:
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            started = perf_counter()
            node.status = "RUNNING"
            try:
                async with asyncio.timeout(node.timeout_s):
                    value = await handler(node) if node.kind in allowed else {"prelude": node.kind.value}
            except TimeoutError:
                node.status = "TIMED_OUT"
                raise
            except BaseException:
                node.status = "FAILED"
                raise
            finally:
                active -= 1
            duration_ms = (perf_counter() - started) * 1000.0
            node.duration_ms = duration_ms
            node.output_hash = sha256_obj(value)
            node.status = "COMPLETED"
            return value, duration_ms, node.output_hash

        while pending:
            ready = sorted(node_id for node_id in pending if all(parent in outputs for parent in nodes[node_id].prerequisites))
            if not ready:
                raise RuntimeError("DAG execution stalled: no ready nodes")
            if len(ready) > 1 and self.max_concurrency > 1:
                capacity = min(self.max_concurrency, len(ready))
                if capacity == 1:
                    avoidable_serialization += len(ready) - 1
            batch = ready[: self.max_concurrency]
            batch_started = perf_counter()
            results = await asyncio.gather(*(invoke(nodes[node_id]) for node_id in batch))
            batch_ms = (perf_counter() - batch_started) * 1000.0
            for node_id, (value, duration_ms, digest) in zip(batch, results, strict=True):
                outputs[node_id] = value
                output_hashes[node_id] = digest
                pending.remove(node_id)
                schedule.append(
                    {
                        "node_id": node_id,
                        "kind": nodes[node_id].kind.value,
                        "prerequisites": list(nodes[node_id].prerequisites),
                        "duration_ms": duration_ms,
                        "batch_wall_ms": batch_ms,
                        "output_hash": digest,
                    }
                )

        observed_wall_ms = (perf_counter() - wall_started) * 1000.0
        serial_work_ms = sum(node.duration_ms for node in plan.nodes if node.status == "COMPLETED" and node.node_id not in pre)
        finishable = [node for node in plan.nodes if node.kind in {NodeKind.AGENT_TASK, NodeKind.FALSIFIER, NodeKind.CHALLENGE}]
        finished = sum(node.status == "COMPLETED" for node in finishable)
        subtask_finish_rate = finished / max(1, len(finishable))
        path_ms: dict[str, float] = {}
        path_steps: dict[str, int] = {}
        for node in self._topological(plan):
            base_ms = max((path_ms[parent] for parent in node.prerequisites), default=0.0)
            base_steps = max((path_steps[parent] for parent in node.prerequisites), default=0)
            path_ms[node.node_id] = base_ms + node.duration_ms
            path_steps[node.node_id] = base_steps + node.logical_steps
        critical_path_ms = max(path_ms.values(), default=0.0)
        critical_steps = max(path_steps.values(), default=0)
        epsilon = 0.001
        speedup = serial_work_ms / max(observed_wall_ms, epsilon)
        efficiency = min(1.0, speedup / max(peak, 1))
        metrics = ExecutionMetrics(
            work_steps=sum(node.logical_steps for node in plan.nodes if node.status == "COMPLETED"),
            critical_steps=critical_steps,
            critical_path_ms=critical_path_ms,
            observed_wall_ms=observed_wall_ms,
            serial_work_ms=serial_work_ms,
            peak_concurrency=peak,
            parallel_speedup_estimate=speedup,
            parallel_efficiency=efficiency,
            subtask_finish_rate=subtask_finish_rate,
            avoidable_serialization_count=avoidable_serialization,
        )
        return DagExecution(outputs, output_hashes, metrics, schedule)

    @staticmethod
    def _topological(plan: MorphologyPlan) -> list[DagNode]:
        remaining = {node.node_id: node for node in plan.nodes}
        ordered: list[DagNode] = []
        done: set[str] = set()
        while remaining:
            ready = sorted(node_id for node_id, node in remaining.items() if set(node.prerequisites) <= done)
            if not ready:
                raise RuntimeError("invalid DAG topology")
            for node_id in ready:
                node = remaining.pop(node_id)
                ordered.append(node)
                done.add(node_id)
        return ordered
