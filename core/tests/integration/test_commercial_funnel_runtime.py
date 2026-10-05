from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from mimicus.commercial.models import LeadDecisionPolicy
from mimicus.interfaces.cli import main
from mimicus.orchestration.engine import MiMicusEngine
from mimicus.providers.scripted import ScriptedProvider

AS_OF = datetime(2026, 10, 4, 3, 0, tzinfo=UTC)


def _finding(
    prospect_id: str,
    *,
    source_name: str = "Facebook",
    status: str = "replied",
    score: int = 80,
    commercial: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "id": prospect_id,
        "title": f"Lead {prospect_id}",
        "buyer": "Buyer",
        "sourceName": source_name,
        "sourceUrl": f"https://example.test/{prospect_id}",
        "directUrl": f"https://example.test/{prospect_id}/contact",
        "publishedAt": "2026-10-01T12:00:00+00:00",
        "verifiedAt": "2026-10-02T12:00:00+00:00",
        "active": True,
        "argentinaEligible": True,
        "workerFee": False,
        "scamRisk": "low",
        "rank": {"score": score},
        "outreach": {
            "status": status,
            "channel": "messenger" if source_name == "Facebook" else "reddit_comment",
            "contactedAt": "2026-10-03T00:00:00+00:00",
        },
        "commercial": commercial or {"stage": "unknown"},
    }


def _policy() -> LeadDecisionPolicy:
    return LeadDecisionPolicy(
        version="funnel-runtime-v1",
        max_work_per_lane=3,
        prepared_min_score=70,
        follow_up_after_hours={"messenger": 24, "reddit_comment": 24},
    )


def _ledger() -> dict[str, object]:
    return {
        "findings": [
            _finding(
                "proposal",
                commercial={
                    "stage": "proposal",
                    "evidence": [
                        {
                            "stage": "qualified",
                            "observedAt": "2026-10-03T00:00:00+00:00",
                            "sourceRef": "fixture:qualified",
                        },
                        {
                            "stage": "proposal",
                            "observedAt": "2026-10-03T12:00:00+00:00",
                            "sourceRef": "fixture:proposal",
                        },
                    ],
                },
            ),
            _finding(
                "won",
                source_name="Reddit",
                status="closed",
                commercial={
                    "stage": "won",
                    "evidence": [
                        {
                            "stage": "qualified",
                            "observedAt": "2026-10-02T00:00:00+00:00",
                            "sourceRef": "fixture:won-qualified",
                        },
                        {
                            "stage": "proposal",
                            "observedAt": "2026-10-02T12:00:00+00:00",
                            "sourceRef": "fixture:won-proposal",
                        },
                        {
                            "stage": "won",
                            "observedAt": "2026-10-03T12:00:00+00:00",
                            "sourceRef": "fixture:won",
                        },
                    ],
                },
            ),
        ]
    }


def test_engine_commercial_funnel_uses_authoritative_batch_without_provider_calls(
    tmp_path: Path,
) -> None:
    provider = ScriptedProvider()
    engine = MiMicusEngine(f"sqlite:///{tmp_path / 'funnel.db'}", provider=provider)

    snapshot = engine.commercial_funnel(_ledger(), policy=_policy(), as_of=AS_OF)

    assert snapshot.overall.lead_count == 2
    assert snapshot.overall.current_commercial_stage_counts["proposal"] == 1
    assert snapshot.overall.terminal_outcome_counts == {"won": 1}
    assert snapshot.overall.terminal_win_rate == 1.0
    assert snapshot.overall.qualified_to_proposal.advanced_count == 2
    assert snapshot.overall.proposal_to_terminal.advanced_count == 1
    assert provider.total_calls == 0
    assert "Buyer" not in snapshot.model_dump_json()
    assert "fixture:" not in snapshot.model_dump_json()


def test_cli_funnel_is_read_only_json_projection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setenv("MIMICUS_DATABASE_URL", "sqlite:///:memory:")
    ledger = tmp_path / "ledger.json"
    policy = tmp_path / "policy.json"
    ledger.write_text(json.dumps(_ledger()), encoding="utf-8")
    policy.write_text(json.dumps(_policy().model_dump(mode="json")), encoding="utf-8")

    rc = main(
        [
            "funnel",
            "--ledger-file",
            str(ledger),
            "--policy-file",
            str(policy),
            "--as-of",
            AS_OF.isoformat(),
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["overall"]["lead_count"] == 2
    assert payload["overall"]["terminal_outcome_counts"] == {"won": 1}
    assert payload["overall"]["terminal_win_rate"] == 1.0
    assert payload["snapshot_hash"]
    serialized = json.dumps(payload)
    assert "fixture:" not in serialized
    assert "Buyer" not in serialized
