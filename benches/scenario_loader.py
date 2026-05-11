from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

from corelm.schema import Event, Query


def load_scenarios(root: str | Path) -> List[Dict]:
    root = Path(root)
    scenarios: List[Dict] = []
    for path in sorted(root.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        events = [Event(**event) for event in raw["events"]]
        queries = [Query(**query) for query in raw["queries"]]
        scenarios.append({
            "name": raw["name"],
            "description": raw.get("description", ""),
            "tags": raw.get("tags", []),
            "threshold": raw.get("threshold", 1.0),
            "events": events,
            "queries": queries,
        })
    return scenarios
