from __future__ import annotations

from typing import Any, Dict, List

from .schema import Event, Query


class MemorySystem:
    name: str = "memory_system"

    def reset(self, seed: int = 0) -> None:
        raise NotImplementedError

    def step(self, event: Event) -> Dict[str, Any]:
        raise NotImplementedError

    def answer(self, query: Query) -> str:
        raise NotImplementedError

    def snapshot(self) -> Dict[str, Any]:
        raise NotImplementedError

    def digest(self) -> str:
        raise NotImplementedError

    def replay(self, events: List[Event], queries: List[Query], seed: int = 0) -> Dict[str, Any]:
        self.reset(seed=seed)
        for event in events:
            self.step(event)
        answers = [self.answer(q) for q in queries]
        return {"digest": self.digest(), "answers": answers}

    def stats(self) -> Dict[str, Any]:
        raise NotImplementedError
