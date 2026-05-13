from __future__ import annotations

from typing import Any

from .security import sanitize_obj


OLLAMA_USAGE_FIELDS = (
    "total_duration",
    "load_duration",
    "prompt_eval_count",
    "prompt_eval_duration",
    "eval_count",
    "eval_duration",
    "done_reason",
    "model",
    "created_at",
)


def _nullable_number(value: Any) -> int | float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def ns_to_ms(value: Any) -> float | None:
    number = _nullable_number(value)
    if number is None:
        return None
    return number / 1_000_000.0


def safe_tokens_per_second(count: Any, duration_ns: Any) -> float | None:
    token_count = _nullable_number(count)
    duration = _nullable_number(duration_ns)
    if token_count is None or duration is None or duration <= 0:
        return None
    return token_count / (duration / 1_000_000_000.0)


def build_provider_metrics(
    provider: str,
    usage: dict[str, Any] | None,
    request_start_ns: int,
    request_end_ns: int,
    time_to_first_byte_ms: float | None = None,
) -> dict[str, Any]:
    usage = dict(usage or {})
    native = {field: usage.get(field) for field in OLLAMA_USAGE_FIELDS}
    provider_metrics_available = any(native.get(field) is not None for field in OLLAMA_USAGE_FIELDS[:6])
    local_wall_time_ms = max(0.0, (request_end_ns - request_start_ns) / 1_000_000.0)

    prompt_tokens = _nullable_number(native.get("prompt_eval_count"))
    completion_tokens = _nullable_number(native.get("eval_count"))
    total_tokens = None
    if prompt_tokens is not None and completion_tokens is not None:
        total_tokens = prompt_tokens + completion_tokens

    provider_total_duration = native.get("total_duration")
    derived = {
        "provider_total_latency_ms": ns_to_ms(provider_total_duration),
        "provider_load_latency_ms": ns_to_ms(native.get("load_duration")),
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "prompt_tokens_per_second": safe_tokens_per_second(prompt_tokens, native.get("prompt_eval_duration")),
        "generation_tokens_per_second": safe_tokens_per_second(completion_tokens, native.get("eval_duration")),
        "end_to_end_tokens_per_second": safe_tokens_per_second(total_tokens, provider_total_duration),
        "local_end_to_end_tps": None,
    }
    if derived["end_to_end_tokens_per_second"] is None and total_tokens is not None and local_wall_time_ms > 0:
        derived["local_end_to_end_tps"] = total_tokens / (local_wall_time_ms / 1000.0)

    metric_sources = {
        **{field: "provider_native" for field in native},
        "request_start_ns": "local_instrumented",
        "request_end_ns": "local_instrumented",
        "local_wall_time_ms": "local_instrumented",
        "time_to_first_byte_ms": "local_instrumented" if time_to_first_byte_ms is not None else "unavailable",
        "provider_total_latency_ms": "provider_native_derived" if derived["provider_total_latency_ms"] is not None else "unavailable",
        "provider_load_latency_ms": "provider_native_derived" if derived["provider_load_latency_ms"] is not None else "unavailable",
        "prompt_tokens": "provider_native",
        "completion_tokens": "provider_native",
        "total_tokens": "provider_native_derived" if total_tokens is not None else "unavailable",
        "prompt_tokens_per_second": "provider_native_derived" if derived["prompt_tokens_per_second"] is not None else "unavailable",
        "generation_tokens_per_second": "provider_native_derived" if derived["generation_tokens_per_second"] is not None else "unavailable",
        "end_to_end_tokens_per_second": "provider_native_derived" if derived["end_to_end_tokens_per_second"] is not None else "unavailable",
        "local_end_to_end_tps": "local_derived" if derived["local_end_to_end_tps"] is not None else "unavailable",
    }

    return sanitize_obj(
        {
            "version": "provider_metrics.v1",
            "provider": provider,
            "provider_metrics_available": provider_metrics_available,
            "native": native,
            "local": {
                "request_start_ns": request_start_ns,
                "request_end_ns": request_end_ns,
                "local_wall_time_ms": local_wall_time_ms,
                "time_to_first_byte_ms": time_to_first_byte_ms,
            },
            "derived": derived,
            "metric_sources": metric_sources,
            "raw_usage": {field: usage.get(field) for field in OLLAMA_USAGE_FIELDS if field in usage},
        }
    )


def flatten_provider_metrics(provider_metrics: dict[str, Any] | None) -> dict[str, Any]:
    if not provider_metrics:
        return {}
    derived = provider_metrics.get("derived") or {}
    native = provider_metrics.get("native") or {}
    local = provider_metrics.get("local") or {}
    return {
        "provider_metrics_available": bool(provider_metrics.get("provider_metrics_available")),
        "provider_name": provider_metrics.get("provider"),
        "provider_done_reason": native.get("done_reason"),
        "provider_model": native.get("model"),
        "provider_created_at": native.get("created_at"),
        "provider_total_latency_ms": derived.get("provider_total_latency_ms"),
        "provider_load_latency_ms": derived.get("provider_load_latency_ms"),
        "prompt_tokens": derived.get("prompt_tokens"),
        "completion_tokens": derived.get("completion_tokens"),
        "total_tokens": derived.get("total_tokens"),
        "prompt_tokens_per_second": derived.get("prompt_tokens_per_second"),
        "generation_tokens_per_second": derived.get("generation_tokens_per_second"),
        "end_to_end_tokens_per_second": derived.get("end_to_end_tokens_per_second"),
        "local_end_to_end_tps": derived.get("local_end_to_end_tps"),
        "local_wall_time_ms": local.get("local_wall_time_ms"),
        "time_to_first_byte_ms": local.get("time_to_first_byte_ms"),
        "provider_metric_sources": provider_metrics.get("metric_sources", {}),
        "provider_metrics": provider_metrics,
    }
