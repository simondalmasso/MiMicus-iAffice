from __future__ import annotations

import json
from pathlib import Path

from mimicus.commercial.models import LeadDecisionPolicy

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_cockpit_has_live_observer_mode_without_commercial_decision_logic() -> None:
    app = (REPO_ROOT / "public" / "app.js").read_text(encoding="utf-8")

    assert "local-live-observer" in app
    assert "/api/activity?since=" in app
    assert "commercial_stage" in app
    assert "commercial_evidence_count" in app
    assert "commercial_stage_evidenced" in app
    assert "next_action" in app
    for event_name in ("lead_ingested", "laya_reading", "decision_emitted", "batch_complete", "observer_error"):
        assert event_name in app

    # Cockpit renders decisions; it must not reproduce the policy engine.
    assert "max_work_per_lane" not in app
    assert "follow_up_after_hours" not in app
    assert "setter_score >" not in app
    assert "rank.score" not in app
    assert "source_ref" not in app
    assert "sourceRef" not in app


def test_default_live_policy_covers_current_setter_channels() -> None:
    path = REPO_ROOT / "core" / "config" / "commercial-policy-v1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    policy = LeadDecisionPolicy.model_validate(payload)

    assert policy.max_work_per_lane == 3
    assert policy.follow_up_after_hours["messenger"] == 24
    assert policy.follow_up_after_hours["post-comment"] == 24
