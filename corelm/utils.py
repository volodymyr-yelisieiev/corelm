from __future__ import annotations

import hashlib
import json
import math
import re
from typing import Any, Sequence


def normalize_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\-\+\./_= ]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_value(text: str) -> str:
    return re.sub(r"\s+", " ", str(text).strip())


def token_set(text: str) -> set[str]:
    return {tok for tok in normalize_text(text).split(" ") if tok}


def jaccard(a: str, b: str) -> float:
    sa, sb = token_set(a), token_set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / max(1, len(sa | sb))


def stable_digest(obj: Any) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def bounded(value: float) -> bool:
    return math.isfinite(value)


def word_count(text: str) -> int:
    return len(normalize_text(text).split())


def contains_all(answer: str, needles: Sequence[str]) -> bool:
    answer_n = normalize_text(answer)
    return all(normalize_text(n) in answer_n for n in needles)
