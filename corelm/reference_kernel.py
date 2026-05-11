from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Optional

import numpy as np

from .adapter import DeterministicTraceAdapter
from .base import MemorySystem
from .schema import Claim, Event, FactRecord, LedgerEntry, Query
from .utils import bounded, jaccard, normalize_value, stable_digest, word_count
from .vendor.lucid_mind_v15_core_ref import LucidMindCoreV15, TextHashEmbeddingSource


class ReferenceKernel(MemorySystem):
    """
    Deterministic reference implementation of Core LM for publication-level
    benchmarking.

    Architecture:
        adapter -> numeric excitation/state update -> normalize -> verify ->
        append-only ledger -> current truth state
    """

    name = "reference_kernel"

    def __init__(self, n: int = 96, history_window: int = 256,
                 dedupe_threshold: float = 0.86, state_norm_limit: float = 50.0):
        self.n = n
        self.history_window = history_window
        self.dedupe_threshold = dedupe_threshold
        self.state_norm_limit = state_norm_limit
        self.adapter = DeterministicTraceAdapter()
        self.seed = 0
        self._source: Optional[TextHashEmbeddingSource] = None
        self._core: Optional[LucidMindCoreV15] = None
        self.reset(seed=0)

    def reset(self, seed: int = 0) -> None:
        self.seed = int(seed)
        self._core = LucidMindCoreV15(n=self.n, k=self.n // 3, m=self.n // 3, p=self.n - 2 * (self.n // 3), window_k=self.history_window)
        self._source = TextHashEmbeddingSource(n=self.n, seed=1337 + self.seed)
        self.ledger: List[LedgerEntry] = []
        self.facts: Dict[str, FactRecord] = {}
        self.current_by_slot: Dict[str, str] = {}
        self.claim_text_index: Dict[str, List[str]] = {}
        self.event_texts: Dict[str, str] = {}
        self.event_branches: Dict[str, str] = {}
        self.branch_slots: Dict[str, set[str]] = {}
        self.deduped_events = 0
        self.rejected_claims = 0
        self.invariant_violations_total = 0
        self.max_state_norm = 0.0

    @property
    def core(self) -> LucidMindCoreV15:
        assert self._core is not None
        return self._core

    @property
    def source(self) -> TextHashEmbeddingSource:
        assert self._source is not None
        return self._source

    def _fact_id(self, claim: Claim, ordinal: int) -> str:
        return stable_digest({
            "slot": claim.slot,
            "value": claim.value,
            "event": claim.source_event_id,
            "ordinal": ordinal,
        })[:16]

    def _similar_to_existing(self, claim: Claim) -> bool:
        existing_fact_id = self.current_by_slot.get(claim.slot)
        if not existing_fact_id:
            return False
        existing = self.facts[existing_fact_id]
        if normalize_value(existing.value) == normalize_value(claim.value):
            return True
        similarity = jaccard(existing.value, claim.value)
        return similarity >= self.dedupe_threshold

    def _apply_claim(self, claim: Claim, ordinal: int, ledger_entry: LedgerEntry) -> None:
        self.branch_slots.setdefault(claim.branch, set())
        self.branch_slots[claim.branch].add(claim.slot)

        if self._similar_to_existing(claim):
            ledger_entry.deduped_claims.append(claim.slot)
            self.deduped_events += 1
            return

        fact_id = self._fact_id(claim, ordinal=ordinal)
        previous_fact_id = self.current_by_slot.get(claim.slot)
        record = FactRecord(
            fact_id=fact_id,
            slot=claim.slot,
            value=claim.value,
            branch=claim.branch,
            subject=claim.subject,
            attribute=claim.attribute,
            source_event_id=claim.source_event_id,
            source_text=claim.source_text,
            timestamp=claim.timestamp,
            tags=list(claim.tags),
        )
        if previous_fact_id:
            self.facts[previous_fact_id].superseded_by_fact_id = fact_id
            record.supersedes_fact_id = previous_fact_id
        self.facts[fact_id] = record
        self.current_by_slot[claim.slot] = fact_id
        ledger_entry.admitted_claims.append(claim.slot)

    def _check_invariants(self) -> List[str]:
        violations: List[str] = []
        state_norm = float(np.linalg.norm(self.core.S))
        self.max_state_norm = max(self.max_state_norm, state_norm)
        if not bounded(state_norm):
            violations.append("state_norm_not_finite")
        if state_norm > self.state_norm_limit:
            violations.append("state_norm_exceeded_limit")
        for slot, fact_id in self.current_by_slot.items():
            record = self.facts[fact_id]
            if record.slot != slot:
                violations.append(f"slot_mismatch:{slot}")
            if not record.current:
                violations.append(f"noncurrent_slot_pointer:{slot}")
            if not record.source_event_id:
                violations.append(f"missing_provenance:{slot}")
        return violations

    def step(self, event: Event) -> Dict[str, Any]:
        self.event_texts[event.event_id] = event.text
        self.event_branches[event.event_id] = event.branch
        metrics = self.core.update(self.source, event.text)
        entry = LedgerEntry(
            entry_id=f"l{len(self.ledger)+1}",
            event_id=event.event_id,
            branch=event.branch,
            raw_text=event.text,
            current_norm=float(np.linalg.norm(self.core.S)),
            energy=metrics.energy,
            csi=metrics.csi,
            energy_drift=metrics.energy_drift,
        )
        claims = self.adapter.extract_claims(event)
        for ordinal, claim in enumerate(claims, start=1):
            self._apply_claim(claim, ordinal=ordinal, ledger_entry=entry)
        entry.invariant_violations = self._check_invariants()
        self.invariant_violations_total += len(entry.invariant_violations)
        self.ledger.append(entry)
        return {
            "admitted_claims": list(entry.admitted_claims),
            "deduped_claims": list(entry.deduped_claims),
            "state_norm": entry.current_norm,
            "energy": entry.energy,
            "invariant_violations": list(entry.invariant_violations),
        }

    def _current_record(self, query: Query) -> Optional[FactRecord]:
        if query.slot is None:
            return None
        fact_id = self.current_by_slot.get(query.slot)
        if fact_id is None:
            return None
        return self.facts[fact_id]

    def answer(self, query: Query) -> str:
        if query.kind == "value":
            record = self._current_record(query)
            return record.value if record else "UNKNOWN"
        if query.kind == "provenance":
            record = self._current_record(query)
            if not record:
                return "UNKNOWN"
            return f"{record.source_event_id}: {record.source_text}"
        if query.kind == "superseded_by":
            record = self._current_record(query)
            if not record:
                return "UNKNOWN"
            if record.supersedes_fact_id is None:
                return "NONE"
            old = self.facts[record.supersedes_fact_id]
            return f"{old.value} -> {record.value}"
        if query.kind == "branch_list":
            branch = (query.target_branch or "").strip().lower()
            slots = sorted(self.branch_slots.get(branch, set()))
            values = []
            for slot in slots:
                fact_id = self.current_by_slot.get(slot)
                if fact_id:
                    rec = self.facts[fact_id]
                    values.append(f"{rec.subject}.{rec.attribute}={rec.value}")
            return "; ".join(values) if values else "UNKNOWN"
        return "UNKNOWN"

    def snapshot(self) -> Dict[str, Any]:
        return {
            "system": self.name,
            "seed": self.seed,
            "numeric_state": self.core.snapshot(),
            "current_by_slot": dict(self.current_by_slot),
            "facts": {fact_id: rec.to_dict() for fact_id, rec in sorted(self.facts.items())},
            "ledger": [entry.to_dict() for entry in self.ledger],
        }

    def digest(self) -> str:
        return stable_digest(self.snapshot())

    def stats(self) -> Dict[str, Any]:
        provenance_total = len(self.facts)
        provenance_good = sum(1 for rec in self.facts.values() if rec.source_event_id and rec.source_text)
        norms = [entry.current_norm for entry in self.ledger] or [0.0]
        approx_words = sum(word_count(entry.raw_text) for entry in self.ledger)
        return {
            "system": self.name,
            "durable_facts": len(self.facts),
            "current_facts": len(self.current_by_slot),
            "ledger_entries": len(self.ledger),
            "deduped_events": self.deduped_events,
            "provenance_coverage": provenance_good / max(1, provenance_total),
            "invariant_violations": self.invariant_violations_total,
            "max_state_norm": max(norms),
            "mean_state_norm": float(sum(norms) / max(1, len(norms))),
            "approx_memory_words": approx_words,
        }
