from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Claim:
    branch: str
    subject: str
    attribute: str
    value: str
    claim_type: str = "fact"  # fact | correction | note
    source_event_id: str = ""
    source_text: str = ""
    timestamp: int = 0
    tags: List[str] = field(default_factory=list)

    @property
    def slot(self) -> str:
        return f"{self.branch.strip().lower()}::{self.subject.strip().lower()}::{self.attribute.strip().lower()}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Event:
    event_id: str
    branch: str
    text: str
    event_type: str = "message"  # message | noise | query
    annotations: List[Dict[str, Any]] = field(default_factory=list)
    timestamp: int = 0
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Query:
    query_id: str
    text: str
    kind: str = "value"  # value | provenance | superseded_by | branch_list
    target_branch: Optional[str] = None
    subject: Optional[str] = None
    attribute: Optional[str] = None
    expected: Optional[str] = None
    expected_contains: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    @property
    def slot(self) -> Optional[str]:
        if self.target_branch is None or self.subject is None or self.attribute is None:
            return None
        return f"{self.target_branch.strip().lower()}::{self.subject.strip().lower()}::{self.attribute.strip().lower()}"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class FactRecord:
    fact_id: str
    slot: str
    value: str
    branch: str
    subject: str
    attribute: str
    source_event_id: str
    source_text: str
    admitted: bool = True
    superseded_by_fact_id: Optional[str] = None
    supersedes_fact_id: Optional[str] = None
    timestamp: int = 0
    tags: List[str] = field(default_factory=list)

    @property
    def current(self) -> bool:
        return self.superseded_by_fact_id is None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LedgerEntry:
    entry_id: str
    event_id: str
    branch: str
    raw_text: str
    admitted_claims: List[str] = field(default_factory=list)
    deduped_claims: List[str] = field(default_factory=list)
    rejected_claims: List[str] = field(default_factory=list)
    current_norm: float = 0.0
    energy: float = 0.0
    csi: float = 0.0
    energy_drift: float = 0.0
    invariant_violations: List[str] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
