from __future__ import annotations

from dataclasses import dataclass

from mimicus.falsifiers.primitives import execute_primitive
from mimicus.falsifiers.spec import FalsifierSpec
from mimicus.germinal.fossils import Fossil
from mimicus.germinal.mutate import MutationCandidate
from mimicus.types import Verdict


@dataclass(frozen=True)
class RegressionMetrics:
    tested: int
    tp: int
    tn: int
    fp: int
    fn: int
    precision: float
    recall: float
    fpr: float
    fnr: float
    critical_regressions: int


@dataclass(frozen=True)
class PromotionDecision:
    status: str
    reason: str
    parent_metrics: RegressionMetrics
    candidate_metrics: RegressionMetrics


def evaluate(spec: FalsifierSpec, fossils: list[Fossil]) -> RegressionMetrics:
    relevant = [f for f in fossils if f.primitive == spec.primitive]
    tp = tn = fp = fn = critical = 0
    for fossil in relevant:
        actual = execute_primitive(spec, fossil.context).verdict
        expected_fail = fossil.expected == Verdict.FAIL
        actual_fail = actual == Verdict.FAIL
        if expected_fail and actual_fail:
            tp += 1
        elif not expected_fail and not actual_fail:
            tn += 1
        elif not expected_fail and actual_fail:
            fp += 1
            critical += int(fossil.critical)
        else:
            fn += 1
            critical += int(fossil.critical and expected_fail)
    precision = tp / max(1, tp + fp)
    recall = tp / max(1, tp + fn)
    fpr = fp / max(1, fp + tn)
    fnr = fn / max(1, fn + tp)
    return RegressionMetrics(len(relevant), tp, tn, fp, fn, precision, recall, fpr, fnr, critical)


def decide(parent: FalsifierSpec, mutation: MutationCandidate, fossils: list[Fossil]) -> PromotionDecision:
    parent_metrics = evaluate(parent, fossils)
    candidate_metrics = evaluate(mutation.candidate, fossils)
    conditions = [
        mutation.catches_triggering_evasion,
        candidate_metrics.precision >= parent_metrics.precision,
        candidate_metrics.recall >= parent_metrics.recall - 0.02,
        candidate_metrics.critical_regressions == 0,
        candidate_metrics.tested >= 20,
    ]
    if all(conditions):
        return PromotionDecision("PROMOTE", "deterministic promotion gate passed", parent_metrics, candidate_metrics)
    return PromotionDecision("REJECT", "deterministic promotion gate failed", parent_metrics, candidate_metrics)
