from __future__ import annotations

from dataclasses import dataclass

from mimicus.canonical import sha256_obj
from mimicus.types import Verdict


@dataclass(frozen=True)
class Fossil:
    fossil_id: str
    primitive: str
    context: dict[str, object]
    expected: Verdict
    critical: bool = False

    @property
    def snapshot_hash(self) -> str:
        return sha256_obj({"id": self.fossil_id, "primitive": self.primitive, "context": self.context, "expected": self.expected.value, "critical": self.critical})


def seed_fossils() -> list[Fossil]:
    fossils: list[Fossil] = []
    for i in range(20):
        ok = i % 2 == 0
        expected = 1200.0
        claimed = expected * (1.0 if ok else 1.5)
        fossils.append(Fossil(f"F1-{i:02d}", "numeric_invariant", {"price": 10.0, "users": 10.0, "price_period": "monthly", "claimed": claimed}, Verdict.PASS if ok else Verdict.FAIL, critical=i < 2))
    for i in range(20):
        fresh = i % 2 == 0
        date = "2026-08-10T00:00:00+00:00" if fresh else "2025-01-01T00:00:00+00:00"
        fossils.append(Fossil(f"F2-{i:02d}", "freshness", {"evidence_date": date, "as_of": "2026-08-17T00:00:00+00:00"}, Verdict.PASS if fresh else Verdict.FAIL))
    for i in range(20):
        independent = i % 2 == 0
        clusters = ["a", "b"] if independent else ["a", "a"]
        fossils.append(Fossil(f"F3-{i:02d}", "source_independence", {"clusters": clusters, "texts": ["alpha report", "alpha report syndicated"]}, Verdict.PASS if independent else Verdict.FAIL))
    for i in range(20):
        entailed = i % 2 == 0
        spans = [{"span_id": "s1", "supported_figures": ["42"] if entailed else ["41"], "material_support": entailed}]
        fossils.append(Fossil(f"F4-{i:02d}", "citation_entailment", {"claim_figure": 42, "evidence_spans": spans}, Verdict.PASS if entailed else Verdict.FAIL))
    registry_hash = "a" * 64
    for i in range(20):
        absent = i % 2 == 0
        registry = {} if absent else {"target": {"id": i}}
        fossils.append(Fossil(f"F5-{i:02d}", "counterexample_search", {"absence_key": "target", "registry": registry, "registry_snapshot_hash": registry_hash}, Verdict.PASS if absent else Verdict.FAIL))
    return fossils
