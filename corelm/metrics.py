from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Dict, List


@dataclass
class SystemSummary:
    system: str
    scenarios: int
    passed_scenarios: int
    query_accuracy: float
    replay_determinism: float
    provenance_coverage: float
    invariant_violation_rate: float
    max_state_norm: float
    mean_state_norm: float
    total_durable_facts: int
    total_deduped_events: int
    approx_memory_words: int
    notes: List[str]

    def to_dict(self) -> Dict[str, float | int | str | list]:
        return asdict(self)
