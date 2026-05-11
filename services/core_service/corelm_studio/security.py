from __future__ import annotations

import re
from typing import Any


SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{12,}"),
    re.compile(r"(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^'\"\s,}]+", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9_\-.=]{12,}", re.IGNORECASE),
]


def sanitize_text(value: str) -> str:
    sanitized = value
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)
    return sanitized


def sanitize_obj(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [sanitize_obj(item) for item in value]
    if isinstance(value, tuple):
        return tuple(sanitize_obj(item) for item in value)
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            lower_key = str(key).lower()
            if any(marker in lower_key for marker in ("api_key", "apikey", "token", "secret", "password")):
                cleaned[key] = "[REDACTED_SECRET]"
            else:
                cleaned[key] = sanitize_obj(item)
        return cleaned
    return value
