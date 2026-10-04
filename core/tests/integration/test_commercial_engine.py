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
    commercial: dict[str, object] | None = None,
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
        "commercial": commercial or {"stage": "unknown"},
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


def test_engine_trace_observer_cannot_change_authoritative_decision(tmp_path: Path) -> None:
    engine = MiMicusEngine(f"sqlite:///{tmp_path / 'trace.db'}")
    payload = {"findings": [_finding("immutable-trace", status="replied", score=77)]}
    policy = _policy()

    baseline = engine.triage_prospects(payload, policy=policy, as_of=AS_OF)
    observed: list[object] = []

    def sink(event: object) -> None:
        observed.append(event)

    traced = engine.triage_prospects(payload, policy=policy, as_of=AS_OF, trace_sink=sink)

    assert traced == baseline
    assert traced.batch_hash == baseline.batch_hash
    assert len(observed) == 3


def test_engine_trace_sink_failure_does_not_gain_control_authority(tmp_path: Path) -> None:
    engine = MiMicusEngine(f"sqlite:///{tmp_path / 'trace-fail.db'}")
    payload = {"findings": [_finding("trace-failure", status="prepared", score=80)]}

    def broken_sink(_event: object) -> None:
        raise RuntimeError("observer unavailable")

    batch = engine.triage_prospects(
        payload,
        policy=_policy(),
        as_of=AS_OF,
        trace_sink=broken_sink,
    )

    assert batch.selected_by_lane["facebook"] == ("trace-failure",)


def test_laya_reading_trace_exposes_sanitized_commercial_evidence_state(tmp_path: Path) -> None:
    engine = MiMicusEngine(f"sqlite:///{tmp_path / 'commercial-trace.db'}")
    observed: list[object] = []

    engine.triage_prospects(
        {
            "findings": [
                _finding(
                    "proposal-proof",
                    status="replied",
                    commercial={
                        "stage": "proposal",
                        "evidence": [
                            {
                                "stage": "proposal",
                                "observedAt": "2026-10-01T17:30:00+00:00",
                                "sourceRef": "messenger:thread-42",
                                "summary": "Private detail must not be emitted by trace.",
                            }
                        ],
                    },
                )
            ]
        },
        policy=_policy(),
        as_of=AS_OF,
        trace_sink=observed.append,
    )

    reading = next(
        event.model_dump(mode="json")
        for event in observed
        if getattr(event, "event", None) == "laya_reading"
    )
    assert reading["commercial_stage"] == "proposal"
    assert reading["commercial_evidence_count"] == 1
    assert reading["commercial_stage_evidenced"] is True
    serialized = str(reading)
    assert "Private detail must not be emitted by trace." not in serialized
    assert "messenger:thread-42" not in serialized
