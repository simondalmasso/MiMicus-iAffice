from __future__ import annotations

from mimicus.agents.auditions import CANARY_BANK, audition
from mimicus.agents.bankruptcy import evaluate_bankruptcy, recover
from mimicus.agents.calibration import CalibrationLedger, CalibrationRecord
from mimicus.agents.fingerprints import AgentFingerprintInput
from mimicus.coalition.selector import AgentCandidate, correlation, select_coalition
from mimicus.coalition.sparse_comm import sparse_edges
from mimicus.coalition.threat_profile import profile_task
from mimicus.coalition.topology import topology_for_size
from mimicus.types import BankruptcyState


def test_all_canary_categories() -> None:
    assert len(CANARY_BANK) == 6
    for category, (_, token) in CANARY_BANK.items():
        assert audition("fp", "d", category, token).passed
        assert not audition("fp", "d", category, "wrong").passed


def test_calibration_domain_scope_bankruptcy_and_recovery() -> None:
    ledger = CalibrationLedger()
    record = ledger.get("fp", "finance")
    assert record.trust == 0.5
    for _ in range(3):
        record.update(predicted_probability=0.8, outcome=False, canary=True)
    bankruptcy = evaluate_bankruptcy(record)
    assert bankruptcy.state == BankruptcyState.BANKRUPT
    assert recover(bankruptcy, recovery_audition_passed=False).state == BankruptcyState.BANKRUPT
    assert recover(bankruptcy, recovery_audition_passed=True).state == BankruptcyState.ACTIVE
    assert ledger.direct_trust("fp", "medical") == 0.5

    low = CalibrationRecord("fp2", "d")
    for _ in range(5):
        low.update(predicted_probability=0.9, outcome=False)
    assert evaluate_bankruptcy(low).state == BankruptcyState.BANKRUPT


def test_fingerprint_changes_materially() -> None:
    base = AgentFingerprintInput(
        provider="a",
        model="m",
        model_version="1",
        system_prompt_hash="p",
        tool_manifest_hash="t",
        policy_hash="x",
    )
    changed = base.model_copy(update={"model_version": "2"})
    assert base.fingerprint != changed.fingerprint


def _candidate(name: str, provider: str, model: str, prompt: str, tool: str, caps: set[str]) -> AgentCandidate:
    return AgentCandidate(name, name, frozenset(caps), provider, model, prompt, tool)


def test_correlation_and_dynamic_morphology() -> None:
    clone1 = _candidate("c1", "p", "m", "q", "t", {"numeric"})
    clone2 = _candidate("c2", "p", "m", "q", "t", {"numeric"})
    distinct = _candidate("d", "z", "n", "r", "u", {"source", "freshness", "independence"})
    assert correlation(clone1, clone2) >= 0.75
    assert correlation(clone1, distinct) == 0.0

    simple = profile_task("numeric TAM price", "x")
    mixed = profile_task("numeric current source citation echo", "x")
    candidates = [clone1, clone2, distinct, _candidate("s", "s", "s", "s", "s", {"synthesize"})]
    selected_simple, _ = select_coalition(simple, candidates, 4)
    selected_mixed, rationale = select_coalition(mixed, candidates, 4)
    assert len(selected_simple) == 1
    assert len(selected_mixed) >= 2
    assert rationale["uncovered_capabilities"] == []
    assert topology_for_size(1, 0.2) == "solo"
    assert topology_for_size(2, 0.5) == "paired"
    assert topology_for_size(3, 0.8) == "sparse-star"
    assert sparse_edges(["a", "b", "c"], 0.4, k=2)
    assert sparse_edges(["a", "b"], 0.01) == []
