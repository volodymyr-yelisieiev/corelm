from __future__ import annotations

import re
from typing import Any


SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_\-]{12,}"),
    re.compile(r"(api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?[^'\"\s,}]+", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9_\-.=]{12,}", re.IGNORECASE),
    re.compile(r"Basic\s+[A-Za-z0-9+/=]{8,}", re.IGNORECASE),
    re.compile(r"(authorization|cookie|set-cookie)\s*[:=]\s*['\"]?[^'\"\n,}]+", re.IGNORECASE),
]

SAFE_TOKEN_COUNT_KEYS = {
    "token_ids",
    "decoded_tokens",
    "token_trace",
    "token_trace_hash",
    "token_trace_hash_repeat_rate",
    "per_token_timestamps_ms",
    "actual_generated_token_count",
    "supports_token_ids",
    "supports_token_text",
    "supports_per_token_timestamps",
    "supports_top_k",
    "exact_token_sequence_repeat_rate",
    "prefix_stability_at_1",
    "prefix_stability_at_5",
    "prefix_stability_at_10",
    "raw_token_count",
    "canonical_token_count",
    "void_token_count",
    "max_new_tokens",
    "prompt_token_count",
    "total_token_count",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "prompt_tokens_per_second",
    "generation_tokens_per_second",
    "end_to_end_tokens_per_second",
    "compression_throughput_tokens_per_sec",
    "token_proxy_before",
    "token_proxy_after",
}


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
            token_key_is_safe_metric = lower_key in SAFE_TOKEN_COUNT_KEYS
            if not token_key_is_safe_metric and any(
                marker in lower_key
                for marker in ("api_key", "apikey", "token", "secret", "password", "authorization", "cookie")
            ):
                cleaned[key] = "[REDACTED_SECRET]"
            else:
                cleaned[key] = sanitize_obj(item)
        return cleaned
    return value
