from __future__ import annotations

import json
from pathlib import Path

from mimicus.falsifiers.builtins import builtin_specs
from mimicus.falsifiers.k3_compat import compatibility_vectors
from mimicus.germinal.center import germinal_demo
from mimicus.security import dynamic_code_execution_findings, spec_rejects_source_payload

root = Path(__file__).resolve().parents[1]
findings = dynamic_code_execution_findings((root / "src" / "mimicus").rglob("*.py"))
vectors = compatibility_vectors()
germinal = germinal_demo()
report = {
    "no_dynamic_code_execution": findings == [],
    "dynamic_findings": findings,
    "source_payload_rejected": spec_rejects_source_payload(builtin_specs()["F1"].model_dump()),
    "k3_compatibility": all(bool(vector["pass"]) for vector in vectors),
    "k3_vectors": vectors,
    "germinal_reject_then_promote": germinal["rejected_decision"] == "REJECT" and germinal["promoted_decision"] == "PROMOTE",
}
print(json.dumps(report, indent=2, sort_keys=True))
raise SystemExit(0 if all([report["no_dynamic_code_execution"], report["source_payload_rejected"], report["k3_compatibility"], report["germinal_reject_then_promote"]]) else 1)
