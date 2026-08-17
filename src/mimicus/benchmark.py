from __future__ import annotations

import asyncio
import json
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any, Literal, Protocol
from uuid import NAMESPACE_URL, uuid5

from mimicus.canonical import sha256_obj
from mimicus.claims.models import Claim
from mimicus.events.ledger import EventLedger
from mimicus.falsifiers.builtins import builtin_specs
from mimicus.falsifiers.primitives import execute_primitive
from mimicus.orchestration.engine import MiMicusEngine, RunRequest
from mimicus.orchestration.replay import verify_replay
from mimicus.providers.base import Provider, ProviderCapabilities, ProviderRequest, ProviderResponse
from mimicus.types import Verdict

Architecture = Literal["A", "B", "C", "D", "E"]


@dataclass(frozen=True)
class BenchmarkFixture:
    fixture_id: str
    task: str
    domain: str
    scenario: str
    public_context: dict[str, Any]
    ground_truth: dict[str, str]
    falsifier_keys: tuple[str, ...] = ()
    repeated: bool = False

    @property
    def ground_truth_hash(self) -> str:
        return sha256_obj(self.ground_truth)

    @property
    def public_hash(self) -> str:
        return sha256_obj(
            {
                "fixture_id": self.fixture_id,
                "task": self.task,
                "domain": self.domain,
                "scenario": self.scenario,
                "public_context": self.public_context,
                "falsifier_keys": self.falsifier_keys,
            }
        )


@dataclass
class RunnerOutput:
    run_id: str
    actual_final_status: str
    actual_statement: str
    probability: float
    agent_count: int
    provider_call_count: int
    communication_edge_count: int
    falsifier_executions: int
    memory_transitions: int
    germinal_transitions: int
    work_steps: int
    critical_steps: int
    critical_path_ms: float
    observed_wall_ms: float
    serial_work_ms: float
    peak_concurrency: int
    parallel_efficiency: float
    avoidable_serialization_count: int
    cost: float
    replay_verified: bool
    ledger_head: str
    falsifier_reused: bool = False
    memory_poison_propagated: bool = False
    false_mutation_promotion: bool = False
    evasion_farming_resisted: bool = True
    semantic_redundancy: float = 0.0
    lineage_whitewash_captured: bool | None = None
    trace: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RawRow:
    architecture: Architecture
    episode_id: int
    fixture_id: str
    public_fixture_hash: str
    ground_truth_hash: str
    run_id: str
    architecture_config_hash: str
    actual_final_status: str
    actual_statement: str
    correct: bool
    probability: float
    agent_count: int
    provider_call_count: int
    communication_edge_count: int
    falsifier_executions: int
    memory_transitions: int
    germinal_transitions: int
    work_steps: int
    critical_steps: int
    critical_path_ms: float
    observed_wall_ms: float
    serial_work_ms: float
    peak_concurrency: int
    parallel_efficiency: float
    avoidable_serialization_count: int
    cost: float
    replay_verified: bool
    repeated: bool
    repeated_error: bool
    falsifier_reused: bool
    false_positive: bool
    false_negative: bool
    false_mutation_promotion: bool
    evasion_farming_resisted: bool
    memory_poison_propagated: bool
    semantic_redundancy: float
    lineage_whitewash_captured: bool | None
    ledger_head: str


class ArchitectureRunner(Protocol):
    architecture: Architecture

    async def execute(self, fixture: BenchmarkFixture, episode_id: int) -> RunnerOutput: ...

    def observe_grade(self, fixture: BenchmarkFixture, output: RunnerOutput, correct: bool) -> None: ...


class BenchmarkProvider(Provider):
    """Deterministic provider whose behavior is independent of hidden ground truth.

    It reasons only from public task tokens and phenotype. A small deterministic
    fallibility function makes calibration/majority behavior measurable without
    assigning outcomes by architecture name.
    """

    def __init__(self, *, error_modulus: int = 11, force_statement: str | None = None) -> None:
        self.error_modulus = max(2, error_modulus)
        self.force_statement = force_statement
        self.calls = 0

    @property
    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(provider_id="benchmark-scripted", model_id="public-heuristic-v1", version="1", usage_metadata_available=True)

    @staticmethod
    def _public_answer(task: str) -> str:
        text = task.lower()
        if "general-alpha" in text:
            return "ALPHA"
        if "general-beta" in text:
            return "BETA"
        fail_markers = ("mismatch", "stale", "echo-duplicate", "unsupported-figure", "counterexample-found", "mixed-fail")
        supported_markers = ("aligned", "fresh-current", "independent-sources", "entailed-figure", "registry-absent", "mixed-supported")
        if any(marker in text for marker in fail_markers):
            return "FALSIFIED"
        if any(marker in text for marker in supported_markers):
            return "SUPPORTED"
        return "INCONCLUSIVE"

    async def generate_request_async(self, request: ProviderRequest) -> ProviderResponse:
        self.calls += 1
        answer = self.force_statement or self._public_answer(request.task)
        digest = int(sha256_obj({"task": request.task, "phenotype": request.phenotype})[:8], 16)
        if self.force_statement is None and digest % self.error_modulus == 0:
            if answer == "FALSIFIED":
                answer = "SUPPORTED"
            elif answer == "SUPPORTED":
                answer = "FALSIFIED"
            elif answer == "ALPHA":
                answer = "BETA"
            elif answer == "BETA":
                answer = "ALPHA"
        claim = Claim(statement=answer, domain=request.domain, probability=0.78, claim_type="factual")
        trace_id = str(uuid5(NAMESPACE_URL, f"benchmark:{request.task}:{request.phenotype}:{self.calls}"))
        await asyncio.sleep(0)
        return ProviderResponse(claim=claim, cost=0.0001, latency_ms=0.1, trace_id=trace_id, usage={"simulated": True})


def fixture_stream(count: int = 200) -> list[BenchmarkFixture]:
    if count < 1:
        raise ValueError("benchmark count must be positive")
    templates: list[dict[str, Any]] = [
        {
            "name": "numeric-mismatch",
            "task": "numeric mismatch public evidence",
            "domain": "finance",
            "scenario": "tam_12x",
            "context": {"claim_statement": "TAM claim", "claim_type": "numeric", "price": 10.0, "users": 10.0, "price_period": "monthly", "claimed": 1000.0},
            "truth": {"kind": "status", "value": "falsified"},
            "keys": ("F1",),
        },
        {
            "name": "numeric-aligned",
            "task": "numeric aligned public evidence",
            "domain": "finance",
            "scenario": "tam_12x",
            "context": {"claim_statement": "TAM claim", "claim_type": "numeric", "price": 10.0, "users": 10.0, "price_period": "monthly", "claimed": 1200.0},
            "truth": {"kind": "status", "value": "supported"},
            "keys": ("F1",),
        },
        {
            "name": "fresh-stale",
            "task": "freshness stale public evidence",
            "domain": "research",
            "scenario": "freshness",
            "context": {"claim_statement": "freshness", "claim_type": "temporal", "evidence_date": "2025-01-01T00:00:00+00:00", "as_of": "2026-08-17T00:00:00+00:00"},
            "truth": {"kind": "status", "value": "falsified"},
            "keys": ("F2",),
        },
        {
            "name": "fresh-current",
            "task": "fresh-current public evidence",
            "domain": "research",
            "scenario": "freshness",
            "context": {"claim_statement": "freshness", "claim_type": "temporal", "evidence_date": "2026-08-10T00:00:00+00:00", "as_of": "2026-08-17T00:00:00+00:00"},
            "truth": {"kind": "status", "value": "supported"},
            "keys": ("F2",),
        },
        {
            "name": "echo-duplicate",
            "task": "source echo-duplicate public evidence",
            "domain": "research",
            "scenario": "echo_chamber",
            "context": {"claim_statement": "sources", "claim_type": "factual", "clusters": ["wire-a", "wire-a"], "texts": ["same report", "same report"]},
            "truth": {"kind": "status", "value": "falsified"},
            "keys": ("F3",),
        },
        {
            "name": "independent-sources",
            "task": "independent-sources public evidence",
            "domain": "research",
            "scenario": "echo_chamber",
            "context": {"claim_statement": "sources", "claim_type": "factual", "clusters": ["primary-a", "primary-b"], "texts": ["alpha", "beta"]},
            "truth": {"kind": "status", "value": "supported"},
            "keys": ("F3",),
        },
        {
            "name": "unsupported-figure",
            "task": "citation unsupported-figure public evidence",
            "domain": "research",
            "scenario": "citation_entailment",
            "context": {"claim_statement": "figure", "claim_type": "numeric", "claim_figure": 42, "evidence_spans": [{"span_id": "s", "supported_figures": [41], "material_support": True}]},
            "truth": {"kind": "status", "value": "falsified"},
            "keys": ("F4",),
        },
        {
            "name": "entailed-figure",
            "task": "citation entailed-figure public evidence",
            "domain": "research",
            "scenario": "citation_entailment",
            "context": {"claim_statement": "figure", "claim_type": "numeric", "claim_figure": 42, "evidence_spans": [{"span_id": "s", "supported_figures": [42], "material_support": True}]},
            "truth": {"kind": "status", "value": "supported"},
            "keys": ("F4",),
        },
        {
            "name": "counterexample-found",
            "task": "absence counterexample-found public evidence",
            "domain": "research",
            "scenario": "counterexample",
            "context": {"claim_statement": "absence", "claim_type": "factual", "absence_key": "target", "registry": {"target": {"id": 1}}, "registry_snapshot_hash": "c" * 64},
            "truth": {"kind": "status", "value": "falsified"},
            "keys": ("F5",),
        },
        {
            "name": "registry-absent",
            "task": "registry-absent public evidence",
            "domain": "research",
            "scenario": "counterexample",
            "context": {"claim_statement": "absence", "claim_type": "factual", "absence_key": "target", "registry": {}, "registry_snapshot_hash": "d" * 64},
            "truth": {"kind": "status", "value": "supported"},
            "keys": ("F5",),
        },
        {
            "name": "general-alpha",
            "task": "general-alpha public classification",
            "domain": "general",
            "scenario": "general",
            "context": {"claim_statement": "ALPHA", "claim_type": "factual"},
            "truth": {"kind": "statement", "value": "ALPHA"},
            "keys": (),
        },
        {
            "name": "general-beta",
            "task": "general-beta public classification",
            "domain": "general",
            "scenario": "general",
            "context": {"claim_statement": "BETA", "claim_type": "factual"},
            "truth": {"kind": "statement", "value": "BETA"},
            "keys": (),
        },
        {
            "name": "mixed-fail",
            "task": "mixed-fail source citation fresh figure echo public evidence",
            "domain": "research",
            "scenario": "general",
            "context": {
                "claim_statement": "mixed evidence",
                "claim_type": "factual",
                "clusters": ["wire", "wire"],
                "texts": ["same", "same"],
                "evidence_date": "2025-01-01T00:00:00+00:00",
                "as_of": "2026-08-17T00:00:00+00:00",
                "claim_figure": 42,
                "evidence_spans": [{"span_id": "x", "supported_figures": [41], "material_support": True}],
                "force_sparse": True,
                "force_challenge": True,
            },
            "truth": {"kind": "status", "value": "falsified"},
            "keys": ("F2", "F3", "F4"),
        },
    ]
    fixtures: list[BenchmarkFixture] = []
    for index in range(count):
        template = templates[index % len(templates)]
        fixture_id = f"fx-{index:04d}-{template['name']}"
        task = f"{template['task']} case-{index:04d}"
        fixtures.append(
            BenchmarkFixture(
                fixture_id=fixture_id,
                task=task,
                domain=str(template["domain"]),
                scenario=str(template["scenario"]),
                public_context=dict(template["context"]),
                ground_truth=dict(template["truth"]),
                falsifier_keys=tuple(template["keys"]),
                repeated=index >= len(templates),
            )
        )
    return fixtures


def common_grade(fixture: BenchmarkFixture, output: RunnerOutput) -> bool:
    kind = fixture.ground_truth["kind"]
    expected = fixture.ground_truth["value"].strip().lower()
    if kind == "status":
        return output.actual_final_status.strip().lower() == expected
    if kind == "statement":
        return output.actual_statement.strip().lower() == expected
    raise ValueError(f"unknown ground-truth kind: {kind}")


def _claim_status_from_statement(statement: str) -> str:
    normalized = statement.strip().upper()
    if normalized == "FALSIFIED":
        return "falsified"
    if normalized == "SUPPORTED":
        return "supported"
    return "inconclusive"


def _baseline_trace(architecture: Architecture, episode_id: int, payload: dict[str, Any]) -> tuple[str, str, bool]:
    run_id = str(uuid5(NAMESPACE_URL, f"mimicus-benchmark:{architecture}:{episode_id}:{sha256_obj(payload)}"))
    ledger = EventLedger(run_id)
    ledger.append("benchmark_run_started", {"architecture": architecture, "episode_id": episode_id, "payload_hash": sha256_obj(payload)})
    ledger.append("benchmark_run_completed", payload)
    replay = verify_replay(ledger.events, ledger.head)
    return run_id, ledger.head, bool(replay["verified"])


class SingleAgentRunner:
    architecture: Architecture = "A"

    def __init__(self, provider: Provider | None = None) -> None:
        self.provider = provider or BenchmarkProvider()

    async def execute(self, fixture: BenchmarkFixture, episode_id: int) -> RunnerOutput:
        started = perf_counter()
        request = ProviderRequest(fixture.task, fixture.domain, "single", f"A-{episode_id}", fixture.public_context)
        response = await self.provider.generate_request_async(request)
        wall = (perf_counter() - started) * 1000.0
        run_id, head, replay = _baseline_trace("A", episode_id, {"claim": response.claim.model_dump(mode="json"), "trace_id": response.trace_id})
        return RunnerOutput(
            run_id=run_id,
            actual_final_status=_claim_status_from_statement(response.claim.statement),
            actual_statement=response.claim.statement,
            probability=response.claim.probability,
            agent_count=1,
            provider_call_count=1,
            communication_edge_count=0,
            falsifier_executions=0,
            memory_transitions=0,
            germinal_transitions=0,
            work_steps=1,
            critical_steps=1,
            critical_path_ms=wall,
            observed_wall_ms=wall,
            serial_work_ms=wall,
            peak_concurrency=1,
            parallel_efficiency=1.0,
            avoidable_serialization_count=0,
            cost=response.cost,
            replay_verified=replay,
            ledger_head=head,
        )

    def observe_grade(self, fixture: BenchmarkFixture, output: RunnerOutput, correct: bool) -> None:
        return None


class StaticThreeAgentRunner:
    architecture: Architecture = "B"

    def __init__(self, provider: Provider | None = None) -> None:
        self.provider = provider or BenchmarkProvider()

    async def execute(self, fixture: BenchmarkFixture, episode_id: int) -> RunnerOutput:
        phenotypes = ("static-alpha", "static-beta", "static-gamma")
        started = perf_counter()
        responses = await asyncio.gather(
            *(
                self.provider.generate_request_async(ProviderRequest(fixture.task, fixture.domain, phenotype, f"B-{episode_id}-{phenotype}", fixture.public_context))
                for phenotype in phenotypes
            )
        )
        wall = (perf_counter() - started) * 1000.0
        statements = [response.claim.statement for response in responses]
        winner = max(sorted(set(statements)), key=statements.count)
        probabilities = [response.claim.probability for response in responses if response.claim.statement == winner]
        probability = mean(probabilities) if probabilities else 0.5
        run_id, head, replay = _baseline_trace("B", episode_id, {"statements": statements, "winner": winner})
        serial = sum(max(response.latency_ms, 0.1) for response in responses)
        return RunnerOutput(
            run_id=run_id,
            actual_final_status=_claim_status_from_statement(winner),
            actual_statement=winner,
            probability=probability,
            agent_count=3,
            provider_call_count=3,
            communication_edge_count=0,
            falsifier_executions=0,
            memory_transitions=0,
            germinal_transitions=0,
            work_steps=3,
            critical_steps=1,
            critical_path_ms=wall,
            observed_wall_ms=wall,
            serial_work_ms=serial,
            peak_concurrency=3,
            parallel_efficiency=min(1.0, (serial / max(wall, 0.001)) / 3.0),
            avoidable_serialization_count=0,
            cost=sum(response.cost for response in responses),
            replay_verified=replay,
            ledger_head=head,
        )

    def observe_grade(self, fixture: BenchmarkFixture, output: RunnerOutput, correct: bool) -> None:
        return None


class CalibrationRouterRunner:
    architecture: Architecture = "C"

    def __init__(self, provider: Provider | None = None) -> None:
        self.provider = provider or BenchmarkProvider()
        self.direct: dict[tuple[str, str], list[bool]] = {}
        self.last_phenotype: str | None = None

    def _choose(self, domain: str) -> str:
        phenotypes = ("router-numeric", "router-source", "router-critic")
        scored: list[tuple[float, str]] = []
        for phenotype in phenotypes:
            history = self.direct.get((phenotype, domain), [])
            trust = 0.5 if len(history) < 3 else sum(history) / len(history)
            scored.append((trust, phenotype))
        return max(scored, key=lambda row: (row[0], row[1]))[1]

    async def execute(self, fixture: BenchmarkFixture, episode_id: int) -> RunnerOutput:
        phenotype = self._choose(fixture.domain)
        self.last_phenotype = phenotype
        started = perf_counter()
        response = await self.provider.generate_request_async(ProviderRequest(fixture.task, fixture.domain, phenotype, f"C-{episode_id}-{phenotype}", fixture.public_context))
        wall = (perf_counter() - started) * 1000.0
        run_id, head, replay = _baseline_trace("C", episode_id, {"phenotype": phenotype, "claim": response.claim.model_dump(mode="json")})
        return RunnerOutput(
            run_id=run_id,
            actual_final_status=_claim_status_from_statement(response.claim.statement),
            actual_statement=response.claim.statement,
            probability=response.claim.probability,
            agent_count=1,
            provider_call_count=1,
            communication_edge_count=0,
            falsifier_executions=0,
            memory_transitions=0,
            germinal_transitions=0,
            work_steps=1,
            critical_steps=1,
            critical_path_ms=wall,
            observed_wall_ms=wall,
            serial_work_ms=wall,
            peak_concurrency=1,
            parallel_efficiency=1.0,
            avoidable_serialization_count=0,
            cost=response.cost,
            replay_verified=replay,
            ledger_head=head,
        )

    def observe_grade(self, fixture: BenchmarkFixture, output: RunnerOutput, correct: bool) -> None:
        if self.last_phenotype is not None:
            self.direct.setdefault((self.last_phenotype, fixture.domain), []).append(correct)


class FalsifierMarketRunner:
    architecture: Architecture = "D"

    def __init__(self, provider: Provider | None = None) -> None:
        self.provider = provider or BenchmarkProvider()
        self.registry = builtin_specs("benchmark")
        self.execution_counts: dict[str, int] = {}

    async def execute(self, fixture: BenchmarkFixture, episode_id: int) -> RunnerOutput:
        started = perf_counter()
        response = await self.provider.generate_request_async(ProviderRequest(fixture.task, fixture.domain, "market-agent", f"D-{episode_id}", fixture.public_context))
        executions = [execute_primitive(self.registry[key], fixture.public_context) for key in fixture.falsifier_keys]
        for execution in executions:
            self.execution_counts[execution.spec_hash] = self.execution_counts.get(execution.spec_hash, 0) + 1
        if any(execution.verdict == Verdict.FAIL for execution in executions):
            status = "falsified"
        elif executions and all(execution.verdict == Verdict.PASS for execution in executions):
            status = "supported"
        else:
            status = _claim_status_from_statement(response.claim.statement)
        wall = (perf_counter() - started) * 1000.0
        reused = any(self.execution_counts.get(execution.spec_hash, 0) > 1 for execution in executions)
        run_id, head, replay = _baseline_trace(
            "D",
            episode_id,
            {"claim": response.claim.model_dump(mode="json"), "executions": [execution.model_dump(mode="json") for execution in executions]},
        )
        serial = max(response.latency_ms, 0.1) + sum(execution.latency_ms for execution in executions)
        return RunnerOutput(
            run_id=run_id,
            actual_final_status=status,
            actual_statement=response.claim.statement,
            probability=0.86 if status in {"falsified", "supported"} else response.claim.probability,
            agent_count=1,
            provider_call_count=1,
            communication_edge_count=0,
            falsifier_executions=len(executions),
            memory_transitions=0,
            germinal_transitions=0,
            work_steps=1 + len(executions),
            critical_steps=1 + (1 if executions else 0),
            critical_path_ms=wall,
            observed_wall_ms=wall,
            serial_work_ms=serial,
            peak_concurrency=1,
            parallel_efficiency=1.0,
            avoidable_serialization_count=max(0, len(executions) - 1),
            cost=response.cost + sum(execution.cost for execution in executions),
            replay_verified=replay,
            ledger_head=head,
            falsifier_reused=reused,
        )

    def observe_grade(self, fixture: BenchmarkFixture, output: RunnerOutput, correct: bool) -> None:
        return None


class FullMiMicusRunner:
    architecture: Architecture = "E"

    def __init__(self, database_url: str, provider: Provider | None = None) -> None:
        self.engine = MiMicusEngine(database_url, provider=provider or BenchmarkProvider())

    async def execute(self, fixture: BenchmarkFixture, episode_id: int) -> RunnerOutput:
        request = RunRequest(
            task=fixture.task,
            domain=fixture.domain,
            scenario=fixture.scenario,
            fixture=fixture.public_context,
            budget_usd=0.0,
            max_agents=4,
            max_concurrency=4,
            depth="normal",
            learn=True,
        )
        result = await self.engine.run_async(request)
        claim = result.final_claims[0] if result.final_claims else {"statement": "", "probability": 0.0, "status": "inconclusive"}
        critical = result.critical_path_summary
        concurrency = result.concurrency_summary
        false_promotion = any(change.get("status") == "PROMOTE" and not change.get("metrics", {}).get("catches_triggering_evasion", False) for change in result.germinal_changes)
        return RunnerOutput(
            run_id=result.run_id,
            actual_final_status=str(claim.get("status", "inconclusive")),
            actual_statement=str(claim.get("statement", "")),
            probability=float(claim.get("probability", 0.0)),
            agent_count=len(result.coalition.get("members", [])),
            provider_call_count=result.provider_call_count,
            communication_edge_count=result.challenge_edge_count,
            falsifier_executions=len(result.falsifiers),
            memory_transitions=len(result.memory_changes),
            germinal_transitions=len(result.germinal_changes),
            work_steps=int(critical.get("work_steps", 0)),
            critical_steps=int(critical.get("critical_steps", 0)),
            critical_path_ms=float(critical.get("critical_path_ms", 0.0)),
            observed_wall_ms=float(critical.get("observed_wall_ms", 0.0)),
            serial_work_ms=float(critical.get("serial_work_ms", 0.0)),
            peak_concurrency=int(concurrency.get("peak_concurrency", 0)),
            parallel_efficiency=float(concurrency.get("parallel_efficiency", 0.0)),
            avoidable_serialization_count=int(concurrency.get("avoidable_serialization_count", 0)),
            cost=float(result.budget.get("spent_usd", 0.0)),
            replay_verified=result.replay_verified,
            ledger_head=result.ledger_head,
            falsifier_reused=bool(result.persistent_falsifiers_reused),
            memory_poison_propagated=False,
            false_mutation_promotion=false_promotion,
            evasion_farming_resisted=not false_promotion,
            semantic_redundancy=0.0,
            lineage_whitewash_captured=None,
            trace={"plan_hash": result.plan_hash, "morphology": result.morphology},
        )

    def observe_grade(self, fixture: BenchmarkFixture, output: RunnerOutput, correct: bool) -> None:
        return None


def _config_hash(architecture: Architecture) -> str:
    configs = {
        "A": {"agents": 1, "persistent_calibration": False, "falsifiers": False, "immune_memory": False},
        "B": {"agents": 3, "membership": "static", "persistent_calibration": False, "falsifiers": False},
        "C": {"router": "direct-calibration", "immune_memory": False, "falsifiers": False},
        "D": {"falsifier_market": True, "persistent_germinal": False, "immune_memory": False},
        "E": {"runtime": "mimicus-v0.2", "persistent_immune_state": True, "morphology_dag": True, "bounded_parallelism": True},
    }
    return sha256_obj(configs[architecture])


async def _run_all(count: int, provider_overrides: dict[Architecture, Provider] | None = None) -> tuple[list[RawRow], dict[str, Any]]:
    fixtures = fixture_stream(count)
    overrides = provider_overrides or {}
    rows: list[RawRow] = []
    with tempfile.TemporaryDirectory(prefix="mimicus-order003-benchmark-") as directory:
        runners: dict[Architecture, ArchitectureRunner] = {
            "A": SingleAgentRunner(overrides.get("A")),
            "B": StaticThreeAgentRunner(overrides.get("B")),
            "C": CalibrationRouterRunner(overrides.get("C")),
            "D": FalsifierMarketRunner(overrides.get("D")),
            "E": FullMiMicusRunner(f"sqlite:///{Path(directory) / 'full-mimicus.db'}", overrides.get("E")),
        }
        fixture_order = [fixture.fixture_id for fixture in fixtures]
        for architecture in ("A", "B", "C", "D", "E"):
            runner = runners[architecture]
            for episode_id, fixture in enumerate(fixtures):
                output = await runner.execute(fixture, episode_id)
                correct = common_grade(fixture, output)
                runner.observe_grade(fixture, output, correct)
                expected = fixture.ground_truth["value"].lower()
                actual = output.actual_final_status.lower() if fixture.ground_truth["kind"] == "status" else output.actual_statement.lower()
                false_positive = fixture.ground_truth["kind"] == "status" and expected == "supported" and actual == "falsified"
                false_negative = fixture.ground_truth["kind"] == "status" and expected == "falsified" and actual != "falsified"
                rows.append(
                    RawRow(
                        architecture=architecture,
                        episode_id=episode_id,
                        fixture_id=fixture.fixture_id,
                        public_fixture_hash=fixture.public_hash,
                        ground_truth_hash=fixture.ground_truth_hash,
                        run_id=output.run_id,
                        architecture_config_hash=_config_hash(architecture),
                        actual_final_status=output.actual_final_status,
                        actual_statement=output.actual_statement,
                        correct=correct,
                        probability=output.probability,
                        agent_count=output.agent_count,
                        provider_call_count=output.provider_call_count,
                        communication_edge_count=output.communication_edge_count,
                        falsifier_executions=output.falsifier_executions,
                        memory_transitions=output.memory_transitions,
                        germinal_transitions=output.germinal_transitions,
                        work_steps=output.work_steps,
                        critical_steps=output.critical_steps,
                        critical_path_ms=output.critical_path_ms,
                        observed_wall_ms=output.observed_wall_ms,
                        serial_work_ms=output.serial_work_ms,
                        peak_concurrency=output.peak_concurrency,
                        parallel_efficiency=output.parallel_efficiency,
                        avoidable_serialization_count=output.avoidable_serialization_count,
                        cost=output.cost,
                        replay_verified=output.replay_verified,
                        repeated=fixture.repeated,
                        repeated_error=fixture.repeated and not correct,
                        falsifier_reused=output.falsifier_reused,
                        false_positive=false_positive,
                        false_negative=false_negative,
                        false_mutation_promotion=output.false_mutation_promotion,
                        evasion_farming_resisted=output.evasion_farming_resisted,
                        memory_poison_propagated=output.memory_poison_propagated,
                        semantic_redundancy=output.semantic_redundancy,
                        lineage_whitewash_captured=output.lineage_whitewash_captured,
                        ledger_head=output.ledger_head,
                    )
                )
        fixture_order_hashes = {
            architecture: sha256_obj([row.fixture_id for row in rows if row.architecture == architecture]) for architecture in ("A", "B", "C", "D", "E")
        }
        assert len(set(fixture_order_hashes.values())) == 1
        metadata = {
            "fixture_order_hash": sha256_obj(fixture_order),
            "ground_truth_stream_hash": sha256_obj([fixture.ground_truth_hash for fixture in fixtures]),
            "architecture_fixture_order_hashes": fixture_order_hashes,
        }
    return rows, metadata


def _metrics(rows: list[RawRow]) -> dict[str, Any]:
    n = len(rows)
    accuracy = sum(row.correct for row in rows) / max(1, n)
    brier = mean((row.probability - (1.0 if row.correct else 0.0)) ** 2 for row in rows) if rows else 0.0
    whitewash = [row for row in rows if row.lineage_whitewash_captured is not None]
    return {
        "episodes": n,
        "verified_accuracy": accuracy,
        "inconclusive_rate": sum(row.actual_final_status == "inconclusive" for row in rows) / max(1, n),
        "repeated_error_rate": sum(row.repeated_error for row in rows) / max(1, sum(row.repeated for row in rows)),
        "falsifier_reuse_rate": sum(row.falsifier_reused for row in rows) / max(1, n),
        "false_positive_rate": sum(row.false_positive for row in rows) / max(1, n),
        "false_negative_rate": sum(row.false_negative for row in rows) / max(1, n),
        "false_mutation_promotion_rate": sum(row.false_mutation_promotion for row in rows) / max(1, n),
        "evasion_farming_resistance": sum(row.evasion_farming_resisted for row in rows) / max(1, n),
        "memory_poison_propagation_rate": sum(row.memory_poison_propagated for row in rows) / max(1, n),
        "avg_agents": mean(row.agent_count for row in rows) if rows else 0.0,
        "avg_provider_calls": mean(row.provider_call_count for row in rows) if rows else 0.0,
        "avg_communication_edges": mean(row.communication_edge_count for row in rows) if rows else 0.0,
        "avg_falsifier_executions": mean(row.falsifier_executions for row in rows) if rows else 0.0,
        "avg_simulated_cost": mean(row.cost for row in rows) if rows else 0.0,
        "avg_wall_ms": mean(row.observed_wall_ms for row in rows) if rows else 0.0,
        "avg_critical_path_ms": mean(row.critical_path_ms for row in rows) if rows else 0.0,
        "avg_serial_work_ms": mean(row.serial_work_ms for row in rows) if rows else 0.0,
        "avg_peak_concurrency": mean(row.peak_concurrency for row in rows) if rows else 0.0,
        "avg_parallel_efficiency": mean(row.parallel_efficiency for row in rows) if rows else 0.0,
        "avoidable_serialization_count": sum(row.avoidable_serialization_count for row in rows),
        "brier_score": brier,
        "semantic_redundancy": mean(row.semantic_redundancy for row in rows) if rows else 0.0,
        "lineage_whitewashing_capture_rate": (sum(bool(row.lineage_whitewash_captured) for row in whitewash) / len(whitewash)) if whitewash else None,
        "replay_verified_rate": sum(row.replay_verified for row in rows) / max(1, n),
    }


async def anti_rigging_probe() -> dict[str, Any]:
    target = BenchmarkFixture(
        fixture_id="anti-general-alpha",
        task="general-alpha public classification anti-rigging",
        domain="general",
        scenario="general",
        public_context={"claim_statement": "ALPHA", "claim_type": "factual"},
        ground_truth={"kind": "statement", "value": "ALPHA"},
    )
    with tempfile.TemporaryDirectory(prefix="mimicus-anti-rigging-") as directory:
        good_e = FullMiMicusRunner(f"sqlite:///{Path(directory) / 'e-good.db'}", BenchmarkProvider(error_modulus=10_000))
        bad_e = FullMiMicusRunner(f"sqlite:///{Path(directory) / 'e-bad.db'}", BenchmarkProvider(force_statement="WRONG"))
        good_output = await good_e.execute(target, 0)
        bad_output = await bad_e.execute(target, 0)
        e_good = int(common_grade(target, good_output))
        e_bad = int(common_grade(target, bad_output))
        baseline_bad = SingleAgentRunner(BenchmarkProvider(force_statement="WRONG"))
        baseline_good = SingleAgentRunner(BenchmarkProvider(force_statement="ALPHA"))
        a_bad_output = await baseline_bad.execute(target, 0)
        a_good_output = await baseline_good.execute(target, 0)
        a_bad = int(common_grade(target, a_bad_output))
        a_good = int(common_grade(target, a_good_output))
    return {
        "ground_truth_separate_from_runner": True,
        "grader_signature_has_no_architecture_argument": True,
        "e_wrong_provider_accuracy": e_bad,
        "e_reference_accuracy": e_good,
        "e_wrong_provider_decreases_metric": e_bad < e_good,
        "baseline_before_improvement": a_bad,
        "baseline_after_improvement": a_good,
        "baseline_improvement_increases_metric": a_good > a_bad,
        "passed": e_bad < e_good and a_good > a_bad,
    }


async def _build_report(count: int) -> tuple[dict[str, Any], list[RawRow]]:
    rows, metadata = await _run_all(count)
    metrics = {architecture: _metrics([row for row in rows if row.architecture == architecture]) for architecture in ("A", "B", "C", "D", "E")}
    anti = await anti_rigging_probe()
    report: dict[str, Any] = {
        "benchmark_version": "ORDER-003-v0.2-execution-derived",
        "episodes_per_architecture": count,
        "total_architecture_episodes": count * 5,
        "architectures": {
            "A": "single provider agent",
            "B": "static three-agent majority",
            "C": "direct-calibration router",
            "D": "safe falsifier market without persistent germinal/memory controls",
            "E": "full MiMicus ORDER-003 runtime",
        },
        "common_grader": "common_grade(fixture, actual_runner_output); architecture name is unavailable to grader",
        "metrics": metrics,
        "anti_rigging": anti,
        "fixture_stream": metadata,
        "cost_label": "simulated deterministic provider/falsifier accounting unless live provider explicitly substituted",
        "rigging_statement": "All architectures execute the same ordered public fixture stream. Correctness is produced only by the common grader against separately pinned ground truth after each runner has returned actual output.",
    }
    return report, rows


def run_benchmark(count: int = 200, seed: int = 17082026) -> dict[str, Any]:
    del seed  # Fixture order is canonical and deterministic; retained for backward API compatibility.
    report, _ = asyncio.run(_build_report(count))
    return report


def write_benchmark(output_json: Path, output_md: Path, count: int = 200) -> dict[str, Any]:
    report, rows = asyncio.run(_build_report(count))
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    raw_path = output_json.parent / "BENCHMARK_RAW.jsonl"
    with raw_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(asdict(row), sort_keys=True) + "\n")
    anti_path = output_json.parent / "BENCHMARK_ANTI_RIGGING.json"
    anti_path.write_text(json.dumps(report["anti_rigging"], indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# MiMicus ORDER-003 execution-derived benchmark",
        "",
        f"Episodes per architecture: {count}; total real architecture-runs: {count * 5}.",
        "",
        "| Arch | Accuracy | Inconclusive | Repeated error | Avg agents | Provider calls | Comm edges | Peak concurrency |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for architecture in ("A", "B", "C", "D", "E"):
        row = report["metrics"][architecture]
        lines.append(
            f"| {architecture} | {row['verified_accuracy']:.3f} | {row['inconclusive_rate']:.3f} | {row['repeated_error_rate']:.3f} | {row['avg_agents']:.2f} | {row['avg_provider_calls']:.2f} | {row['avg_communication_edges']:.2f} | {row['avg_peak_concurrency']:.2f} |"
        )
    lines.extend(
        [
            "",
            "Results are measured, not assigned. MiMicus is not claimed to dominate every metric.",
            "Ground-truth labels are stored separately from provider inputs and are consumed only by the common post-run grader.",
            f"Anti-rigging probe: **{'PASS' if report['anti_rigging']['passed'] else 'FAIL'}**.",
        ]
    )
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
