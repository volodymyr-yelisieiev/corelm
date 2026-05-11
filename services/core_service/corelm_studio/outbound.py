from __future__ import annotations

import json
import subprocess
import urllib.request
import uuid
from pathlib import Path
from typing import Any

from .db import utc_now
from .formatters import prompt_template
from .security import sanitize_obj, sanitize_text


def _post_json(url: str, payload: dict[str, Any], headers: dict[str, str], timeout: float = 30.0) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def route_outbound(
    target_type: str,
    content: str,
    config: dict[str, Any] | None = None,
    packet_type: str = "engineering_task_packet",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    raw_config = dict(config or {})
    safe_config = sanitize_obj(raw_config)
    metadata = sanitize_obj(metadata or {})
    content = sanitize_text(content)
    target_type = target_type.lower().replace("-", "_")
    packet = prompt_template(packet_type, content, metadata)
    receipt = {
        "receipt_id": f"out-{uuid.uuid4().hex[:12]}",
        "target_type": target_type,
        "packet_type": packet_type,
        "timestamp": utc_now(),
        "mock": bool(raw_config.get("mock", True)),
    }
    if target_type in {"programming_agent_packet", "prompt_export", "structured_prompt"}:
        return receipt | {"status": "prepared", "packet": packet}
    if target_type in {"file_export", "file"}:
        output_dir = Path(str(raw_config.get("directory") or "exports")).expanduser()
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / str(raw_config.get("filename") or f"{receipt['receipt_id']}.md")
        path.write_text(packet, encoding="utf-8")
        return receipt | {"status": "written", "path": str(path)}
    if target_type in {"clipboard_export", "clipboard"}:
        return receipt | {"status": "prepared", "clipboard_text": packet}
    if target_type in {"generic_http_rest", "http_rest", "rest"}:
        if raw_config.get("mock", True):
            return receipt | {"status": "mock-delivered", "target": safe_config.get("url", "mock://rest")}
        body = _post_json(
            str(raw_config["url"]),
            {"content": packet, "metadata": metadata},
            raw_config.get("headers", {}),
            float(raw_config.get("timeout", 30)),
        )
        return receipt | {"status": "delivered", "response": sanitize_obj(body)}
    if target_type in {"openai_compatible_outbound", "openai"}:
        if raw_config.get("mock", True):
            return receipt | {"status": "mock-delivered", "target": safe_config.get("model", "mock-openai")}
        base_url = str(raw_config.get("base_url") or "https://api.openai.com/v1").rstrip("/")
        payload = {
            "model": raw_config.get("model", "gpt-4.1-mini"),
            "messages": [{"role": "user", "content": packet}],
            "temperature": 0,
        }
        body = _post_json(f"{base_url}/chat/completions", payload, {"Authorization": f"Bearer {raw_config['api_key']}"})
        return receipt | {"status": "delivered", "response": sanitize_obj(body)}
    if target_type in {"local_model_outbound", "local_model", "ollama"}:
        if raw_config.get("mock", True):
            return receipt | {"status": "mock-delivered", "target": safe_config.get("model", "mock-local")}
        base_url = str(raw_config.get("base_url") or "http://127.0.0.1:11434").rstrip("/")
        body = _post_json(
            f"{base_url}/api/generate",
            {"model": raw_config.get("model", "llama3.1"), "prompt": packet, "stream": False},
            {},
        )
        return receipt | {"status": "delivered", "response": sanitize_obj(body)}
    if target_type in {"shell_cli_handoff", "shell"}:
        if raw_config.get("mock", True):
            return receipt | {"status": "mock-delivered", "command": safe_config.get("command", "mock-shell")}
        if not raw_config.get("allow_exec"):
            raise ValueError("shell outbound requires allow_exec=true outside mock mode")
        command = raw_config["command"]
        result = subprocess.run(
            list(command) if isinstance(command, list) else str(command).split(),
            input=packet,
            check=False,
            capture_output=True,
            text=True,
            timeout=float(raw_config.get("timeout", 20)),
        )
        return receipt | {"status": "executed", "exit_code": result.returncode, "stdout": sanitize_text(result.stdout)}
    raise ValueError(f"Unsupported outbound target type: {target_type}")
