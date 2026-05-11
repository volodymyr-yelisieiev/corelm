from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .reference_kernel import ReferenceKernel
from .schema import Event, Query
from .utils import stable_digest


class CoreLMProduct:
    """
    Local, installable reference product built on top of the deterministic
    Core LM reference kernel.

    Scope:
    - single-user / single-process operation
    - append-only event log persisted as JSON
    - structured fact ingestion with provenance and replay verification

    This is intentionally a local reference product, not a hosted SaaS.
    """

    def __init__(self, seed: int = 0) -> None:
        self.seed = int(seed)
        self.kernel = ReferenceKernel()
        self.reset(seed=seed)

    def reset(self, seed: Optional[int] = None) -> None:
        if seed is not None:
            self.seed = int(seed)
        self.kernel.reset(seed=self.seed)
        self.events: List[Event] = []
        self._counter = 0

    def _next_timestamp(self) -> int:
        self._counter += 1
        return self._counter

    def _event_id(self, payload: Dict[str, Any]) -> str:
        return stable_digest(payload)[:12]

    def ingest_text(self, branch: str, text: str, annotations: Optional[List[Dict[str, Any]]] = None,
                    event_type: str = 'message', meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        timestamp = self._next_timestamp()
        annotations = list(annotations or [])
        payload = {
            'branch': branch,
            'text': text,
            'annotations': annotations,
            'event_type': event_type,
            'timestamp': timestamp,
            'meta': meta or {},
        }
        event = Event(
            event_id=self._event_id(payload),
            branch=branch,
            text=text,
            event_type=event_type,
            annotations=annotations,
            timestamp=timestamp,
            meta=dict(meta or {}),
        )
        result = self.kernel.step(event)
        self.events.append(event)
        return {
            'event_id': event.event_id,
            'digest': self.kernel.digest(),
            'result': result,
        }

    def ingest_fact(self, branch: str, subject: str, attribute: str, value: str,
                    text: Optional[str] = None, claim_type: str = 'fact',
                    tags: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        text = text or f"{subject} {attribute} = {value}"
        annotations = [{
            'branch': branch,
            'subject': subject,
            'attribute': attribute,
            'value': value,
            'claim_type': claim_type,
            'tags': list(tags or []),
        }]
        return self.ingest_text(branch=branch, text=text, annotations=annotations)

    def correct_fact(self, branch: str, subject: str, attribute: str, value: str,
                     text: Optional[str] = None, tags: Optional[Iterable[str]] = None) -> Dict[str, Any]:
        text = text or f"Correction: {subject} {attribute} = {value}"
        return self.ingest_fact(branch=branch, subject=subject, attribute=attribute,
                                value=value, text=text, claim_type='correction', tags=tags)

    def get_value(self, branch: str, subject: str, attribute: str) -> str:
        query = Query(query_id='q-value', text=f'{subject}.{attribute}', kind='value',
                      target_branch=branch, subject=subject, attribute=attribute)
        return self.kernel.answer(query)

    def get_provenance(self, branch: str, subject: str, attribute: str) -> str:
        query = Query(query_id='q-prov', text=f'why {subject}.{attribute}', kind='provenance',
                      target_branch=branch, subject=subject, attribute=attribute)
        return self.kernel.answer(query)

    def get_supersession(self, branch: str, subject: str, attribute: str) -> str:
        query = Query(query_id='q-sup', text=f'supersession {subject}.{attribute}', kind='superseded_by',
                      target_branch=branch, subject=subject, attribute=attribute)
        return self.kernel.answer(query)

    def list_branch(self, branch: str) -> str:
        query = Query(query_id='q-branch', text=f'list {branch}', kind='branch_list', target_branch=branch)
        return self.kernel.answer(query)

    def export_state(self) -> Dict[str, Any]:
        return {
            'seed': self.seed,
            'events': [event.to_dict() for event in self.events],
            'kernel_snapshot': self.kernel.snapshot(),
            'digest': self.kernel.digest(),
            'stats': self.kernel.stats(),
        }

    def save_session(self, path: str | Path) -> Path:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.export_state(), ensure_ascii=False, indent=2), encoding='utf-8')
        return path

    @classmethod
    def load_session(cls, path: str | Path) -> 'CoreLMProduct':
        path = Path(path)
        payload = json.loads(path.read_text(encoding='utf-8'))
        obj = cls(seed=int(payload.get('seed', 0)))
        obj.reset(seed=int(payload.get('seed', 0)))
        for raw_event in payload.get('events', []):
            event = Event(**raw_event)
            obj.kernel.step(event)
            obj.events.append(event)
            obj._counter = max(obj._counter, int(event.timestamp))
        return obj

    def replay_verify(self) -> Dict[str, Any]:
        replay = self.kernel.replay(self.events, [], seed=self.seed)
        return {
            'expected_digest': self.kernel.digest(),
            'replay_digest': replay['digest'],
            'ok': replay['digest'] == self.kernel.digest(),
        }
