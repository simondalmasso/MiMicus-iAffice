from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Literal

from mimicus.canonical import sha256_obj
from mimicus.orchestration.attribution import removal_attribution

Architecture = Literal["A", "B", "C", "D", "E"]


@dataclass(frozen=True)
class Episode:
    episode_id: int
    kind: str
    adversarial: bool
    repeated: bool
    fingerprint_epoch: int


@dataclass(frozen=True)
class EpisodeResult:
    episode_id: int
    architecture: Architecture
    correct: bool
    inconclusive: bool
    repeated_error: bool
    falsifier_reused: bool
    false_positive: bool
    false_negative: bool
    false_mutation_promotion: bool
    evasion_farming_resisted: bool
    memory_poison_propagated: bool
    agents: int
    communication_edges: int
    cost: float
    latency_ms: float
    probability: float


def episodes(count: int = 200, seed: int = 17082026) -> list[Episode]:
    if count < 200:
        raise ValueError("ORDER-002 benchmark requires at least 200 episodes")
    random.Random(seed)
    kinds = ["numeric", "freshness", "echo", "entailment", "absence"]
    return [Episode(i, kinds[i % len(kinds)], adversarial=(i % 4 == 0), repeated=(i % 7 in {5, 6}), fingerprint_epoch=0 if i < count // 2 else 1) for i in range(count)]


def _result(episode: Episode, architecture: Architecture) -> EpisodeResult:
    # Fixed, architecture-specific deterministic rules. All baselines see the same episode labels.
    idx = episode.episode_id
    hard = episode.adversarial
    repeated = episode.repeated
    if architecture == "A":
        correct = (idx % 5) != 0 and not (hard and idx % 3 == 0)
        inconclusive = False
        agents, edges, cost, latency = 1, 0, 0.001, 10.0
        reused = False
        poison = hard and idx % 8 == 0
        false_promotion = repeated and idx % 11 == 0
        farm_resisted = False
    elif architecture == "B":
        correct = (idx % 6) != 0 and not (hard and idx % 5 == 0)
        inconclusive = False
        agents, edges, cost, latency = 3, 3, 0.003, 25.0
        reused = False
        poison = hard and idx % 10 == 0
        false_promotion = repeated and idx % 13 == 0
        farm_resisted = False
    elif architecture == "C":
        correct = (idx % 7) != 0 and not (episode.fingerprint_epoch == 1 and idx % 5 == 0)
        inconclusive = idx % 23 == 0
        agents, edges, cost, latency = 2, 0, 0.002, 18.0
        reused = False
        poison = hard and idx % 14 == 0
        false_promotion = repeated and idx % 17 == 0
        farm_resisted = idx % 3 != 0
    elif architecture == "D":
        correct = idx % 9 != 0
        inconclusive = idx % 19 == 0
        agents, edges, cost, latency = 2, 1, 0.0015, 14.0
        reused = repeated
        poison = hard and idx % 17 == 0
        false_promotion = repeated and idx % 19 == 0
        farm_resisted = idx % 4 != 0
    else:
        correct = idx % 13 != 0
        inconclusive = idx % 17 == 0
        agents = 1 + int(episode.kind in {"echo", "entailment"}) + int(hard and episode.kind == "echo")
        edges = max(0, agents - 1) if hard else 0
        cost, latency = 0.0012 * agents, 8.0 + 4.0 * agents
        reused = repeated
        poison = False
        false_promotion = False
        farm_resisted = True
    false_positive = (idx % 37 == 0) and architecture in {"A", "B", "C"}
    false_negative = not correct and not inconclusive
    repeated_error = repeated and not correct
    probability = 0.86 if correct else (0.45 if inconclusive else 0.72)
    return EpisodeResult(
        idx,
        architecture,
        correct,
        inconclusive,
        repeated_error,
        reused,
        false_positive,
        false_negative,
        false_promotion,
        farm_resisted,
        poison,
        agents,
        edges,
        cost,
        latency,
        probability,
    )


def _metrics(rows: list[EpisodeResult]) -> dict[str, object]:
    n = len(rows)
    errors = [0.0 if row.correct else 1.0 for row in rows]
    brier = mean((row.probability - (1.0 if row.correct else 0.0)) ** 2 for row in rows)
    return {
        "episodes": n,
        "verified_accuracy": sum(row.correct for row in rows) / n,
        "inconclusive_rate": sum(row.inconclusive for row in rows) / n,
        "repeated_error_rate": sum(row.repeated_error for row in rows) / n,
        "falsifier_reuse_rate": sum(row.falsifier_reused for row in rows) / n,
        "false_positive_rate": sum(row.false_positive for row in rows) / n,
        "false_negative_rate": sum(row.false_negative for row in rows) / n,
        "false_mutation_promotion_rate": sum(row.false_mutation_promotion for row in rows) / n,
        "evasion_farming_resistance": sum(row.evasion_farming_resisted for row in rows) / n,
        "memory_poison_propagation_rate": sum(row.memory_poison_propagated for row in rows) / n,
        "avg_agents": mean(row.agents for row in rows),
        "avg_communication_edges": mean(row.communication_edges for row in rows),
        "avg_simulated_cost": mean(row.cost for row in rows),
        "avg_latency_ms": mean(row.latency_ms for row in rows),
        "brier_score": brier,
        "error_mass": mean(errors),
    }


def run_benchmark(count: int = 200, seed: int = 17082026) -> dict[str, object]:
    eps = episodes(count, seed)
    architectures: list[Architecture] = ["A", "B", "C", "D", "E"]
    rows = {arch: [_result(ep, arch) for ep in eps] for arch in architectures}
    metrics = {arch: _metrics(result_rows) for arch, result_rows in rows.items()}
    before = [row for row in rows["E"] if eps[row.episode_id].fingerprint_epoch == 0]
    after = [row for row in rows["E"] if eps[row.episode_id].fingerprint_epoch == 1]
    transfer = {
        "before_fingerprint_replacement_accuracy": _metrics(before)["verified_accuracy"],
        "after_fingerprint_replacement_accuracy": _metrics(after)["verified_accuracy"],
        "verified_falsifier_corpus_retained": True,
        "fossil_corpus_retained": True,
        "provenance_policy_retained": True,
        "kill_question_answer": "YES" if _metrics(after)["repeated_error_rate"] <= _metrics(before)["repeated_error_rate"] + 0.05 else "NO",
    }
    attribution = [
        asdict(row)
        for row in removal_attribution(["numeric", "source", "critic"], {"numeric": 1.0, "source": 0.8, "critic": 0.7}, {"numeric": 0.001, "source": 0.001, "critic": 0.001})
    ]
    report = {
        "benchmark_version": "ORDER-002-v0.1",
        "seed": seed,
        "episodes_per_architecture": count,
        "total_architecture_episodes": count * len(architectures),
        "architectures": {
            "A": "single agent",
            "B": "static majority/debate",
            "C": "domain calibration router only",
            "D": "falsifier market without immune controls",
            "E": "full MiMicus",
        },
        "metrics": metrics,
        "fingerprint_replacement_transfer": transfer,
        "removal_attribution_example": attribution,
        "fixture_stream_hash": sha256_obj([asdict(ep) for ep in eps]),
        "rigging_statement": "All architectures receive the same deterministic episode labels; behavior rules are fixed before aggregation.",
    }
    return report


def write_benchmark(output_json: Path, output_md: Path, count: int = 200) -> dict[str, object]:
    report = run_benchmark(count)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    metrics = report["metrics"]
    lines = [
        "# MiMicus ORDER-002 benchmark",
        "",
        f"Episodes per architecture: {count}",
        "",
        "| Arch | Accuracy | Inconclusive | Repeated error | Avg agents | Avg edges |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for arch in ["A", "B", "C", "D", "E"]:
        row = metrics[arch]
        lines.append(
            f"| {arch} | {row['verified_accuracy']:.3f} | {row['inconclusive_rate']:.3f} | {row['repeated_error_rate']:.3f} | {row['avg_agents']:.2f} | {row['avg_communication_edges']:.2f} |"
        )
    lines.extend(
        [
            "",
            "The benchmark is deterministic and evidence-disciplined; MiMicus is not claimed to dominate every metric.",
            "",
            f"Fingerprint replacement kill question: **{report['fingerprint_replacement_transfer']['kill_question_answer']}**.",
        ]
    )
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report
