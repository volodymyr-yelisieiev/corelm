from __future__ import annotations

import hashlib
import os
import platform
import resource
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from .security import sanitize_obj, sanitize_text


def stable_hash(value: Any) -> str:
    import json

    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")).hexdigest()


def _now_ms(start_ns: int) -> float:
    return (time.perf_counter_ns() - start_ns) / 1_000_000.0


def _peak_ram_mb() -> float | None:
    try:
        usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except Exception:  # noqa: BLE001 - telemetry is best effort and nullable
        return None
    if platform.system().lower() == "darwin":
        return float(usage) / (1024.0 * 1024.0)
    return float(usage) / 1024.0


@dataclass
class DirectRuntimeSession:
    session_id: str
    adapter_id: str
    runtime_family: str
    model_ref: str
    config: dict[str, Any]
    handle: Any = None
    tokenizer: Any = None
    created_at_ms: float = field(default_factory=lambda: time.time() * 1000.0)


@dataclass
class DirectGenerationResult:
    final_text: str
    token_ids: list[int | None]
    decoded_tokens: list[str]
    per_token_timestamps_ms: list[float | None]
    top_k_candidates: list[list[dict[str, Any]]] = field(default_factory=list)
    logits: list[Any] | None = None
    logprobs: list[float | None] = field(default_factory=list)
    entropy_trace: list[float | None] = field(default_factory=list)
    confidence_trace: list[float | None] = field(default_factory=list)
    sampler_config_actual: dict[str, Any] = field(default_factory=dict)
    seed_actual: int | None = None
    runtime: dict[str, Any] = field(default_factory=dict)
    model: dict[str, Any] = field(default_factory=dict)
    telemetry: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    unsupported_fields: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return sanitize_obj(
            {
                "final_text": self.final_text,
                "token_ids": self.token_ids,
                "decoded_tokens": self.decoded_tokens,
                "per_token_timestamps_ms": self.per_token_timestamps_ms,
                "top_k_candidates": self.top_k_candidates,
                "logits": self.logits,
                "logprobs": self.logprobs,
                "entropy_trace": self.entropy_trace,
                "confidence_trace": self.confidence_trace,
                "sampler_config_actual": self.sampler_config_actual,
                "seed_actual": self.seed_actual,
                "runtime": self.runtime,
                "model": self.model,
                "telemetry": self.telemetry,
                "warnings": self.warnings,
                "unsupported_fields": self.unsupported_fields,
                "token_trace_hash": stable_hash(
                    {
                        "token_ids": self.token_ids,
                        "decoded_tokens": self.decoded_tokens,
                        "timestamps_available": any(item is not None for item in self.per_token_timestamps_ms),
                    }
                ),
                "output_hash": stable_hash({"final_text": self.final_text}),
            }
        )


class DirectRuntimeAdapter:
    adapter_id = "direct_base"
    family = "base"
    strict_eligible = False

    def id(self) -> str:
        return self.adapter_id

    def runtime_family(self) -> str:
        return self.family

    def list_local_models(self, config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return []

    def load_model(self, model_ref: str, config: dict[str, Any] | None = None) -> DirectRuntimeSession:
        raise NotImplementedError

    def unload_model(self, session: DirectRuntimeSession) -> None:
        session.handle = None
        session.tokenizer = None

    def warmup(self, session: DirectRuntimeSession) -> dict[str, Any]:
        return {"status": "ok", "warmup_ms": 0.0}

    def generate(
        self,
        session: DirectRuntimeSession,
        prompt: str,
        system: str | None,
        generation_config: dict[str, Any],
        trace_config: dict[str, Any] | None = None,
    ) -> DirectGenerationResult:
        raise NotImplementedError

    def stream_generate(
        self,
        session: DirectRuntimeSession,
        prompt: str,
        system: str | None,
        generation_config: dict[str, Any],
        trace_config: dict[str, Any] | None = None,
    ) -> Iterable[DirectGenerationResult]:
        yield self.generate(session, prompt, system, generation_config, trace_config)

    def health_check(self) -> dict[str, Any]:
        return {"adapter_id": self.id(), "healthy": True, "runtime_family": self.runtime_family()}

    def capability_report(self) -> dict[str, Any]:
        return {
            "adapter_id": self.id(),
            "runtime_family": self.runtime_family(),
            "strict_eligible": self.strict_eligible,
            "direct_execution": True,
            "supports_token_ids": False,
            "supports_token_text": False,
            "supports_per_token_timestamps": False,
            "supports_logits": False,
            "supports_top_k": False,
            "supports_seed": False,
            "requires_optional_dependency": None,
            "availability": "available",
            "warnings": [],
        }

    def benchmark_capability_report(self) -> dict[str, Any]:
        report = self.capability_report()
        metric_support = {
            "runtime_metrics": "partial",
            "determinism_metrics": "supported",
            "compression_metrics": "via_corelm_pipeline",
            "state_metrics": "via_corelm_pipeline",
        }
        return report | {"metric_support": metric_support}


class DeterministicDirectAdapter(DirectRuntimeAdapter):
    adapter_id = "deterministic_direct_smoke"
    family = "deterministic_inprocess"
    strict_eligible = False

    def list_local_models(self, config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return [
            {
                "model_ref": "deterministic://corelm-smoke",
                "name": "Core LM deterministic direct smoke",
                "available": True,
                "strict_eligible": False,
                "notes": "In-process deterministic adapter for smoke tests; not a production LLM benchmark result.",
            }
        ]

    def load_model(self, model_ref: str, config: dict[str, Any] | None = None) -> DirectRuntimeSession:
        return DirectRuntimeSession(
            session_id=f"drt-{uuid.uuid4().hex[:12]}",
            adapter_id=self.id(),
            runtime_family=self.runtime_family(),
            model_ref=model_ref or "deterministic://corelm-smoke",
            config=sanitize_obj(config or {}),
            handle={"loaded": True},
        )

    def generate(
        self,
        session: DirectRuntimeSession,
        prompt: str,
        system: str | None,
        generation_config: dict[str, Any],
        trace_config: dict[str, Any] | None = None,
    ) -> DirectGenerationResult:
        start = time.perf_counter_ns()
        seed = generation_config.get("seed")
        max_tokens = int(generation_config.get("max_new_tokens") or generation_config.get("num_predict") or 64)
        payload = sanitize_text(prompt).strip() or "benchmark.fact = empty prompt"
        if "=" not in payload and ":" not in payload:
            payload = f"benchmark.output = {payload}"
        words = payload.split()[:max_tokens]
        timestamps: list[float | None] = []
        for _word in words:
            timestamps.append(_now_ms(start))
        token_ids = [int(hashlib.sha256(word.encode("utf-8")).hexdigest()[:8], 16) for word in words]
        total_ms = _now_ms(start)
        return DirectGenerationResult(
            final_text=" ".join(words),
            token_ids=token_ids,
            decoded_tokens=words,
            per_token_timestamps_ms=timestamps,
            sampler_config_actual={
                "mode": generation_config.get("mode", "deterministic_smoke"),
                "temperature": generation_config.get("temperature", 0),
                "top_p": generation_config.get("top_p", 1),
                "top_k": generation_config.get("top_k", 1),
                "max_new_tokens": max_tokens,
            },
            seed_actual=int(seed) if seed is not None and str(seed) != "" else None,
            runtime={
                "adapter_id": self.id(),
                "runtime_family": self.runtime_family(),
                "runtime_version": "inprocess-smoke.v1",
                "engine": "python",
            },
            model={
                "model_id": session.model_ref,
                "model_path_or_ref": session.model_ref,
                "quantization": None,
                "precision": None,
            },
            telemetry={
                "load_ms": 0.0,
                "warmup_ms": 0.0,
                "ttft_ms": timestamps[0] if timestamps else None,
                "total_ms": total_ms,
                "prompt_eval_ms": None,
                "decode_ms": total_ms,
                "prompt_token_count": len(prompt.split()),
                "actual_generated_token_count": len(words),
                "total_token_count": len(prompt.split()) + len(words),
                "decode_tps": None if total_ms <= 0 else len(words) / (total_ms / 1000.0),
                "prompt_tps": None,
                "end_to_end_tps": None if total_ms <= 0 else (len(prompt.split()) + len(words)) / (total_ms / 1000.0),
                "peak_ram_mb": _peak_ram_mb(),
                "avg_ram_mb": None,
                "peak_vram_mb": None,
                "avg_vram_mb": None,
            },
            warnings=["deterministic_direct_smoke is for local smoke tests and is not a production strict LLM benchmark adapter"],
        )

    def capability_report(self) -> dict[str, Any]:
        return super().capability_report() | {
            "strict_eligible": False,
            "supports_token_ids": True,
            "supports_token_text": True,
            "supports_per_token_timestamps": True,
            "supports_seed": True,
            "availability": "available",
            "support_classification": "DIRECT / PARTIAL METRICS",
            "warnings": ["Smoke adapter only; exclude from production strict benchmark claims."],
        }


class TransformersDirectAdapter(DirectRuntimeAdapter):
    adapter_id = "transformers_direct"
    family = "transformers"
    strict_eligible = True

    def _import_runtime(self) -> tuple[Any, Any, Any]:
        try:
            import torch  # type: ignore
            from transformers import AutoModelForCausalLM, AutoTokenizer  # type: ignore
        except Exception as exc:  # noqa: BLE001 - reported as adapter availability
            raise RuntimeError("transformers and torch are required for TransformersDirectAdapter") from exc
        return torch, AutoModelForCausalLM, AutoTokenizer

    def _model_dirs(self, config: dict[str, Any] | None = None) -> list[Path]:
        config = config or {}
        raw_dirs = config.get("model_dirs") or os.getenv("CORELM_TRANSFORMERS_MODEL_DIRS") or ""
        if isinstance(raw_dirs, str):
            parts = [item for item in raw_dirs.split(os.pathsep) if item]
        else:
            parts = [str(item) for item in raw_dirs]
        defaults = [Path.home() / ".cache" / "huggingface" / "hub"]
        return [Path(item).expanduser() for item in parts] + defaults

    def list_local_models(self, config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        models: list[dict[str, Any]] = []
        for folder in self._model_dirs(config):
            if not folder.exists():
                continue
            for candidate in folder.glob("**/config.json"):
                model_dir = candidate.parent
                models.append(
                    {
                        "model_ref": str(model_dir),
                        "name": model_dir.name,
                        "path": str(model_dir),
                        "available": True,
                        "strict_eligible": True,
                    }
                )
                if len(models) >= 50:
                    return models
        return models

    def load_model(self, model_ref: str, config: dict[str, Any] | None = None) -> DirectRuntimeSession:
        config = dict(config or {})
        start = time.perf_counter_ns()
        torch, AutoModelForCausalLM, AutoTokenizer = self._import_runtime()
        local_only = bool(config.get("local_files_only", True))
        tokenizer = AutoTokenizer.from_pretrained(model_ref, local_files_only=local_only)
        dtype_name = str(config.get("torch_dtype") or "auto")
        dtype = "auto" if dtype_name == "auto" else getattr(torch, dtype_name)
        model = AutoModelForCausalLM.from_pretrained(model_ref, local_files_only=local_only, torch_dtype=dtype)
        if config.get("device"):
            model = model.to(str(config["device"]))
        model.eval()
        session = DirectRuntimeSession(
            session_id=f"drt-{uuid.uuid4().hex[:12]}",
            adapter_id=self.id(),
            runtime_family=self.runtime_family(),
            model_ref=model_ref,
            config=sanitize_obj(config | {"load_ms": _now_ms(start)}),
            handle=model,
            tokenizer=tokenizer,
        )
        return session

    def warmup(self, session: DirectRuntimeSession) -> dict[str, Any]:
        start = time.perf_counter_ns()
        self.generate(
            session,
            "warmup = true",
            None,
            {"max_new_tokens": 1, "temperature": 0, "top_k": 1, "top_p": 1, "seed": 0},
            {},
        )
        return {"status": "ok", "warmup_ms": _now_ms(start)}

    def generate(
        self,
        session: DirectRuntimeSession,
        prompt: str,
        system: str | None,
        generation_config: dict[str, Any],
        trace_config: dict[str, Any] | None = None,
    ) -> DirectGenerationResult:
        trace_config = trace_config or {}
        start = time.perf_counter_ns()
        torch, _AutoModelForCausalLM, _AutoTokenizer = self._import_runtime()
        seed = generation_config.get("seed")
        if seed is not None and str(seed) != "":
            torch.manual_seed(int(seed))
        tokenizer = session.tokenizer
        model = session.handle
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        encoded = tokenizer(full_prompt, return_tensors="pt")
        device = next(model.parameters()).device
        encoded = {key: value.to(device) for key, value in encoded.items()}
        prompt_tokens = int(encoded["input_ids"].shape[-1])
        max_new_tokens = int(generation_config.get("max_new_tokens") or generation_config.get("num_predict") or 128)
        temperature = float(generation_config.get("temperature", 0) or 0)
        do_sample = temperature > 0
        generate_kwargs = {
            "max_new_tokens": max_new_tokens,
            "do_sample": do_sample,
            "temperature": temperature if do_sample else None,
            "top_p": float(generation_config.get("top_p", 1.0)),
            "top_k": int(generation_config.get("top_k", 1 if not do_sample else 50)),
            "return_dict_in_generate": True,
            "output_scores": bool(trace_config.get("capture_scores", True)),
            "pad_token_id": tokenizer.eos_token_id,
        }
        generate_kwargs = {key: value for key, value in generate_kwargs.items() if value is not None}
        gen_start = time.perf_counter_ns()
        with torch.no_grad():
            output = model.generate(**encoded, **generate_kwargs)
        total_ms = _now_ms(start)
        generated_ids_tensor = output.sequences[0][prompt_tokens:]
        token_ids = [int(item) for item in generated_ids_tensor.detach().cpu().tolist()]
        decoded_tokens = [tokenizer.decode([item], skip_special_tokens=False) for item in token_ids]
        final_text = tokenizer.decode(generated_ids_tensor, skip_special_tokens=True)
        timestamps = [None for _ in token_ids]
        warnings = ["per-token timestamps are unavailable from non-incremental transformers.generate and are stored as null"]
        top_k_candidates: list[list[dict[str, Any]]] = []
        logprobs: list[float | None] = []
        confidence_trace: list[float | None] = []
        if bool(trace_config.get("capture_scores", True)) and getattr(output, "scores", None):
            for token_id, score in zip(token_ids, output.scores):
                probs = torch.softmax(score[0], dim=-1)
                top_k = min(int(trace_config.get("top_k_trace", 5)), int(probs.shape[-1]))
                values, indices = torch.topk(probs, top_k)
                top_k_candidates.append(
                    [
                        {"candidate_id": int(idx), "candidate_text": tokenizer.decode([int(idx)]), "probability": float(prob)}
                        for idx, prob in zip(indices.detach().cpu().tolist(), values.detach().cpu().tolist())
                    ]
                )
                prob = float(probs[token_id].detach().cpu()) if token_id < probs.shape[-1] else None
                confidence_trace.append(prob)
                logprobs.append(None if prob is None or prob <= 0 else float(torch.log(torch.tensor(prob))))
        return DirectGenerationResult(
            final_text=final_text,
            token_ids=token_ids,
            decoded_tokens=decoded_tokens,
            per_token_timestamps_ms=timestamps,
            top_k_candidates=top_k_candidates,
            logprobs=logprobs,
            confidence_trace=confidence_trace,
            sampler_config_actual={
                "max_new_tokens": max_new_tokens,
                "do_sample": do_sample,
                "temperature": temperature,
                "top_p": generate_kwargs.get("top_p"),
                "top_k": generate_kwargs.get("top_k"),
            },
            seed_actual=int(seed) if seed is not None and str(seed) != "" else None,
            runtime={
                "adapter_id": self.id(),
                "runtime_family": self.runtime_family(),
                "runtime_version": "transformers",
                "engine": type(model).__name__,
            },
            model={
                "model_id": str(session.model_ref),
                "model_path_or_ref": str(session.model_ref),
                "precision": str(getattr(next(model.parameters()), "dtype", "")),
                "quantization": None,
            },
            telemetry={
                "load_ms": session.config.get("load_ms"),
                "warmup_ms": None,
                "ttft_ms": None,
                "total_ms": total_ms,
                "prompt_eval_ms": None,
                "decode_ms": (time.perf_counter_ns() - gen_start) / 1_000_000.0,
                "prompt_token_count": prompt_tokens,
                "actual_generated_token_count": len(token_ids),
                "total_token_count": prompt_tokens + len(token_ids),
                "decode_tps": None if total_ms <= 0 else len(token_ids) / (total_ms / 1000.0),
                "prompt_tps": None,
                "end_to_end_tps": None if total_ms <= 0 else (prompt_tokens + len(token_ids)) / (total_ms / 1000.0),
                "peak_ram_mb": _peak_ram_mb(),
                "avg_ram_mb": None,
                "peak_vram_mb": None,
                "avg_vram_mb": None,
            },
            warnings=warnings,
        )

    def health_check(self) -> dict[str, Any]:
        try:
            self._import_runtime()
            return {"adapter_id": self.id(), "healthy": True, "runtime_family": self.runtime_family()}
        except RuntimeError as exc:
            return {"adapter_id": self.id(), "healthy": False, "runtime_family": self.runtime_family(), "last_error": str(exc)}

    def capability_report(self) -> dict[str, Any]:
        healthy = self.health_check()
        return super().capability_report() | {
            "strict_eligible": True,
            "supports_token_ids": True,
            "supports_token_text": True,
            "supports_per_token_timestamps": False,
            "supports_logits": False,
            "supports_top_k": True,
            "supports_seed": True,
            "requires_optional_dependency": "transformers, torch",
            "availability": "available" if healthy.get("healthy") else "blocked",
            "last_error": healthy.get("last_error"),
            "support_classification": "DIRECT / STRICT-BENCH ELIGIBLE" if healthy.get("healthy") else "BLOCKED BY LICENSE / CLOSED RUNTIME / MANUAL STEP",
        }


class LlamaCppDirectAdapter(DirectRuntimeAdapter):
    adapter_id = "llamacpp_direct"
    family = "llama_cpp"
    strict_eligible = True

    def _import_runtime(self) -> Any:
        try:
            from llama_cpp import Llama  # type: ignore
        except Exception as exc:  # noqa: BLE001 - reported as adapter availability
            raise RuntimeError("llama-cpp-python is required for LlamaCppDirectAdapter") from exc
        return Llama

    def _model_dirs(self, config: dict[str, Any] | None = None) -> list[Path]:
        config = config or {}
        raw_dirs = config.get("model_dirs") or os.getenv("CORELM_LLAMACPP_MODEL_DIRS") or ""
        if isinstance(raw_dirs, str):
            parts = [item for item in raw_dirs.split(os.pathsep) if item]
        else:
            parts = [str(item) for item in raw_dirs]
        defaults = [Path.home() / "models", Path.home() / ".cache" / "lm-studio" / "models"]
        return [Path(item).expanduser() for item in parts] + defaults

    def list_local_models(self, config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        models: list[dict[str, Any]] = []
        for folder in self._model_dirs(config):
            if not folder.exists():
                continue
            for candidate in folder.glob("**/*.gguf"):
                models.append(
                    {
                        "model_ref": str(candidate),
                        "name": candidate.name,
                        "path": str(candidate),
                        "available": True,
                        "strict_eligible": True,
                    }
                )
                if len(models) >= 100:
                    return models
        return models

    def load_model(self, model_ref: str, config: dict[str, Any] | None = None) -> DirectRuntimeSession:
        config = dict(config or {})
        start = time.perf_counter_ns()
        Llama = self._import_runtime()
        model_path = str(model_ref)
        if not Path(model_path).expanduser().exists():
            raise RuntimeError(f"GGUF model not found: {model_ref}")
        llm = Llama(
            model_path=str(Path(model_path).expanduser()),
            n_ctx=int(config.get("n_ctx", config.get("num_ctx", 2048))),
            n_threads=int(config.get("threads", os.cpu_count() or 1)),
            n_gpu_layers=int(config.get("n_gpu_layers", 0)),
            seed=int(config.get("seed", -1)),
            verbose=bool(config.get("verbose", False)),
        )
        return DirectRuntimeSession(
            session_id=f"drt-{uuid.uuid4().hex[:12]}",
            adapter_id=self.id(),
            runtime_family=self.runtime_family(),
            model_ref=model_path,
            config=sanitize_obj(config | {"load_ms": _now_ms(start)}),
            handle=llm,
        )

    def warmup(self, session: DirectRuntimeSession) -> dict[str, Any]:
        start = time.perf_counter_ns()
        self.generate(session, "warmup = true", None, {"max_new_tokens": 1, "temperature": 0, "seed": 0}, {})
        return {"status": "ok", "warmup_ms": _now_ms(start)}

    def generate(
        self,
        session: DirectRuntimeSession,
        prompt: str,
        system: str | None,
        generation_config: dict[str, Any],
        trace_config: dict[str, Any] | None = None,
    ) -> DirectGenerationResult:
        start = time.perf_counter_ns()
        llm = session.handle
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        max_tokens = int(generation_config.get("max_new_tokens") or generation_config.get("num_predict") or 128)
        seed = generation_config.get("seed", session.config.get("seed"))
        output_parts: list[str] = []
        timestamps: list[float | None] = []
        token_ids: list[int | None] = []
        decoded_tokens: list[str] = []
        stream = llm(
            full_prompt,
            max_tokens=max_tokens,
            temperature=float(generation_config.get("temperature", 0) or 0),
            top_p=float(generation_config.get("top_p", 1.0)),
            top_k=int(generation_config.get("top_k", 1)),
            seed=int(seed) if seed is not None and str(seed) != "" else None,
            stream=True,
            logprobs=int((trace_config or {}).get("logprobs", 0)),
        )
        for item in stream:
            choice = (item.get("choices") or [{}])[0]
            text = str(choice.get("text") or "")
            output_parts.append(text)
            decoded_tokens.append(text)
            token_ids.append(None)
            timestamps.append(_now_ms(start))
        final_text = "".join(output_parts)
        total_ms = _now_ms(start)
        prompt_token_count = len(llm.tokenize(full_prompt.encode("utf-8"))) if hasattr(llm, "tokenize") else len(full_prompt.split())
        return DirectGenerationResult(
            final_text=final_text,
            token_ids=token_ids,
            decoded_tokens=decoded_tokens,
            per_token_timestamps_ms=timestamps,
            sampler_config_actual={
                "max_new_tokens": max_tokens,
                "temperature": float(generation_config.get("temperature", 0) or 0),
                "top_p": float(generation_config.get("top_p", 1.0)),
                "top_k": int(generation_config.get("top_k", 1)),
            },
            seed_actual=int(seed) if seed is not None and str(seed) != "" else None,
            runtime={
                "adapter_id": self.id(),
                "runtime_family": self.runtime_family(),
                "runtime_version": "llama-cpp-python",
                "engine": "llama.cpp",
            },
            model={
                "model_id": Path(session.model_ref).name,
                "model_path_or_ref": session.model_ref,
                "quantization": "gguf",
                "precision": None,
            },
            telemetry={
                "load_ms": session.config.get("load_ms"),
                "warmup_ms": None,
                "ttft_ms": timestamps[0] if timestamps else None,
                "total_ms": total_ms,
                "prompt_eval_ms": None,
                "decode_ms": total_ms,
                "prompt_token_count": prompt_token_count,
                "actual_generated_token_count": len(decoded_tokens),
                "total_token_count": prompt_token_count + len(decoded_tokens),
                "decode_tps": None if total_ms <= 0 else len(decoded_tokens) / (total_ms / 1000.0),
                "prompt_tps": None,
                "end_to_end_tps": None if total_ms <= 0 else (prompt_token_count + len(decoded_tokens)) / (total_ms / 1000.0),
                "peak_ram_mb": _peak_ram_mb(),
                "avg_ram_mb": None,
                "peak_vram_mb": None,
                "avg_vram_mb": None,
            },
            warnings=["llama.cpp streaming chunks may not expose numeric token ids through llama-cpp-python"],
        )

    def health_check(self) -> dict[str, Any]:
        try:
            self._import_runtime()
            return {"adapter_id": self.id(), "healthy": True, "runtime_family": self.runtime_family()}
        except RuntimeError as exc:
            return {"adapter_id": self.id(), "healthy": False, "runtime_family": self.runtime_family(), "last_error": str(exc)}

    def capability_report(self) -> dict[str, Any]:
        healthy = self.health_check()
        return super().capability_report() | {
            "strict_eligible": True,
            "supports_token_ids": False,
            "supports_token_text": True,
            "supports_per_token_timestamps": True,
            "supports_logits": False,
            "supports_top_k": False,
            "supports_seed": True,
            "requires_optional_dependency": "llama-cpp-python",
            "availability": "available" if healthy.get("healthy") else "blocked",
            "last_error": healthy.get("last_error"),
            "support_classification": "DIRECT / STRICT-BENCH ELIGIBLE" if healthy.get("healthy") else "BLOCKED BY LICENSE / CLOSED RUNTIME / MANUAL STEP",
        }


class DirectRuntimeRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, DirectRuntimeAdapter] = {}
        for adapter in (TransformersDirectAdapter(), LlamaCppDirectAdapter(), DeterministicDirectAdapter()):
            self.register(adapter)
        self._sessions: dict[str, DirectRuntimeSession] = {}

    def register(self, adapter: DirectRuntimeAdapter) -> None:
        self._adapters[adapter.id()] = adapter

    def adapters(self) -> list[dict[str, Any]]:
        return [adapter.benchmark_capability_report() for adapter in self._adapters.values()]

    def get(self, adapter_id: str) -> DirectRuntimeAdapter:
        if adapter_id not in self._adapters:
            raise ValueError(f"Unknown direct runtime adapter: {adapter_id}")
        return self._adapters[adapter_id]

    def list_models(self, adapter_id: str | None = None, config: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        adapters = [self.get(adapter_id)] if adapter_id else list(self._adapters.values())
        output: list[dict[str, Any]] = []
        for adapter in adapters:
            try:
                models = adapter.list_local_models(config)
                output.extend([{"adapter_id": adapter.id(), "runtime_family": adapter.runtime_family()} | item for item in models])
            except Exception as exc:  # noqa: BLE001 - discovery should report blocked adapters, not fail the whole API
                output.append(
                    {
                        "adapter_id": adapter.id(),
                        "runtime_family": adapter.runtime_family(),
                        "available": False,
                        "error": sanitize_text(str(exc)),
                    }
                )
        return output

    def load(self, adapter_id: str, model_ref: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
        adapter = self.get(adapter_id)
        session = adapter.load_model(model_ref, config)
        self._sessions[session.session_id] = session
        return {
            "session_id": session.session_id,
            "adapter_id": adapter.id(),
            "runtime_family": adapter.runtime_family(),
            "model_ref": session.model_ref,
            "config": sanitize_obj(session.config),
        }

    def unload(self, session_id: str) -> dict[str, Any]:
        session = self._sessions.pop(session_id, None)
        if not session:
            raise ValueError(f"Unknown direct runtime session: {session_id}")
        self.get(session.adapter_id).unload_model(session)
        return {"status": "unloaded", "session_id": session_id, "adapter_id": session.adapter_id}


_REGISTRY = DirectRuntimeRegistry()


def direct_runtime_registry() -> DirectRuntimeRegistry:
    return _REGISTRY
