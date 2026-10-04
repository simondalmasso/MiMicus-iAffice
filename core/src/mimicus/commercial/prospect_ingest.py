from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from mimicus.commercial.models import LeadCandidate

_LANES = {
    "facebook": "facebook",
    "reddit": "reddit",
}


def normalize_prospect(row: Mapping[str, Any]) -> LeadCandidate:
    if "active" not in row:
        raise ValueError("active is required")

    source_name = str(row.get("sourceName", "")).strip()
    lane = _LANES.get(source_name.lower())
    if lane is None:
        raise ValueError(f"unsupported sourceName for commercial gate: {source_name!r}")

    rank = row.get("rank")
    if not isinstance(rank, Mapping):
        raise ValueError("rank must be an object")

    outreach = row.get("outreach")
    if not isinstance(outreach, Mapping):
        raise ValueError("outreach must be an object")

    commercial = row.get("commercial")
    if commercial is None:
        commercial = {"stage": "unknown"}
    elif not isinstance(commercial, Mapping):
        raise ValueError("commercial must be an object")

    return LeadCandidate.model_validate(
        {
            "prospect_id": str(row.get("id", "")),
            "source_name": source_name,
            "lane": lane,
            "buyer": row.get("buyer"),
            "title": str(row.get("title", "")),
            "active": row["active"],
            "argentina_eligible": row.get("argentinaEligible"),
            "worker_fee": row.get("workerFee"),
            "scam_risk": row.get("scamRisk"),
            "setter_score": rank.get("score"),
            "outreach_status": str(outreach.get("status", "")),
            "outreach_channel": outreach.get("channel"),
            "published_at": row.get("publishedAt"),
            "verified_at": row.get("verifiedAt"),
            "contacted_at": outreach.get("contactedAt"),
            "source_url": row.get("sourceUrl"),
            "direct_url": row.get("directUrl"),
            "commercial": {
                "stage": commercial.get("stage", "unknown"),
                "updated_at": commercial.get("updatedAt"),
                "note": commercial.get("note"),
            },
        }
    )


def normalize_ledger(payload: Mapping[str, Any]) -> list[LeadCandidate]:
    findings = payload.get("findings")
    if not isinstance(findings, list):
        raise ValueError("ledger findings must be a list")
    return [normalize_prospect(row) for row in findings]
