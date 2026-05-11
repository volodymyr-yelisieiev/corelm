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
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"raw_payload": self.raw_payload, "metadata": self.metadata}


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
        return ConnectorResult(
            raw_payload=sanitize_text(str(config.get("text") or "")),
            metadata=_metadata("manual_text", branch, safe_config),
        )
    if connector_type in {"openai_compatible_llm", "openai"}:
        prompt = str(config.get("prompt") or config.get("text") or "Summarize Core LM state.")
        api_key = _usable_secret(config.get("api_key"), "OPENAI_API_KEY")
        if config.get("mock", True) or not api_key:
            text = f"[mock-openai] {prompt}"
            return ConnectorResult(sanitize_text(text), _metadata("openai_compatible_llm", branch, safe_config))
        base_url = str(config.get("base_url") or "https://api.openai.com/v1").rstrip("/")
        model = str(config.get("model") or "gpt-4.1-mini")
        payload = {"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0}
        body = _post_json(f"{base_url}/chat/completions", payload, {"Authorization": f"Bearer {api_key}"})
        content = body["choices"][0]["message"]["content"]
        return ConnectorResult(sanitize_text(content), _metadata("openai_compatible_llm", branch, safe_config))
    if connector_type in {"ollama_local_model", "local_model", "ollama"}:
        prompt = str(config.get("prompt") or config.get("text") or "Core LM local model check")
        if config.get("mock", True):
            return ConnectorResult(sanitize_text(f"[mock-local-model] {prompt}"), _metadata("ollama_local_model", branch, safe_config))
        base_url = str(config.get("base_url") or "http://127.0.0.1:11434").rstrip("/")
        body = _post_json(
            f"{base_url}/api/generate",
            {"model": config.get("model", "llama3.1"), "prompt": prompt, "stream": False},
            {},
        )
        return ConnectorResult(sanitize_text(str(body.get("response", ""))), _metadata("ollama_local_model", branch, safe_config))
    if connector_type == "file_input":
        path = Path(str(config["path"])).expanduser()
        text = path.read_text(encoding=str(config.get("encoding") or "utf-8"))
        metadata = _metadata("file_input", branch, safe_config, content_type=str(config.get("content_type") or "text/plain"))
        metadata["file_name"] = path.name
        metadata["file_size"] = path.stat().st_size
        return ConnectorResult(sanitize_text(text), metadata)
    if connector_type == "folder_watcher":
        folder = Path(str(config["path"])).expanduser()
        pattern = str(config.get("pattern") or "*")
        files = sorted(str(path) for path in folder.glob(pattern) if path.is_file())
        payload = json.dumps({"folder": str(folder), "files": files}, ensure_ascii=False, indent=2)
        return ConnectorResult(sanitize_text(payload), _metadata("folder_watcher", branch, safe_config, content_type="application/json"))
    if connector_type in {"generic_web_api_fetch", "web_api_fetch", "api_fetch"}:
        text = _get_text(str(config["url"]), config.get("headers", {}), float(config.get("timeout", 30)))
        return ConnectorResult(sanitize_text(text), _metadata("generic_web_api_fetch", branch, safe_config, content_type="application/json"))
    if connector_type == "clipboard_input":
        text = str(config.get("text") or "")
        return ConnectorResult(sanitize_text(text), _metadata("clipboard_input", branch, safe_config))
    if connector_type == "generic_rest_input":
        method = str(config.get("method") or "GET").upper()
        if method != "GET":
            payload = _post_json(str(config["url"]), config.get("body", {}), config.get("headers", {}))
            text = json.dumps(payload, ensure_ascii=False, indent=2)
        else:
            text = _get_text(str(config["url"]), config.get("headers", {}), float(config.get("timeout", 30)))
        return ConnectorResult(sanitize_text(text), _metadata("generic_rest_input", branch, safe_config, content_type="application/json"))
    if connector_type == "shell_cli_capture":
        command = config.get("command")
        if config.get("mock", True):
            return ConnectorResult(sanitize_text(f"[mock-shell] {command or 'no command'}"), _metadata("shell_cli_capture", branch, safe_config))
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
        return ConnectorResult(sanitize_text(text), _metadata("shell_cli_capture", branch, safe_config))
    raise ValueError(f"Unsupported inbound connector type: {connector_type}")
def _usable_secret(value: Any, env_name: str) -> str:
    raw = str(value or "")
    if raw == "[REDACTED_SECRET]":
        raw = ""
    return raw or os.getenv(env_name, "")

