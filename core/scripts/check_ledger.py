from __future__ import annotations

import json

from mimicus.events.ledger import EventLedger
from mimicus.orchestration.replay import verify_replay

ledger = EventLedger("order-002-ledger-check")
ledger.append("run_started", {"fixture": "ledger-check"})
ledger.append("falsifier_executed", {"verdict": "FAIL", "spec_hash": "a" * 64})
ledger.append("run_completed", {"status": "answered"})
clean = verify_replay(ledger.events, ledger.head)
tampered = [event.model_dump() for event in ledger.events]
tampered[1]["payload"]["verdict"] = "PASS"
tamper = verify_replay(tampered)
wrong_snapshot = verify_replay(ledger.events, "f" * 64)
report = {
    "clean_verified": clean["verified"],
    "head": ledger.head,
    "tamper_detected": not bool(tamper["verified"]),
    "snapshot_mismatch_detected": not bool(wrong_snapshot["verified"]),
}
print(json.dumps(report, indent=2, sort_keys=True))
raise SystemExit(0 if all([report["clean_verified"], report["tamper_detected"], report["snapshot_mismatch_detected"]]) else 1)
