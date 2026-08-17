from __future__ import annotations

from datetime import UTC, datetime

from mimicus.falsifiers.spec import FalsifierSpec


def builtin_specs(domain: str = "general") -> dict[str, FalsifierSpec]:
    common = {
        "domain": domain,
        "expected_information_gain": 0.9,
        "estimated_cost": 0.0,
        "estimated_latency": 1.0,
        "provenance": "MiMicus clean-room safe primitive derived from ORDER-002/K3 behavioral lineage",
        "valid_from": datetime(2026, 8, 17, tzinfo=UTC),
    }
    return {
        "F1": FalsifierSpec(id="F1.numeric_invariant", version="1.0.0", trigger="numeric arithmetic/unit/period claim", primitive="numeric_invariant", params={"relative_tolerance": 0.05}, oracle_kind="deterministic", **common),
        "F2": FalsifierSpec(id="F2.freshness", version="1.0.0", trigger="current/as-of claim", primitive="freshness", params={"max_age_days": 30}, oracle_kind="deterministic", **common),
        "F3": FalsifierSpec(id="F3.source_independence", version="1.0.0", trigger="multiple cited sources", primitive="source_independence", params={"min_independent": 2}, oracle_kind="deterministic", **common),
        "F4": FalsifierSpec(id="F4.citation_entailment", version="1.0.0", trigger="material numeric citation", primitive="citation_entailment", params={}, oracle_kind="deterministic", **common),
        "F5": FalsifierSpec(id="F5.counterexample_search", version="1.0.0", trigger="absence/universal-negative claim", primitive="counterexample_search", params={}, oracle_kind="registry", **common),
    }
