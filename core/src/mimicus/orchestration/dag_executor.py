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


class DagExecutionError(RuntimeError):
    def __init__(self, failed_nodes: list[str], cancelled_nodes: list[str]) -> None:
        super().__init__(f"fatal DAG node failure; failed={failed_nodes}; cancelled={cancelled_nodes}")
        self.failed_nodes = failed_nodes
        self.cancelled_nodes = cancelled_nodes


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
            except asyncio.CancelledError:
                node.status = "CANCELLED"
                node.duration_ms = (perf_counter() - started) * 1000.0
                raise
            except TimeoutError:
                node.status = "TIMED_OUT"
                node.duration_ms = (perf_counter() - started) * 1000.0
                raise
            except BaseException:
                node.status = "FAILED"
                node.duration_ms = (perf_counter() - started) * 1000.0
                raise
            finally:
                active -= 1
            duration_ms = (perf_counter() - started) * 1000.0
            node.duration_ms = duration_ms
            node.output_hash = sha256_obj(value)
            node.status = "COMPLETED"
            return value, duration_ms, node.output_hash

        in_flight: dict[str, asyncio.Task[tuple[object, float, str]]] = {}
        scheduler_turn = 0

        def schedule_row(node_id: str, *, turn_wall_ms: float) -> dict[str, object]:
            node = nodes[node_id]
            return {
                "node_id": node_id,
                "kind": node.kind.value,
                "prerequisites": list(node.prerequisites),
                "duration_ms": node.duration_ms,
                "batch_wall_ms": turn_wall_ms,
                "scheduler_turn": scheduler_turn,
                "output_hash": node.output_hash,
                "status": node.status,
            }

        async def cancel_in_flight() -> None:
            tasks = list(in_flight.values())
            for task in tasks:
                if not task.done():
                    task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        try:
            while pending or in_flight:
                ready = sorted(
                    node_id
                    for node_id in pending
                    if all(parent in outputs for parent in nodes[node_id].prerequisites)
                )
                capacity = self.max_concurrency - len(in_flight)
                for node_id in ready[:capacity]:
                    pending.remove(node_id)
                    in_flight[node_id] = asyncio.create_task(
                        invoke(nodes[node_id]),
                        name=f"mimicus:{node_id}",
                    )

                waiting_ready = [
                    node_id
                    for node_id in pending
                    if all(parent in outputs for parent in nodes[node_id].prerequisites)
                ]
                if waiting_ready and len(in_flight) < self.max_concurrency:
                    avoidable_serialization += 1

                if not in_flight:
                    if pending:
                        raise RuntimeError("DAG execution stalled: no ready nodes")
                    break

                scheduler_turn += 1
                turn_started = perf_counter()
                done, _ = await asyncio.wait(
                    set(in_flight.values()),
                    return_when=asyncio.FIRST_COMPLETED,
                )
                turn_wall_ms = (perf_counter() - turn_started) * 1000.0

                completed_ids = sorted(
                    node_id for node_id, task in in_flight.items() if task in done
                )
                failed_ids: list[str] = []
                failure: BaseException | None = None
                for node_id in completed_ids:
                    task = in_flight[node_id]
                    if task.cancelled():
                        if nodes[node_id].status != "CANCELLED":
                            nodes[node_id].status = "CANCELLED"
                        if failure is None:
                            failure = asyncio.CancelledError()
                        continue
                    exc = task.exception()
                    if exc is not None:
                        failed_ids.append(node_id)
                        if failure is None:
                            failure = exc

                if failure is not None:
                    await cancel_in_flight()
                    current_ids = sorted(in_flight)
                    failed = sorted(
                        node_id
                        for node_id in current_ids
                        if nodes[node_id].status in {"FAILED", "TIMED_OUT"}
                    )
                    cancelled = sorted(
                        node_id
                        for node_id in current_ids
                        if nodes[node_id].status == "CANCELLED"
                    )
                    schedule.extend(
                        schedule_row(node_id, turn_wall_ms=turn_wall_ms)
                        for node_id in current_ids
                    )
                    raise DagExecutionError(failed, cancelled) from failure

                for node_id in completed_ids:
                    task = in_flight.pop(node_id)
                    value, duration_ms, digest = task.result()
                    outputs[node_id] = value
                    output_hashes[node_id] = digest
                    schedule.append(
                        schedule_row(node_id, turn_wall_ms=turn_wall_ms)
                        | {"duration_ms": duration_ms, "output_hash": digest}
                    )
        except asyncio.CancelledError:
            await cancel_in_flight()
            raise

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
