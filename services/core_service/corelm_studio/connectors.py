from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .db import utc_now
from .local_runtime import ensure_runtime_or_raise
from .metrics import build_provider_metrics
from .security import sanitize_obj, sanitize_text


@dataclass
class ConnectorResult:
    raw_payload: str
    normalized_payload: str
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "raw_payload": self.raw_payload,
            "normalized_payload": self.normalized_payload,
            "metadata": self.metadata,
        }


def _metadata(connector_type: str, branch: str, config: dict[str, Any], content_type: str = "text/plain") -> dict[str, Any]:
    return {
        "source_id": str(config.get("source_id") or f"{connector_type}-{uuid.uuid4().hex[:8]}"),
        "source_type": connector_type,
        "timestamp": utc_now(),
        "content_type": content_type,
        "branch": branch,
        "workspace": str(config.get("workspace") or "default"),
        "trust_level": str(config.get("trust_level") or "medium"),
        "schema_tag": config.get("schema_tag"),
    }


def _normalize_payload(raw_payload: str, content_type: str = "text/plain") -> str:
    text = sanitize_text(str(raw_payload)).replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(line.strip() for line in text.splitlines()).strip()
    if content_type == "application/json":
        try:
            return json.dumps(json.loads(text), ensure_ascii=False, sort_keys=True, indent=2)
        except json.JSONDecodeError:
            return text
    return " ".join(text.split()) if "\n" not in text else text


def _result(raw_payload: str, metadata: dict[str, Any]) -> ConnectorResult:
    content_type = str(metadata.get("content_type") or "text/plain")
    normalized = _normalize_payload(raw_payload, content_type)
    metadata = sanitize_obj(
        metadata
        | {
            "raw_length": len(str(raw_payload)),
            "normalized_length": len(normalized),
        }
    )
    return ConnectorResult(sanitize_text(str(raw_payload)), normalized, metadata)


def connector_catalog() -> dict[str, list[dict[str, Any]]]:
    return {
        "inbound": [
            {"type": "manual_text", "label": "Manual Text", "mock_default": True, "content_type": "text/plain"},
            {"type": "file_input", "label": "File Input", "mock_default": False, "content_type": "text/plain"},
            {"type": "folder_watcher", "label": "Folder Watcher", "mock_default": False, "content_type": "application/json"},
            {"type": "clipboard_input", "label": "Clipboard Input", "mock_default": True, "content_type": "text/plain"},
            {"type": "generic_rest_input", "label": "Generic REST Input", "mock_default": True, "content_type": "application/json"},
            {"type": "generic_web_api_fetch", "label": "Generic Web/API Fetch", "mock_default": True, "content_type": "application/json"},
            {"type": "openai_compatible_llm", "label": "OpenAI-Compatible LLM", "mock_default": True, "content_type": "text/plain"},
            {"type": "lm_studio", "label": "LM Studio Local", "mock_default": False, "content_type": "text/plain"},
            {"type": "ollama_local_model", "label": "Ollama/Local Model", "mock_default": True, "content_type": "text/plain"},
            {"type": "shell_cli_capture", "label": "Shell/CLI Capture", "mock_default": True, "content_type": "text/plain"},
        ],
        "outbound": [
            {"type": "generic_http_rest", "label": "Generic HTTP/REST", "mock_default": True},
            {"type": "openai_compatible_outbound", "label": "OpenAI-Compatible Outbound", "mock_default": True},
            {"type": "local_model_outbound", "label": "Local Model Outbound", "mock_default": True},
            {"type": "file_export", "label": "File Export", "mock_default": False},
            {"type": "clipboard_export", "label": "Clipboard Export", "mock_default": True},
            {"type": "shell_cli_handoff", "label": "Shell/CLI Handoff", "mock_default": True},
            {"type": "programming_agent_packet", "label": "Programming-Agent Packet", "mock_default": True},
        ],
    }


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float = 30.0) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_ollama_generate(url: str, payload: dict[str, Any], timeout: float, request_start_ns: int) -> tuple[dict[str, Any], float | None]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        if payload.get("stream"):
            chunks: list[str] = []
            final: dict[str, Any] = {}
            first_byte_ns: int | None = None
            for line in response:
                if not line.strip():
                    continue
                if first_byte_ns is None:
                    first_byte_ns = time.perf_counter_ns()
                item = json.loads(line.decode("utf-8"))
                chunks.append(str(item.get("response", "")))
                final.update({key: value for key, value in item.items() if key != "response"})
                if item.get("done"):
                    break
            final["response"] = "".join(chunks)
            ttfb = None if first_byte_ns is None else (first_byte_ns - request_start_ns) / 1_000_000.0
            return final, ttfb
        return json.loads(response.read().decode("utf-8")), None


def _is_local_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in {"127.0.0.1", "localhost", "::1"}


def _get_text(url: str, headers: dict[str, str] | None = None, timeout: float = 30.0) -> str:
    request = urllib.request.Request(url, headers=headers or {}, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


OLLAMA_SUPPORTED_CONFIG_FIELDS = {
    "base_url",
    "model",
    "system",
    "prompt",
    "text",
    "format",
    "schema",
    "raw",
    "stream",
    "keep_alive",
    "seed",
    "temperature",
    "top_p",
    "top_k",
    "min_p",
    "repeat_penalty",
    "repeat_last_n",
    "num_ctx",
    "num_predict",
    "stop",
    "mock",
    "timeout",
    "source_id",
    "workspace",
    "trust_level",
    "schema_tag",
    "branch",
    "debug_provider_response",
    "benchmark_mode",
    "deterministic_benchmark",
    "evaluator_config",
    "auto_start",
    "runtime_command",
    "runtime_start_timeout",
    "ollama_bin",
}

OLLAMA_OPTION_FIELDS = {
    "seed",
    "temperature",
    "top_p",
    "top_k",
    "min_p",
    "repeat_penalty",
    "repeat_last_n",
    "num_ctx",
    "num_predict",
    "stop",
}

OLLAMA_NUMERIC_RANGES: dict[str, tuple[type, float | None, float | None]] = {
    "seed": (int, None, None),
    "temperature": (float, 0.0, None),
    "top_p": (float, 0.0, 1.0),
    "top_k": (int, 0, None),
    "min_p": (float, 0.0, 1.0),
    "repeat_penalty": (float, 0.0, None),
    "repeat_last_n": (int, -1, None),
    "num_ctx": (int, 1, None),
    "num_predict": (int, -2, None),
}

OLLAMA_BENCHMARK_DEFAULTS = {
    "temperature": 0.0,
    "top_p": 1.0,
    "top_k": 40,
    "num_predict": 128,
}


def _coerce_bool(config: dict[str, Any], key: str, warnings: list[str]) -> bool | None:
    if key not in config or config[key] is None:
        return None
    value = config[key]
    if isinstance(value, bool):
        return value
    if isinstance(value, str) and value.lower() in {"true", "false"}:
        return value.lower() == "true"
    warnings.append(f"{key} must be a boolean")
    raise ValueError(f"Config field {key} must be a boolean")


def _read_bool(config: dict[str, Any], key: str, default: bool, warnings: list[str] | None = None) -> bool:
    warnings = warnings if warnings is not None else []
    value = _coerce_bool(config, key, warnings)
    return default if value is None else value


def _coerce_number(config: dict[str, Any], key: str, warnings: list[str]) -> int | float | None:
    if key not in config or config[key] is None or config[key] == "":
        return None
    expected_type, lower, upper = OLLAMA_NUMERIC_RANGES[key]
    value = config[key]
    try:
        number = int(value) if expected_type is int else float(value)
    except (TypeError, ValueError) as exc:
        warnings.append(f"{key} has invalid numeric value")
        raise ValueError(f"Ollama config field {key} has invalid numeric value") from exc
    if lower is not None and number < lower:
        raise ValueError(f"Ollama config field {key} must be >= {lower}")
    if upper is not None and number > upper:
        raise ValueError(f"Ollama config field {key} must be <= {upper}")
    return number


def _normalize_stop(value: Any) -> list[str] | None:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        return [value]
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return value
    raise ValueError("Ollama config field stop must be a string or array of strings")


def build_ollama_generate_payload(config: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], list[str]]:
    warnings: list[str] = []
    unsupported = sorted(str(key) for key in config if key not in OLLAMA_SUPPORTED_CONFIG_FIELDS)
    if unsupported:
        warnings.append(f"Unsupported Ollama config fields were not sent: {', '.join(unsupported)}")
    if "think" in config or "reasoning" in config:
        warnings.append("Ollama think/reasoning toggle is not enabled in this connector path")

    deterministic = _read_bool(config, "deterministic_benchmark", False, warnings) or str(config.get("benchmark_mode") or "").lower() == "deterministic"
    if deterministic and config.get("seed") is None:
        raise ValueError("deterministic benchmark mode requires seed")

    prompt = str(config.get("prompt") or config.get("text") or "Core LM local model check")
    stream = _coerce_bool(config, "stream", warnings)
    if deterministic:
        stream = False
    if stream is None:
        stream = False

    payload: dict[str, Any] = {
        "model": str(config.get("model") or "llama3.1"),
        "prompt": prompt,
        "stream": stream,
    }
    for key in ("system", "keep_alive"):
        if config.get(key) not in (None, ""):
            payload[key] = config[key]
    raw = _coerce_bool(config, "raw", warnings)
    if raw is not None:
        payload["raw"] = raw

    fmt = config.get("format")
    if isinstance(fmt, dict):
        payload["format"] = fmt
    elif fmt not in (None, "", "plain", "text"):
        fmt_name = str(fmt).lower()
        if fmt_name == "json":
            payload["format"] = "json"
        elif fmt_name == "schema":
            schema = config.get("schema")
            if isinstance(schema, dict):
                payload["format"] = schema
            else:
                warnings.append("format=schema requested without a schema object")
        else:
            warnings.append(f"Unsupported Ollama format was not sent: {fmt}")

    options: dict[str, Any] = {}
    effective_for_metadata: dict[str, Any] = {
        "base_url": str(config.get("base_url") or "http://127.0.0.1:11434").rstrip("/"),
        "model": payload["model"],
        "stream": stream,
        "deterministic_benchmark": deterministic,
    }
    for key in OLLAMA_OPTION_FIELDS:
        if deterministic and key in OLLAMA_BENCHMARK_DEFAULTS and config.get(key) is None:
            value = OLLAMA_BENCHMARK_DEFAULTS[key]
        elif key == "stop":
            value = _normalize_stop(config.get(key))
        else:
            value = _coerce_number(config, key, warnings) if key in OLLAMA_NUMERIC_RANGES else config.get(key)
        if value is not None:
            options[key] = value
            effective_for_metadata[key] = value
    if options:
        payload["options"] = options

    return payload, effective_for_metadata, warnings


def run_inbound_connector(connector_type: str, config: dict[str, Any], branch: str = "corelm") -> ConnectorResult:
    connector_type = connector_type.lower().replace("-", "_")
    config = dict(config or {})
    safe_config = sanitize_obj(config)
    if connector_type in {"manual_text", "manual"}:
        raw = sanitize_text(str(config.get("text") or ""))
        return _result(raw, _metadata("manual_text", branch, safe_config))
    if connector_type in {"openai_compatible_llm", "openai", "lm_studio", "lmstudio"}:
        metadata_type = "lm_studio" if connector_type in {"lm_studio", "lmstudio"} else "openai_compatible_llm"
        prompt = str(config.get("prompt") or config.get("text") or "Summarize Core LM state.")
        default_base_url = "http://127.0.0.1:1234/v1" if connector_type in {"lm_studio", "lmstudio"} else "https://api.openai.com/v1"
        base_url = str(config.get("base_url") or default_base_url).rstrip("/")
        api_key = _usable_secret(config.get("api_key"), str(config.get("api_key_env") or "OPENAI_API_KEY"))
        mock_default = connector_type not in {"lm_studio", "lmstudio"}
        if _read_bool(config, "mock", mock_default):
            text = f"[mock-openai] {prompt}"
            return _result(text, _metadata(metadata_type, branch, safe_config))
        if not api_key and not _is_local_url(base_url):
            raise ValueError("openai_compatible_llm requires api_key or OPENAI_API_KEY outside local LM Studio endpoints")
        if metadata_type == "lm_studio" and _read_bool(config, "auto_start", True):
            ensure_runtime_or_raise("lm_studio", base_url, config)
        model = str(config.get("model") or "gpt-4.1-mini")
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": config.get("temperature", 0),
        }
        if config.get("max_tokens") is not None:
            payload["max_tokens"] = config["max_tokens"]
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        body = _post_json(f"{base_url}/chat/completions", payload, headers)
        content = body["choices"][0]["message"]["content"]
        return _result(content, _metadata(metadata_type, branch, safe_config))
    if connector_type in {"ollama_local_model", "local_model", "ollama"}:
        prompt = str(config.get("prompt") or config.get("text") or "Core LM local model check")
        payload, sampling_metadata, warnings = build_ollama_generate_payload(config)
        base_url = sampling_metadata["base_url"]
        if _read_bool(config, "mock", True, warnings):
            request_start_ns = time.perf_counter_ns()
            request_end_ns = time.perf_counter_ns()
            metadata = _metadata("ollama_local_model", branch, safe_config)
            metadata["provider_metrics"] = build_provider_metrics("ollama", {}, request_start_ns, request_end_ns)
            metadata["sampling"] = sampling_metadata
            metadata["warnings"] = warnings
            return _result(f"[mock-local-model] {prompt}", metadata)
        runtime_status = ensure_runtime_or_raise("ollama", base_url, config) if _read_bool(config, "auto_start", True, warnings) else None
        request_start_ns = time.perf_counter_ns()
        body, time_to_first_byte_ms = _post_ollama_generate(
            f"{base_url}/api/generate",
            payload,
            float(config.get("timeout", 30)),
            request_start_ns,
        )
        request_end_ns = time.perf_counter_ns()
        usage = {key: body.get(key) for key in (
            "total_duration",
            "load_duration",
            "prompt_eval_count",
            "prompt_eval_duration",
            "eval_count",
            "eval_duration",
            "done_reason",
            "model",
            "created_at",
        )}
        metadata = _metadata("ollama_local_model", branch, safe_config)
        metadata["provider_metrics"] = build_provider_metrics("ollama", usage, request_start_ns, request_end_ns, time_to_first_byte_ms)
        metadata["sampling"] = sampling_metadata
        metadata["runtime"] = runtime_status
        metadata["warnings"] = warnings
        if config.get("debug_provider_response"):
            metadata["debug"] = {"provider_response": sanitize_obj(body)}
        return _result(str(body.get("response", "")), metadata)
    if connector_type == "file_input":
        path = Path(str(config["path"])).expanduser()
        text = path.read_text(encoding=str(config.get("encoding") or "utf-8"))
        metadata = _metadata("file_input", branch, safe_config, content_type=str(config.get("content_type") or "text/plain"))
        metadata["file_name"] = path.name
        metadata["file_size"] = path.stat().st_size
        return _result(text, metadata)
    if connector_type == "folder_watcher":
        folder = Path(str(config["path"])).expanduser()
        pattern = str(config.get("pattern") or "*")
        files = sorted(str(path) for path in folder.glob(pattern) if path.is_file())
        payload = json.dumps({"folder": str(folder), "files": files}, ensure_ascii=False, indent=2)
        return _result(payload, _metadata("folder_watcher", branch, safe_config, content_type="application/json"))
    if connector_type in {"generic_web_api_fetch", "web_api_fetch", "api_fetch"}:
        if config.get("mock", True):
            payload = json.dumps(
                {
                    "mock": True,
                    "source": "generic_web_api_fetch",
                    "url": safe_config.get("url", "mock://web-api"),
                    "body": safe_config.get("body", {"status": "ok"}),
                },
                ensure_ascii=False,
                indent=2,
            )
            return _result(payload, _metadata("generic_web_api_fetch", branch, safe_config, content_type="application/json"))
        text = _get_text(str(config["url"]), config.get("headers", {}), float(config.get("timeout", 30)))
        return _result(text, _metadata("generic_web_api_fetch", branch, safe_config, content_type="application/json"))
    if connector_type == "clipboard_input":
        text = str(config.get("text") or "")
        return _result(text, _metadata("clipboard_input", branch, safe_config))
    if connector_type == "generic_rest_input":
        if config.get("mock", True):
            payload = json.dumps(
                {
                    "mock": True,
                    "source": "generic_rest_input",
                    "method": str(config.get("method") or "GET").upper(),
                    "url": safe_config.get("url", "mock://rest"),
                    "body": safe_config.get("body", {"status": "ok"}),
                },
                ensure_ascii=False,
                indent=2,
            )
            return _result(payload, _metadata("generic_rest_input", branch, safe_config, content_type="application/json"))
        method = str(config.get("method") or "GET").upper()
        if method != "GET":
            payload = _post_json(str(config["url"]), config.get("body", {}), config.get("headers", {}))
            text = json.dumps(payload, ensure_ascii=False, indent=2)
        else:
            text = _get_text(str(config["url"]), config.get("headers", {}), float(config.get("timeout", 30)))
        return _result(text, _metadata("generic_rest_input", branch, safe_config, content_type="application/json"))
    if connector_type == "shell_cli_capture":
        command = config.get("command")
        if config.get("mock", True):
            return _result(f"[mock-shell] {command or 'no command'}", _metadata("shell_cli_capture", branch, safe_config))
        if not config.get("allow_exec"):
            raise ValueError("shell_cli_capture requires allow_exec=true outside mock mode")
        result = subprocess.run(
            list(command) if isinstance(command, list) else str(command).split(),
            check=False,
            capture_output=True,
            text=True,
            timeout=float(config.get("timeout", 20)),
        )
        text = f"exit_code={result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        return _result(text, _metadata("shell_cli_capture", branch, safe_config))
    raise ValueError(f"Unsupported inbound connector type: {connector_type}")
def _usable_secret(value: Any, env_name: str) -> str:
    raw = str(value or "")
    if raw == "[REDACTED_SECRET]":
        raw = ""
    return raw or os.getenv(env_name, "")
