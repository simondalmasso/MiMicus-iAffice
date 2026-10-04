from __future__ import annotations

from mimicus.claims.models import Claim


class ClaimGraph:
    def __init__(self) -> None:
        self.claims: dict[str, Claim] = {}
        self.edges: set[tuple[str, str, str]] = set()

    def add(self, claim: Claim) -> None:
        self.claims[claim.claim_id] = claim

    def relate(self, source_id: str, target_id: str, relation: str) -> None:
        if source_id not in self.claims or target_id not in self.claims:
            raise KeyError("claim graph edge references unknown claim")
        self.edges.add((source_id, target_id, relation))
