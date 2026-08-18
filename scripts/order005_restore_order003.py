from __future__ import annotations

import subprocess
from pathlib import Path

BASE = "1622a67b69737f4dc623bf7df0b9dfb6ac9d77da"
PATH = "src/mimicus/validation/order003_worker.py"
text = subprocess.check_output(["git", "show", f"{BASE}:{PATH}"], text=True)

# ORDER-005 explicit evidence semantics: historical fixture-driven probes stay explicit.
tam = '{"claim_statement": "TAM", "claim_type": "numeric", "price": 10.0, "users": 100.0, "price_period": "monthly", "claimed": 1000.0}'
text = text.replace(
    'result = engine.run(RunRequest(task="K3 TAM 12x mismatch", domain="finance", learn=True))',
    f'result = engine.run(RunRequest(task="K3 TAM 12x mismatch", domain="finance", scenario="tam_12x", fixture={tam}, learn=True))',
    1,
)
text = text.replace(
    'result = engine.run(RunRequest(task="K3 TAM 12x mismatch", domain="finance"))',
    f'result = engine.run(RunRequest(task="K3 TAM 12x mismatch", domain="finance", scenario="tam_12x", fixture={tam}))',
    1,
)

# ORDER-005 identity integrity: whitewashing probes must use a real material revision,
# not a forged arbitrary fingerprint. The forged path has its own rejection tests.
text = text.replace(
    "from mimicus.memory.gates import write_gate\n",
    "from mimicus.agents.identity import make_identity\nfrom mimicus.memory.gates import write_gate\n",
    1,
)
old_white = '''    child = "c" * 64
    fixture = {
        "claim_statement": "revised identity",
        "claim_type": "numeric",
        "price": 1.0,
        "users": 1.0,
        "claimed": 10.0,
        "identity_revisions": {
            base.name: {
                "fingerprint": child,
                "lineage_id": base_identity.lineage_id,
                "parent_fingerprint": base.fingerprint,
                "provenance": "ORDER-003 process whitewash probe",
            }
        },
    }
'''
new_white = '''    child_identity = make_identity(
        provider=base.provider,
        model_family=base.model,
        phenotype=base.name,
        tool_policy_hash=base.tool_hash,
        runtime_model_version=base.runtime_model_version,
        phenotype_version=base.phenotype_version,
        system_prompt_hash="c" * 64,
        tool_manifest_hash=base.tool_hash,
        policy_hash=base.policy_hash,
        provider_adapter_version=base.provider_adapter_version,
        parent_fingerprint=base.fingerprint,
        declared_lineage_id=base_identity.lineage_id,
    )
    child = child_identity.fingerprint
    fixture = {
        "claim_statement": "revised identity",
        "claim_type": "numeric",
        "price": 1.0,
        "users": 1.0,
        "claimed": 10.0,
        "identity_revisions": {
            base.name: {
                "system_prompt_hash": "c" * 64,
                "lineage_id": base_identity.lineage_id,
                "parent_fingerprint": base.fingerprint,
                "provenance": "ORDER-003 process whitewash probe",
            }
        },
    }
'''
if text.count(old_white) != 2:
    raise SystemExit(f"expected 2 whitewash/recovery anchors, got {text.count(old_white)}")
text = text.replace(old_white, new_white, 2)
Path(PATH).write_text(text, encoding="utf-8")

# The shared historical MCP helper now supplies structured evidence through the
# public MCP contract rather than relying on task words to synthesize a fixture.
worker = Path("src/mimicus/validation/worker.py")
w = worker.read_text(encoding="utf-8")
old = '''                        "domain": "finance",
                        "budget_usd": 0.0,
'''
new = '''                        "domain": "finance",
                        "evidence": [
                            {
                                "origin": "mcp://order003-tam",
                                "independence_cluster": "order003-fixture",
                                "content": "Explicit historical TAM evidence",
                                "extracted_facts": {"price": 10.0, "users": 100.0, "price_period": "monthly", "claimed": 1000.0},
                            }
                        ],
                        "budget_usd": 0.0,
'''
if old not in w:
    raise SystemExit("MCP helper anchor missing")
worker.write_text(w.replace(old, new, 1), encoding="utf-8")
print("ORDER005_ORDER003_HARNESS_RESTORED=YES")
