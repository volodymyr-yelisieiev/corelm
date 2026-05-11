from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .adapter import DeterministicTraceAdapter
from .base import MemorySystem
from .schema import Claim, Event, Query
from .utils import jaccard, stable_digest, word_count


class SlidingWindowSystem(MemorySystem):
    name = "sliding_window"

    def __init__(self, window_events: int = 12):
        self.window_events = window_events
        self.adapter = DeterministicTraceAdapter()
        self.reset(seed=0)

    def reset(self, seed: int = 0) -> None:
        self.seed = seed
        self.events: List[Event] = []
        self.claims: List[Claim] = []

    def step(self, event: Event) -> Dict[str, Any]:
        self.events.append(event)
        self.events = self.events[-self.window_events:]
        self.claims.extend(self.adapter.extract_claims(event))
        # only retain claims from visible event ids
        visible_ids = {ev.event_id for ev in self.events}
        self.claims = [claim for claim in self.claims if claim.source_event_id in visible_ids]
        return {"visible_events": len(self.events)}

    def _find(self, query: Query) -> Optional[Claim]:
        for claim in reversed(self.claims):
            if query.target_branch and claim.branch != query.target_branch:
                continue
            if query.subject and claim.subject != query.subject:
                continue
            if query.attribute and claim.attribute != query.attribute:
                continue
            return claim
        return None

    def answer(self, query: Query) -> str:
        claim = self._find(query)
        if claim is None:
            return "UNKNOWN"
        if query.kind == "value":
            return claim.value
        if query.kind == "provenance":
            return "UNKNOWN"
        if query.kind == "superseded_by":
            return "UNKNOWN"
        if query.kind == "branch_list":
            items = []
            for claim in self.claims:
                if claim.branch == (query.target_branch or "").lower():
                    items.append(f"{claim.subject}.{claim.attribute}={claim.value}")
            return "; ".join(items) if items else "UNKNOWN"
        return "UNKNOWN"

    def snapshot(self) -> Dict[str, Any]:
        return {
            "system": self.name,
            "events": [ev.to_dict() for ev in self.events],
            "claims": [claim.to_dict() for claim in self.claims],
        }

    def digest(self) -> str:
        return stable_digest(self.snapshot())

    def stats(self) -> Dict[str, Any]:
        return {
            "system": self.name,
            "durable_facts": len(self.claims),
            "current_facts": len(self.claims),
            "ledger_entries": len(self.events),
            "deduped_events": 0,
            "provenance_coverage": 0.0,
            "invariant_violations": 0,
            "max_state_norm": 0.0,
            "mean_state_norm": 0.0,
            "approx_memory_words": sum(word_count(ev.text) for ev in self.events),
        }


class LargeContextWindowSystem(SlidingWindowSystem):
    name = "large_context_window"

    def __init__(self):
        super().__init__(window_events=48)


class PeriodicSummarySystem(MemorySystem):
    name = "periodic_summary"

    def __init__(self, flush_every: int = 7, per_branch_capacity: int = 4):
        self.flush_every = flush_every
        self.per_branch_capacity = per_branch_capacity
        self.adapter = DeterministicTraceAdapter()
        self.reset(seed=0)

    def reset(self, seed: int = 0) -> None:
        self.seed = seed
        self.buffer: List[Claim] = []
        self.summary: Dict[str, List[Claim]] = {}
        self.steps = 0

    def _flush(self) -> None:
        # summarizes by keeping only the latest N claims per branch, losing provenance
        for claim in self.buffer:
            bucket = self.summary.setdefault(claim.branch, [])
            bucket.append(claim)
            bucket[:] = bucket[-self.per_branch_capacity:]
        self.buffer = []

    def step(self, event: Event) -> Dict[str, Any]:
        self.steps += 1
        self.buffer.extend(self.adapter.extract_claims(event))
        if self.steps % self.flush_every == 0:
            self._flush()
        return {"buffer_claims": len(self.buffer)}

    def _visible_claims(self) -> List[Claim]:
        claims = []
        for bucket in self.summary.values():
            claims.extend(bucket)
        claims.extend(self.buffer)
        return claims

    def answer(self, query: Query) -> str:
        candidates = self._visible_claims()
        for claim in reversed(candidates):
            if query.target_branch and claim.branch != query.target_branch:
                continue
            if query.subject and claim.subject != query.subject:
                continue
            if query.attribute and claim.attribute != query.attribute:
                continue
            if query.kind == "value":
                return claim.value
            return "UNKNOWN"
        if query.kind == "branch_list":
            out = []
            for claim in candidates:
                if claim.branch == (query.target_branch or "").lower():
                    out.append(f"{claim.subject}.{claim.attribute}={claim.value}")
            return "; ".join(out) if out else "UNKNOWN"
        return "UNKNOWN"

    def snapshot(self) -> Dict[str, Any]:
        return {
            "system": self.name,
            "summary": {k: [c.to_dict() for c in v] for k, v in self.summary.items()},
            "buffer": [c.to_dict() for c in self.buffer],
        }

    def digest(self) -> str:
        return stable_digest(self.snapshot())

    def stats(self) -> Dict[str, Any]:
        claims = self._visible_claims()
        approx_words = sum(word_count(claim.value) for claim in claims)
        return {
            "system": self.name,
            "durable_facts": len(claims),
            "current_facts": len(claims),
            "ledger_entries": self.steps,
            "deduped_events": 0,
            "provenance_coverage": 0.0,
            "invariant_violations": 0,
            "max_state_norm": 0.0,
            "mean_state_norm": 0.0,
            "approx_memory_words": approx_words,
        }


class RetrievalOnlySystem(MemorySystem):
    name = "retrieval_only"

    def __init__(self):
        self.adapter = DeterministicTraceAdapter()
        self.reset(seed=0)

    def reset(self, seed: int = 0) -> None:
        self.seed = seed
        self.claims: List[Claim] = []
        self.raw_events: List[Event] = []

    def step(self, event: Event) -> Dict[str, Any]:
        self.raw_events.append(event)
        self.claims.extend(self.adapter.extract_claims(event))
        return {"claims": len(self.claims)}

    def _score_claim(self, query: Query, claim: Claim) -> float:
        score = jaccard(query.text, claim.source_text + " " + claim.value)
        if query.target_branch and claim.branch == query.target_branch:
            score += 0.3
        if query.subject and claim.subject == query.subject:
            score += 0.2
        if query.attribute and claim.attribute == query.attribute:
            score += 0.2
        return score

    def answer(self, query: Query) -> str:
        if not self.claims:
            return "UNKNOWN"
        ranked = sorted(self.claims, key=lambda c: self._score_claim(query, c), reverse=True)
        best = ranked[0]
        if query.kind == "value":
            return best.value
        if query.kind == "provenance":
            return "UNKNOWN"
        if query.kind == "superseded_by":
            return "UNKNOWN"
        if query.kind == "branch_list":
            branch = (query.target_branch or "").lower()
            vals = [f"{c.subject}.{c.attribute}={c.value}" for c in ranked if c.branch == branch][:6]
            return "; ".join(vals) if vals else "UNKNOWN"
        return "UNKNOWN"

    def snapshot(self) -> Dict[str, Any]:
        return {
            "system": self.name,
            "claims": [c.to_dict() for c in self.claims],
        }

    def digest(self) -> str:
        return stable_digest(self.snapshot())

    def stats(self) -> Dict[str, Any]:
        return {
            "system": self.name,
            "durable_facts": len(self.claims),
            "current_facts": len(self.claims),
            "ledger_entries": len(self.raw_events),
            "deduped_events": 0,
            "provenance_coverage": 0.0,
            "invariant_violations": 0,
            "max_state_norm": 0.0,
            "mean_state_norm": 0.0,
            "approx_memory_words": sum(word_count(ev.text) for ev in self.raw_events),
        }
