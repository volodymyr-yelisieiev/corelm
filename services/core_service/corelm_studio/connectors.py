from __future__ import annotations

import json
import os
import subprocess
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .db import utc_now
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


def _get_text(url: str, headers: dict[str, str] | None = None, timeout: float = 30.0) -> str:
    request = urllib.request.Request(url, headers=headers or {}, method="GET")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def run_inbound_connector(connector_type: str, config: dict[str, Any], branch: str = "corelm") -> ConnectorResult:
    connector_type = connector_type.lower().replace("-", "_")
    config = dict(config or {})
    safe_config = sanitize_obj(config)
    if connector_type in {"manual_text", "manual"}:
        raw = sanitize_text(str(config.get("text") or ""))
        return _result(raw, _metadata("manual_text", branch, safe_config))
    if connector_type in {"openai_compatible_llm", "openai"}:
        prompt = str(config.get("prompt") or config.get("text") or "Summarize Core LM state.")
        api_key = _usable_secret(config.get("api_key"), "OPENAI_API_KEY")
        if config.get("mock", True) or not api_key:
            text = f"[mock-openai] {prompt}"
            return _result(text, _metadata("openai_compatible_llm", branch, safe_config))
        base_url = str(config.get("base_url") or "https://api.openai.com/v1").rstrip("/")
        model = str(config.get("model") or "gpt-4.1-mini")
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0}
        body = _post_json(f"{base_url}/chat/completions", payload, {"Authorization": f"Bearer {api_key}"})
        content = body["choices"][0]["message"]["content"]
        return _result(content, _metadata("openai_compatible_llm", branch, safe_config))
    if connector_type in {"ollama_local_model", "local_model", "ollama"}:
        prompt = str(config.get("prompt") or config.get("text") or "Core LM local model check")
        if config.get("mock", True):
            return _result(f"[mock-local-model] {prompt}", _metadata("ollama_local_model", branch, safe_config))
        base_url = str(config.get("base_url") or "http://127.0.0.1:11434").rstrip("/")
        body = _post_json(
            f"{base_url}/api/generate",
            {"model": config.get("model", "llama3.1"), "prompt": prompt, "stream": False},
            {},
        )
        return _result(str(body.get("response", "")), _metadata("ollama_local_model", branch, safe_config))
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
