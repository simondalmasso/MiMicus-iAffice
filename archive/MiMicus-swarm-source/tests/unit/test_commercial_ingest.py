from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from mimicus.commercial.prospect_ingest import normalize_ledger, normalize_prospect


def _finding(
    *,
    id: str = "lead-1",
    status: str = "prepared",
    source_name: str = "Facebook",
    verified_at: str = "2026-10-01T10:00:00-03:00",
    active: bool = True,
) -> dict[str, object]:
    return {
        "id": id,
        "prospectType": "microjob",
        "title": "Need a small implementation",
        "company": "Buyer Co",
        "buyer": "Buyer",
        "location": "Remote",
        "description": "Concrete buyer need",
        "category": "tech",
        "sourceName": source_name,
        "sourceUrl": f"https://example.test/{id}",
        "directUrl": f"https://example.test/{id}/contact",
        "publishedAt": "2026-10-01T08:00:00-03:00",
        "verifiedAt": verified_at,
        "active": active,
        "argentinaEligible": True,
        "applicationMode": "direct",
        "workerFee": False,
        "salary": {"raw": "No publicado", "monthlyMin": None, "monthlyMax": None, "currency": "otra"},
        "scamRisk": "low",
        "rank": {"score": 90, "reason": "verified signal"},
        "evidence": [f"https://example.test/{id}"],
        "outreach": {
            "status": status,
            "channel": "messenger",
            "message": "short message",
            "contactedAt": None,
        },
    }


def test_normalize_replied_facebook_candidate() -> None:
    candidate = normalize_prospect(_finding(status="replied", source_name="Facebook"))

    assert candidate.prospect_id == "lead-1"
    assert candidate.lane == "facebook"
    assert candidate.outreach_status == "replied"
    assert candidate.outreach_channel == "messenger"
    assert candidate.setter_score == 90


def test_normalize_requires_timezone_aware_dates() -> None:
    row = _finding(verified_at="2026-10-01T10:00:00")

    with pytest.raises(ValueError, match="timezone"):
        normalize_prospect(row)


def test_normalize_ledger_preserves_active_and_terminal_rows() -> None:
    rows = normalize_ledger(
        {
            "findings": [
                _finding(id="a"),
                _finding(id="b", active=False, status="closed"),
            ]
        }
    )

    assert [row.prospect_id for row in rows] == ["a", "b"]
    assert rows[1].active is False
    assert rows[1].outreach_status == "closed"


def test_candidate_is_frozen() -> None:
    candidate = normalize_prospect(_finding())

    with pytest.raises(ValidationError):
        candidate.title = "mutated"  # type: ignore[misc]


def test_unknown_source_is_rejected_fail_closed() -> None:
    with pytest.raises(ValueError, match="sourceName"):
        normalize_prospect(_finding(source_name="Telegram"))


def test_absent_outcome_is_backward_compatible() -> None:
    row = _finding()
    row.pop("outcome", None)

    candidate = normalize_prospect(deepcopy(row))

    assert candidate.prospect_id == "lead-1"
