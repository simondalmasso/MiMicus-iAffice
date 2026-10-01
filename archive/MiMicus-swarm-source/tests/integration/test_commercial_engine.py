from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from mimicus.commercial.models import LeadDecisionPolicy
from mimicus.orchestration.engine import MiMicusEngine
from mimicus.providers.scripted import ScriptedProvider

AS_OF = datetime(2026, 10, 1, 18, 0, tzinfo=UTC)


def _finding(
    prospect_id: str,
    *,
    source_name: str = "Facebook",
    status: str = "prepared",
    score: float = 80,
) -> dict[str, object]:
    return {
        "id": prospect_id,
        "title": f"Lead {prospect_id}",
        "buyer": "Buyer",
        "sourceName": source_name,
        "sourceUrl": f"https://example.test/{prospect_id}",
        "directUrl": f"https://example.test/{prospect_id}/contact",
        "publishedAt": "2026-09-30T12:00:00-03:00",
        "verifiedAt": "2026-10-01T12:00:00-03:00",
        "active": True,
        "argentinaEligible": True,
        "workerFee": False,
        "scamRisk": "low",
        "rank": {"score": score},
        "outreach": {
            "status": status,
            "channel": "messenger" if source_name == "Facebook" else "reddit_comment",
            "contactedAt": None,
        },
    }


def _policy() -> LeadDecisionPolicy:
    return LeadDecisionPolicy(
        version="integration-v1",
        max_work_per_lane=3,
        follow_up_after_hours={"messenger": 24, "reddit_comment": 24},
    )


def test_engine_triage_prospects_uses_runtime_service(tmp_path: Path) -> None:
    provider = ScriptedProvider()
    engine = MiMicusEngine(f"sqlite:///{tmp_path / 'commercial.db'}", provider=provider)

    batch = engine.triage_prospects(
        {
            "findings": [
                _finding("fb-prepared", score=99),
                _finding("fb-replied", status="replied", score=50),
                _finding("rd-prepared", source_name="Reddit", score=88),
            ]
        },
        policy=_policy(),
        as_of=AS_OF,
    )

    assert batch.selected_by_lane["facebook"] == ("fb-replied", "fb-prepared")
    assert batch.selected_by_lane["reddit"] == ("rd-prepared",)
    assert engine.services.lead_decision is not None


def test_engine_triage_has_no_provider_calls_or_telemetry_mutation(tmp_path: Path) -> None:
    provider = ScriptedProvider()
    engine = MiMicusEngine(f"sqlite:///{tmp_path / 'commercial.db'}", provider=provider)
    before = engine.services.telemetry.snapshot()

    engine.triage_prospects(
        {"findings": [_finding("fb-prepared")]},
        policy=_policy(),
        as_of=AS_OF,
    )

    assert provider.total_calls == 0
    assert engine.services.telemetry.snapshot() == before == {}
