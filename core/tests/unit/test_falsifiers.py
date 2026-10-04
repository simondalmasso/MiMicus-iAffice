from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from mimicus.falsifiers.builtins import builtin_specs
from mimicus.falsifiers.k3_compat import K3_ARTIFACT_HASHES, K3_CONTRACT_HASHES, compatibility_vectors
from mimicus.falsifiers.market import FalsifierMarket
from mimicus.falsifiers.primitives import execute_primitive
from mimicus.falsifiers.registry import FalsifierRegistry
from mimicus.falsifiers.spec import FalsifierSpec
from mimicus.types import Verdict


def test_k3_compatibility_vectors() -> None:
    vectors = compatibility_vectors()
    assert len(vectors) == 10
    assert all(vector["pass"] for vector in vectors)
    assert any(vector["actual"] == "INCONCLUSIVE" for vector in vectors)
    assert K3_ARTIFACT_HASHES["zip"].startswith("f170")
    assert len(K3_CONTRACT_HASHES) == 5


@pytest.mark.parametrize(
    ("key", "context", "verdict"),
    [
        ("F1", {"price": 10, "users": 10, "price_period": "monthly", "claimed": 1200}, Verdict.PASS),
        ("F1", {"price": 10, "users": 10, "price_period": "monthly", "claimed": 100}, Verdict.FAIL),
        ("F1", {"price": None, "users": 10, "claimed": 100}, Verdict.INCONCLUSIVE),
        ("F1", {"price": 10, "users": 10, "price_period": "century", "claimed": 100}, Verdict.INCONCLUSIVE),
        ("F2", {"evidence_date": "2026-08-10T00:00:00+00:00", "as_of": "2026-08-17T00:00:00+00:00"}, Verdict.PASS),
        ("F2", {"evidence_date": "2026-09-10T00:00:00+00:00", "as_of": "2026-08-17T00:00:00+00:00"}, Verdict.FAIL),
        ("F2", {"evidence_date": "bad", "as_of": "2026-08-17T00:00:00+00:00"}, Verdict.INCONCLUSIVE),
        ("F3", {"clusters": ["a", "b"], "texts": ["one", "two"]}, Verdict.PASS),
        ("F3", {"clusters": ["a", "a"], "texts": ["same", "same"]}, Verdict.FAIL),
        ("F3", {"clusters": []}, Verdict.INCONCLUSIVE),
        ("F4", {"claim_figure": 42, "evidence_spans": [{"span_id": "a", "supported_figures": [42], "material_support": True}]}, Verdict.PASS),
        ("F4", {"claim_figure": 42, "evidence_spans": [{"span_id": "a", "supported_figures": [41], "material_support": True}]}, Verdict.FAIL),
        ("F4", {"claim_figure": 42, "evidence_spans": []}, Verdict.INCONCLUSIVE),
        ("F5", {"absence_key": "x", "registry": {}, "registry_snapshot_hash": "a" * 64}, Verdict.PASS),
        ("F5", {"absence_key": "x", "registry": {"x": 1}, "registry_snapshot_hash": "a" * 64}, Verdict.FAIL),
        ("F5", {"absence_key": "x", "registry": {}}, Verdict.INCONCLUSIVE),
    ],
)
def test_primitives(key: str, context: dict[str, object], verdict: Verdict) -> None:
    assert execute_primitive(builtin_specs()[key], context).verdict == verdict


def test_safe_spec_rejects_code_and_bounds() -> None:
    base = builtin_specs()["F1"].model_dump()
    base["params"] = {"code": "generated program"}
    with pytest.raises(ValidationError):
        FalsifierSpec.model_validate(base)
    assert (
        execute_primitive(
            builtin_specs()["F1"].model_copy(update={"params": {"relative_tolerance": 0.8}}),
            {"price": 1, "users": 1, "claimed": 1},
        ).verdict
        == Verdict.INCONCLUSIVE
    )


def test_registry_market_and_expiry_fields() -> None:
    specs = builtin_specs("x")
    registry = FalsifierRegistry()
    digest = registry.add(specs["F1"])
    assert registry.get(digest) == specs["F1"]
    assert len(registry.values()) == 1
    selected, scores = FalsifierMarket().select([specs["F1"], specs["F2"]], budget_usd=0.0, max_tests=1, information_floor=0.1)
    assert len(selected) == 1
    assert len(scores) == 2
    costly = specs["F1"].model_copy(update={"estimated_cost": 1.0, "valid_from": datetime(2026, 8, 17, tzinfo=UTC)})
    assert FalsifierMarket().select([costly], budget_usd=0.0, max_tests=1)[0] == []
