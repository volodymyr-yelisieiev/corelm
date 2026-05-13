from __future__ import annotations

import atexit
import os
import shutil
import subprocess
import time
import urllib.request
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from .security import sanitize_obj, sanitize_text


@dataclass
class RuntimeHandle:
    provider: str
    base_url: str
    process: subprocess.Popen[Any]
    command: list[str]
    owned: bool = True


_owned_runtimes: dict[str, RuntimeHandle] = {}
_last_status: dict[str, dict[str, Any]] = {}


def _runtime_key(provider: str, base_url: str) -> str:
    return f"{provider}:{base_url.rstrip('/')}"


def _is_local_url(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host in {"127.0.0.1", "localhost", "::1"}


def _get_url(url: str, timeout: float = 1.5) -> bool:
    try:
        request = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(request, timeout=timeout) as response:
            response.read(64)
            return bool(response.status < 500)
    except Exception:  # noqa: BLE001 - health probe reports false
        return False


def probe_runtime(provider: str, base_url: str, timeout: float = 1.5) -> bool:
    base_url = base_url.rstrip("/")
    provider = provider.lower().replace("-", "_")
    if provider == "ollama":
        return _get_url(f"{base_url}/api/tags", timeout)
    if provider in {"lm_studio", "lmstudio"}:
        return _get_url(f"{base_url}/models", timeout)
    return False


def _ollama_command(config: dict[str, Any]) -> list[str] | None:
    configured = config.get("runtime_command") or config.get("ollama_bin") or os.getenv("OLLAMA_BIN")
    if configured:
        if isinstance(configured, list):
            return [str(item) for item in configured]
        return [str(configured), "serve"]
    discovered = shutil.which("ollama")
    if discovered:
        return [discovered, "serve"]
    return None


def _runtime_status(
    provider: str,
    base_url: str,
    healthy: bool,
    *,
    managed: bool = False,
    adopted: bool = False,
    error: str | None = None,
    command: list[str] | None = None,
) -> dict[str, Any]:
    status = sanitize_obj(
        {
            "provider": provider,
            "base_url": base_url.rstrip("/"),
            "healthy": healthy,
            "managed": managed,
            "adopted": adopted,
            "owned": managed and not adopted,
            "command": command,
            "last_error": sanitize_text(error or "") or None,
        }
    )
    _last_status[_runtime_key(provider, base_url)] = status
    return status


def runtime_status(provider: str = "ollama", base_url: str | None = None, config: dict[str, Any] | None = None) -> dict[str, Any]:
    provider = provider.lower().replace("-", "_")
    config = dict(config or {})
    base_url = (base_url or config.get("base_url") or ("http://127.0.0.1:11434" if provider == "ollama" else "http://127.0.0.1:1234/v1")).rstrip("/")
    key = _runtime_key(provider, base_url)
    healthy = probe_runtime(provider, base_url)
    handle = _owned_runtimes.get(key)
    command = handle.command if handle else (_ollama_command(config) if provider == "ollama" else None)
    if healthy:
        return _runtime_status(provider, base_url, True, managed=bool(handle), adopted=not bool(handle), command=command)
    previous = _last_status.get(key, {})
    return _runtime_status(
        provider,
        base_url,
        False,
        managed=bool(handle),
        adopted=False,
        error=str(previous.get("last_error") or ""),
        command=command,
    )


def ensure_runtime(provider: str, base_url: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    provider = provider.lower().replace("-", "_")
    base_url = base_url.rstrip("/")
    config = dict(config or {})
    auto_start = config.get("auto_start", True)
    if isinstance(auto_start, str):
        auto_start = auto_start.strip().lower() not in {"false", "0", "no", "off"}

    if probe_runtime(provider, base_url):
        return _runtime_status(provider, base_url, True, adopted=True)
    if not auto_start:
        return _runtime_status(provider, base_url, False, error="runtime auto-start disabled")
    if not _is_local_url(base_url):
        return _runtime_status(provider, base_url, False, error="runtime auto-start is only allowed for loopback URLs")

    key = _runtime_key(provider, base_url)
    if key in _owned_runtimes and _owned_runtimes[key].process.poll() is None:
        timeout = float(config.get("runtime_start_timeout", 15))
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if probe_runtime(provider, base_url):
                return _runtime_status(provider, base_url, True, managed=True, command=_owned_runtimes[key].command)
            time.sleep(0.25)
        return _runtime_status(provider, base_url, False, managed=True, error="runtime did not become healthy in time")

    if provider != "ollama":
        return _runtime_status(provider, base_url, False, error=f"{provider} runtime auto-start is not supported")

    command = _ollama_command(config)
    if not command:
        return _runtime_status(provider, base_url, False, error="ollama executable was not found")

    env = os.environ.copy()
    parsed = urlparse(base_url)
    if parsed.hostname and parsed.port:
        env["OLLAMA_HOST"] = f"{parsed.hostname}:{parsed.port}"
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, env=env)
    _owned_runtimes[key] = RuntimeHandle(provider=provider, base_url=base_url, process=process, command=command)

    timeout = float(config.get("runtime_start_timeout", 15))
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return _runtime_status(provider, base_url, False, error="ollama serve exited before becoming healthy", command=command)
        if probe_runtime(provider, base_url):
            return _runtime_status(provider, base_url, True, managed=True, command=command)
        time.sleep(0.25)
    return _runtime_status(provider, base_url, False, managed=True, error="ollama serve did not become healthy in time", command=command)


def ensure_runtime_or_raise(provider: str, base_url: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    status = ensure_runtime(provider, base_url, config)
    if not status.get("healthy"):
        raise RuntimeError(str(status.get("last_error") or f"{provider} runtime is not healthy"))
    return status


def stop_owned_runtimes() -> None:
    for key, handle in list(_owned_runtimes.items()):
        if handle.process.poll() is None:
            handle.process.terminate()
            try:
                handle.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                handle.process.kill()
        _owned_runtimes.pop(key, None)


atexit.register(stop_owned_runtimes)
