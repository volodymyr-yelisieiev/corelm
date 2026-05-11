from __future__ import annotations

from typing import List

from .schema import Claim, Event
from .utils import normalize_value


class DeterministicTraceAdapter:
    """
    Deterministic adapter for benchmark traces.

    Traces provide natural-language text plus explicit annotations. The adapter
    is the external extraction layer: it produces structured claims and never
    mutates core state.
    """

    def extract_claims(self, event: Event) -> List[Claim]:
        claims: List[Claim] = []
        for item in event.annotations:
            branch = (item.get("branch") or event.branch).strip().lower()
            subject = item["subject"].strip().lower()
            attribute = item["attribute"].strip().lower()
            value = normalize_value(item["value"])
            claim_type = item.get("claim_type", "fact")
            claim = Claim(
                branch=branch,
                subject=subject,
                attribute=attribute,
                value=value,
                claim_type=claim_type,
                source_event_id=event.event_id,
                source_text=event.text,
                timestamp=event.timestamp,
                tags=list(item.get("tags", [])),
            )
            claims.append(claim)
        return claims
