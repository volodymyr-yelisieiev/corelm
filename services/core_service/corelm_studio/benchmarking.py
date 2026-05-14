from __future__ import annotations

import csv
import hashlib
import json
import os
import statistics
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .compression import preprocess_payload
from .db import dumps_json, utc_now
from .direct_runtime import DirectGenerationResult, direct_runtime_registry, stable_hash
from .security import sanitize_obj, sanitize_text


BENCHMARK_VERSION = "direct_runtime_benchmark.v1"


def default_report_dir() -> Path:
    return Path(os.getenv("CORELM_BENCHMARK_REPORT_DIR", "reports/direct_benchmarks")).expanduser()


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def metric_source(value: Any, source: str) -> dict[str, Any]:
    return {"value": value, "source": source if value is not None else "unavailable"}


def default_benchmark_profiles() -> list[dict[str, Any]]:
    base_generation = {"seed": 0, "temperature": 0, "top_p": 1, "top_k": 1, "max_new_tokens": 48}
    compression = {
        "steps": ["sanitize", "clean", "dedupe", "canonicalize", "schema_extract", "hash_compress", "contradiction_tag"],
        "allow_raw_commit": True,
    }
    thresholds = {
        "invariant_violation_rate": 0,
        "replay_consistency_score": 1.0,
        "provenance_coverage": 1.0,
        "end_to_end_pipeline_success": 1.0,
    }
    categories = [
        ("runtime-conformance", "Runtime Conformance", "adapter.load = ok\nadapter.generate = ok"),
        ("determinism", "Determinism", "determinism.output = repeatable"),
        ("compression", "Compression", "duplicate.fact = one\nduplicate.fact = one\ncorrection: duplicate.fact changed to one"),
        ("state-dynamics", "Core LM State Dynamics", "state.metric = drift bounded"),
        ("structured-output", "Structured Output Quality", '{"subject":"structured","status":"valid","required":"present"}'),
        ("long-context-retention", "Long Context / Retention", "needle.secret = corelm-direct-runtime\nnoise = " + "x " * 80),
        ("workflow-product", "Workflow / Product Integration", "workflow.packet = route through core lm"),
        ("stress-resource", "Stress / Resource Stability", "stress.run = repeated short benchmark"),
    ]
    profiles: list[dict[str, Any]] = []
    for index, (profile_id, name, prompt) in enumerate(categories):
        profiles.append(
            {
                "id": f"builtin-{profile_id}",
                "name": name,
                "description": f"Built-in {name.lower()} smoke profile for the direct benchmark engine.",
                "benchmark_version": BENCHMARK_VERSION,
                "mode": "free_exploratory" if profile_id == "stress-resource" else "seeded_stochastic",
                "strict": False,
                "adapter_id": "deterministic_direct_smoke",
                "model_ref": "deterministic://corelm-smoke",
                "repetitions": 2 if profile_id == "determinism" else 1,
                "cases": [
                    {
                        "id": f"{profile_id}-case-1",
                        "category": name,
                        "prompt": prompt,
                        "system": "You are a local direct runtime benchmark source. Return only canonical facts.",
                        "evaluator_config": {"expected_terms": [prompt.split("=")[0].split(":")[0].strip()]},
                    }
                ],
                "generation_config": base_generation | {"seed": index},
                "trace_config": {"capture_scores": True, "top_k_trace": 5},
                "compression": compression,
                "thresholds": thresholds
                | (
                    {"exact_output_repeat_rate": 1.0, "exact_token_sequence_repeat_rate": 1.0}
                    if profile_id == "determinism"
                    else {}
                ),
                "notes": "Smoke profile uses deterministic_direct_smoke and is excluded from production strict LLM claims.",
            }
        )
    profiles.append(
        {
            "id": "builtin-strict-transformers-template",
            "name": "Strict Transformers Direct Template",
            "description": "Template for real local Hugging Face/safetensors strict runs. Requires local model_ref and optional dependencies.",
            "benchmark_version": BENCHMARK_VERSION,
            "mode": "strict_direct",
            "strict": True,
            "adapter_id": "transformers_direct",
            "model_ref": "",
            "repetitions": 2,
            "cases": [
                {
                    "id": "strict-transformers-json",
                    "category": "Determinism",
                    "prompt": "strict.answer = deterministic",
                    "system": "Return one canonical key-value fact.",
                    "evaluator_config": {"expected_terms": ["strict.answer"]},
                }
            ],
            "generation_config": base_generation,
            "trace_config": {"capture_scores": True, "top_k_trace": 5},
            "compression": compression,
            "thresholds": thresholds | {"exact_output_repeat_rate": 1.0, "exact_token_sequence_repeat_rate": 1.0},
            "notes": "Blocked until a local Transformers model and dependencies are present; no placeholder strict results are produced.",
        }
    )
    profiles.append(
        {
            "id": "builtin-strict-llamacpp-template",
            "name": "Strict llama.cpp Direct Template",
            "description": "Template for real local GGUF strict runs. Requires model_ref path and llama-cpp-python.",
            "benchmark_version": BENCHMARK_VERSION,
            "mode": "strict_direct",
            "strict": True,
            "adapter_id": "llamacpp_direct",
            "model_ref": "",
            "repetitions": 2,
            "cases": [
                {
                    "id": "strict-llamacpp-kv",
                    "category": "Determinism",
                    "prompt": "strict.answer = deterministic",
                    "system": "Return one canonical key-value fact.",
                    "evaluator_config": {"expected_terms": ["strict.answer"]},
                }
            ],
            "generation_config": base_generation,
            "trace_config": {"capture_scores": False},
            "compression": compression,
            "thresholds": thresholds | {"exact_output_repeat_rate": 1.0},
            "notes": "Blocked until a local GGUF model and dependencies are present; no placeholder strict results are produced.",
        }
    )
    return profiles


def normalize_profile(profile: dict[str, Any]) -> dict[str, Any]:
    profile = dict(profile or {})
    profile.setdefault("id", f"profile-{uuid.uuid4().hex[:10]}")
    profile.setdefault("name", profile["id"])
    profile.setdefault("description", "")
    profile.setdefault("benchmark_version", BENCHMARK_VERSION)
    profile.setdefault("mode", "seeded_stochastic")
    profile.setdefault("strict", profile.get("mode") == "strict_direct")
    profile.setdefault("adapter_id", "deterministic_direct_smoke")
    profile.setdefault("model_ref", "deterministic://corelm-smoke")
    profile.setdefault("repetitions", 1)
    profile.setdefault("cases", [{"id": "case-1", "prompt": "benchmark.fact = ok", "category": "Runtime Conformance"}])
    profile.setdefault("generation_config", {"seed": 0, "temperature": 0, "top_p": 1, "top_k": 1, "max_new_tokens": 48})
    profile.setdefault("trace_config", {})
    profile.setdefault("compression", {"allow_raw_commit": True})
    profile.setdefault("thresholds", {})
    return sanitize_obj(profile)


@dataclass
class BenchmarkPolicyResult:
    eligible: bool
    strict_result: bool
    classification: str
    warnings: list[str]
    errors: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "eligible": self.eligible,
            "strict_result": self.strict_result,
            "classification": self.classification,
            "warnings": self.warnings,
            "errors": self.errors,
        }


def evaluate_policy(profile: dict[str, Any], adapter_report: dict[str, Any] | None = None) -> BenchmarkPolicyResult:
    mode = str(profile.get("mode") or "").lower()
    strict_requested = bool(profile.get("strict")) or mode == "strict_direct"
    adapter_id = str(profile.get("adapter_id") or "")
    warnings: list[str] = []
    errors: list[str] = []
    classification = "BRIDGE / NON-STRICT" if adapter_id.startswith("bridge:") or profile.get("connector_type") else "DIRECT / PARTIAL METRICS"
    strict_result = False
    if adapter_report:
        classification = str(adapter_report.get("support_classification") or classification)
    if strict_requested:
        if adapter_id.startswith("bridge:") or profile.get("connector_type"):
            errors.append("strict_direct mode rejects bridge/API connector profiles")
        if not adapter_report:
            errors.append(f"strict_direct mode requires a known direct adapter: {adapter_id}")
        elif not adapter_report.get("strict_eligible"):
            errors.append(f"adapter {adapter_id} is not strict-benchmark eligible")
        elif adapter_report.get("availability") != "available":
            errors.append(f"adapter {adapter_id} is blocked: {adapter_report.get('last_error') or adapter_report.get('availability')}")
        if not profile.get("model_ref"):
            errors.append("strict_direct mode requires explicit model_ref")
        seed = (profile.get("generation_config") or {}).get("seed")
        if seed is None or str(seed) == "":
            errors.append("strict_direct mode requires explicit seed")
        strict_result = not errors
    else:
        warnings.append("run is non-strict and excluded from strict benchmark summaries")
    return BenchmarkPolicyResult(
        eligible=not errors,
        strict_result=strict_result,
        classification=classification,
        warnings=warnings,
        errors=errors,
    )


def compression_metrics(packet: dict[str, Any]) -> dict[str, Any]:
    raw = str(packet.get("raw_text") or "")
    canonical = str(packet.get("canonical_text") or "")
    raw_lines = [line.strip().lower() for line in raw.splitlines() if line.strip()]
    unique_lines = set(raw_lines)
    raw_tokens = raw.split()
    canonical_tokens = canonical.split()
    return {
        "raw_char_count": len(raw),
        "raw_byte_count": len(raw.encode("utf-8")),
        "raw_token_count": len(raw_tokens),
        "canonical_char_count": len(canonical),
        "canonical_byte_count": len(canonical.encode("utf-8")),
        "canonical_token_count": len(canonical_tokens),
        "compressed_state_byte_count": len(canonical.encode("utf-8")),
        "compressed_history_byte_count": len(canonical.encode("utf-8")),
        "void_token_count": max(0, len(raw_tokens) - len(canonical_tokens)),
        "duplicate_items_removed": max(0, len(raw_lines) - len(unique_lines)),
        "contradiction_candidates_found": len(packet.get("contradiction_candidates", []) or []),
        "contradiction_candidates_resolved": 0,
        "schema_fields_extracted": len(packet.get("structured_extraction", []) or []),
        "key_value_pairs_extracted": len(
            [
                item
                for item in packet.get("structured_extraction", []) or []
                if "key-value-extracted" in [str(tag) for tag in item.get("tags", [])]
            ]
        ),
        "digest_stability": 1.0 if packet.get("digest") else 0.0,
        "canonicalization_applied": "canonicalize" in (packet.get("steps") or []),
        "raw_to_canonical_ratio": len(canonical.encode("utf-8")) / max(1, len(raw.encode("utf-8"))),
        "canonical_to_state_ratio": 1.0,
        "overall_compression_ratio": packet.get("compression_ratio"),
        "compression_latency_ms": packet.get("compression_latency_ms"),
        "compression_throughput_chars_per_sec": None,
        "compression_throughput_tokens_per_sec": None,
        "retention_after_compression_exact_match": 1.0 if raw.strip() == canonical.strip() else 0.0,
        "retention_after_compression_keyword_coverage": None,
        "reconstruction_error": None,
        "state_compression_ratio": packet.get("compression_ratio"),
        "history_compression_ratio": packet.get("compression_ratio"),
    }


def _hash_repeat_rate(values: list[str]) -> float:
    if not values:
        return 0.0
    first = values[0]
    return sum(1 for value in values if value == first) / len(values)


def _prefix_stability(token_sequences: list[list[Any]], k: int) -> float:
    if not token_sequences:
        return 0.0
    first = token_sequences[0][:k]
    return sum(1 for sequence in token_sequences if sequence[:k] == first) / len(token_sequences)


def determinism_metrics(trials: list[dict[str, Any]]) -> dict[str, Any]:
    outputs = [str(item.get("adapter_result", {}).get("final_text") or "") for item in trials if item.get("status") == "ok"]
    token_sequences = [item.get("adapter_result", {}).get("token_ids") or [] for item in trials if item.get("status") == "ok"]
    output_hashes = [_hash_text(output) for output in outputs]
    token_hashes = [stable_hash(sequence) for sequence in token_sequences]
    sampler_hashes = [stable_hash(item.get("adapter_result", {}).get("sampler_config_actual") or {}) for item in trials if item.get("status") == "ok"]
    manifest_hashes = [stable_hash(item.get("manifest_fragment") or {}) for item in trials if item.get("status") == "ok"]
    return {
        "exact_output_repeat_rate": _hash_repeat_rate(output_hashes),
        "exact_token_sequence_repeat_rate": _hash_repeat_rate(token_hashes),
        "prefix_stability_at_1": _prefix_stability(token_sequences, 1),
        "prefix_stability_at_5": _prefix_stability(token_sequences, 5),
        "prefix_stability_at_10": _prefix_stability(token_sequences, 10),
        "output_hash_repeat_rate": _hash_repeat_rate(output_hashes),
        "token_trace_hash_repeat_rate": _hash_repeat_rate(token_hashes),
        "sampler_config_match_rate": _hash_repeat_rate(sampler_hashes),
        "run_manifest_match_rate": _hash_repeat_rate(manifest_hashes),
        "logit_trace_divergence": None,
        "topk_candidate_divergence": None,
        "entropy_trace_l2": None,
        "confidence_trace_l2": None,
        "restart_reproducibility_rate": None,
        "state_replay_consistency_score": _mean_metric(trials, "replay_consistency_score"),
        "direct_runtime_determinism_score": min(_hash_repeat_rate(output_hashes), _hash_repeat_rate(token_hashes)),
        "end_to_end_determinism_score": min(_hash_repeat_rate(output_hashes), _mean_metric(trials, "replay_consistency_score")),
    }


def _mean_metric(trials: list[dict[str, Any]], key: str) -> float:
    values = [
        float(item.get("metrics", {}).get(key))
        for item in trials
        if isinstance(item.get("metrics", {}).get(key), (int, float)) and not isinstance(item.get("metrics", {}).get(key), bool)
    ]
    return sum(values) / max(1, len(values))


def runtime_summary(trials: list[dict[str, Any]]) -> dict[str, Any]:
    telemetry = [item.get("adapter_result", {}).get("telemetry") or {} for item in trials if item.get("status") == "ok"]

    def mean(key: str) -> float | None:
        values = [float(item[key]) for item in telemetry if isinstance(item.get(key), (int, float))]
        return None if not values else statistics.mean(values)

    return {
        "load_ms": mean("load_ms"),
        "warmup_ms": mean("warmup_ms"),
        "ttft_ms": mean("ttft_ms"),
        "total_ms": mean("total_ms"),
        "prompt_eval_ms": mean("prompt_eval_ms"),
        "decode_ms": mean("decode_ms"),
        "prompt_tps": mean("prompt_tps"),
        "decode_tps": mean("decode_tps"),
        "end_to_end_tps": mean("end_to_end_tps"),
        "prompt_token_count": mean("prompt_token_count"),
        "actual_generated_token_count": mean("actual_generated_token_count"),
        "total_token_count": mean("total_token_count"),
        "peak_ram_mb": max([float(item["peak_ram_mb"]) for item in telemetry if isinstance(item.get("peak_ram_mb"), (int, float))], default=None),
        "avg_ram_mb": mean("avg_ram_mb"),
        "peak_vram_mb": max([float(item["peak_vram_mb"]) for item in telemetry if isinstance(item.get("peak_vram_mb"), (int, float))], default=None),
        "avg_vram_mb": mean("avg_vram_mb"),
    }


def verdict(summary: dict[str, Any], thresholds: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {}
    passed = True
    for metric, expected in thresholds.items():
        actual = summary.get(metric)
        ok = True
        if actual is None:
            ok = False
        elif isinstance(expected, dict):
            if "min" in expected:
                ok = ok and float(actual) >= float(expected["min"])
            if "max" in expected:
                ok = ok and float(actual) <= float(expected["max"])
            if "eq" in expected:
                ok = ok and float(actual) == float(expected["eq"])
        else:
            ok = float(actual) >= float(expected) if float(expected) > 0 else float(actual) <= float(expected)
        checks[metric] = {"passed": ok, "actual": actual, "threshold": expected}
        passed = passed and ok
    return {"passed": passed, "checks": checks}


class BenchmarkEngine:
    def __init__(self, core: Any) -> None:
        self.core = core
        self.registry = direct_runtime_registry()

    def ensure_builtin_profiles(self) -> None:
        for profile in default_benchmark_profiles():
            if not self.core.db.get_benchmark_profile(profile["id"]):
                self.core.db.upsert_benchmark_profile(profile)

    def list_profiles(self) -> list[dict[str, Any]]:
        self.ensure_builtin_profiles()
        return self.core.db.list_benchmark_profiles()

    def get_profile(self, profile_id: str) -> dict[str, Any] | None:
        self.ensure_builtin_profiles()
        return self.core.db.get_benchmark_profile(profile_id)

    def save_profile(self, profile: dict[str, Any]) -> dict[str, Any]:
        return self.core.db.upsert_benchmark_profile(normalize_profile(profile))

    def run_profile(
        self,
        profile: dict[str, Any],
        session_id: str = "default",
        branch: str = "corelm",
        report_dir: str | Path | None = None,
    ) -> dict[str, Any]:
        profile = normalize_profile(profile)
        if hasattr(self.core, "ensure_session"):
            self.core.ensure_session(session_id, f"Session {session_id}", 0, branch)
        adapter_id = str(profile.get("adapter_id"))
        adapter_report = next((item for item in self.registry.adapters() if item.get("adapter_id") == adapter_id), None)
        policy = evaluate_policy(profile, adapter_report)
        run_id = f"bench-{uuid.uuid4().hex[:12]}"
        report_dir = Path(report_dir) if report_dir else default_report_dir()
        manifest = {
            "run_id": run_id,
            "benchmark_version": BENCHMARK_VERSION,
            "profile_id": profile["id"],
            "profile_hash": stable_hash(profile),
            "adapter_id": adapter_id,
            "adapter_report": adapter_report,
            "model_ref": profile.get("model_ref"),
            "mode": profile.get("mode"),
            "strict": bool(profile.get("strict")),
            "policy": policy.to_dict(),
            "generation_config_hash": stable_hash(profile.get("generation_config") or {}),
            "adapter_config_hash": stable_hash(profile.get("adapter_config") or {}),
            "build_hash": self._build_hash(),
            "started_at": utc_now(),
        }
        self.core.db.start_benchmark_run(
            run_id=run_id,
            profile_id=str(profile["id"]),
            session_id=session_id,
            mode=str(profile.get("mode")),
            strict=bool(profile.get("strict")),
            adapter_id=adapter_id,
            manifest=manifest,
        )
        if not policy.eligible:
            summary = {
                "status": "blocked",
                "strict_result": False,
                "policy": policy.to_dict(),
                "warnings": policy.warnings,
                "errors": policy.errors,
                "end_to_end_pipeline_success": 0.0,
            }
            payload = self._finish_run(run_id, profile, manifest, [], summary, report_dir)
            return payload

        adapter = self.registry.get(adapter_id)
        session = None
        trials: list[dict[str, Any]] = []
        run_warnings = list(policy.warnings)
        try:
            session = adapter.load_model(str(profile.get("model_ref") or ""), profile.get("adapter_config") or {})
            warmup = adapter.warmup(session)
            run_warnings.extend([str(item) for item in warmup.get("warnings", []) or []])
            repetitions = max(1, int(profile.get("repetitions") or 1))
            for case in profile.get("cases") or []:
                for repetition_index in range(repetitions):
                    trial = self._run_trial(profile, case, repetition_index, session, warmup, session_id, branch, run_id)
                    trials.append(trial)
                    self.core.db.record_benchmark_trial(run_id, trial)
        except Exception as exc:  # noqa: BLE001 - benchmark should persist blocked/failed state
            run_warnings.append(sanitize_text(str(exc)))
            trials.append(
                {
                    "id": f"trial-{uuid.uuid4().hex[:12]}",
                    "run_id": run_id,
                    "case_id": "load-or-run",
                    "repetition_index": 0,
                    "status": "blocked" if bool(profile.get("strict")) else "error",
                    "input": {},
                    "adapter_result": {},
                    "ingest": {},
                    "metrics": {},
                    "warnings": [sanitize_text(str(exc))],
                    "manifest_fragment": {"adapter_id": adapter_id, "model_ref": profile.get("model_ref")},
                }
            )
            self.core.db.record_benchmark_trial(run_id, trials[-1])
        finally:
            if session is not None:
                try:
                    adapter.unload_model(session)
                except Exception as exc:  # noqa: BLE001
                    run_warnings.append(f"unload failed: {sanitize_text(str(exc))}")
        summary = self._summarize(profile, policy, trials, run_warnings)
        return self._finish_run(run_id, profile, manifest, trials, summary, report_dir)

    def run_profile_id(
        self,
        profile_id: str,
        session_id: str = "default",
        branch: str = "corelm",
        report_dir: str | Path | None = None,
    ) -> dict[str, Any]:
        profile = self.get_profile(profile_id)
        if not profile:
            raise ValueError(f"Unknown benchmark profile: {profile_id}")
        return self.run_profile(profile, session_id, branch, report_dir)

    def _run_trial(
        self,
        profile: dict[str, Any],
        case: dict[str, Any],
        repetition_index: int,
        session: Any,
        warmup: dict[str, Any],
        session_id: str,
        branch: str,
        run_id: str,
    ) -> dict[str, Any]:
        trial_id = f"trial-{uuid.uuid4().hex[:12]}"
        case_id = str(case.get("id") or f"case-{repetition_index}")
        prompt = str(case.get("prompt") or "")
        system = str(case.get("system") or "") or None
        adapter = self.registry.get(str(profile.get("adapter_id")))
        generation_config = dict(profile.get("generation_config") or {})
        trace_config = dict(profile.get("trace_config") or {})
        result: DirectGenerationResult = adapter.generate(session, prompt, system, generation_config, trace_config)
        result_dict = result.to_dict()
        result_dict["telemetry"] = dict(result_dict.get("telemetry") or {}) | {"warmup_ms": warmup.get("warmup_ms")}
        compression_start = time.perf_counter_ns()
        preview = preprocess_payload(result.final_text, branch, profile.get("compression") or {}, case.get("annotations", []))
        compression_packet = preview.to_dict() | {"compression_latency_ms": (time.perf_counter_ns() - compression_start) / 1_000_000.0}
        source = {
            "source_id": trial_id,
            "source_type": "direct_runtime_benchmark",
            "branch": branch,
            "benchmark_run_id": run_id,
            "benchmark_trial_id": trial_id,
            "benchmark_profile_id": profile.get("id"),
            "direct_runtime": {
                "adapter_id": profile.get("adapter_id"),
                "runtime_family": session.runtime_family,
                "model_ref": session.model_ref,
                "strict_result": bool(profile.get("strict")),
            },
            "direct_runtime_result": result_dict,
            "token_trace": {
                "token_ids": result.token_ids,
                "decoded_tokens": result.decoded_tokens,
                "per_token_timestamps_ms": result.per_token_timestamps_ms,
                "token_trace_hash": result_dict.get("token_trace_hash"),
            },
            "sampler": result.sampler_config_actual,
            "runtime_telemetry": result.telemetry,
            "warnings": result.warnings,
        }
        ingest = self.core.ingest(
            session_id=session_id,
            branch=branch,
            text=result.final_text,
            source=source,
            workflow_id=f"benchmark:{run_id}",
            fmt=str(case.get("format") or "markdown"),
            compression=profile.get("compression") or {},
            annotations=case.get("annotations", []),
            evaluator_config=case.get("evaluator_config") or profile.get("evaluator_config") or {},
        )
        metrics = dict(ingest.get("metrics") or {})
        metrics.update(compression_metrics(ingest.get("compression") or compression_packet))
        metrics.update(
            {
                "runtime_family": session.runtime_family,
                "runtime_version": result.runtime.get("runtime_version"),
                "adapter_id": profile.get("adapter_id"),
                "model_id": result.model.get("model_id"),
                "model_path_or_ref": result.model.get("model_path_or_ref"),
                "quantization": result.model.get("quantization"),
                "precision": result.model.get("precision"),
                "backend": result.runtime.get("engine"),
                "device": (profile.get("adapter_config") or {}).get("device"),
                "threads": (profile.get("adapter_config") or {}).get("threads"),
                "n_ctx": (profile.get("adapter_config") or {}).get("n_ctx") or (profile.get("adapter_config") or {}).get("num_ctx"),
                "n_predict": generation_config.get("max_new_tokens") or generation_config.get("num_predict"),
                "actual_generated_token_count": result.telemetry.get("actual_generated_token_count"),
                "prompt_token_count": result.telemetry.get("prompt_token_count"),
                "total_token_count": result.telemetry.get("total_token_count"),
                "prompt_hash": _hash_text(prompt),
                "system_hash": _hash_text(system or ""),
                "generation_config_hash": stable_hash(generation_config),
                "adapter_config_hash": stable_hash(profile.get("adapter_config") or {}),
                "build_hash": self._build_hash(),
                "end_to_end_pipeline_success": 1.0 if ingest.get("status") == "ok" else 0.0,
                "chat_publish_success": 1.0 if ingest.get("chat_message") else 0.0,
                "ledger_commit_success": 1.0 if ingest.get("ledger_entry") else 0.0,
                "replay_snapshot_success": 1.0 if ingest.get("replay") else 0.0,
                "provenance_link_success": 1.0 if ingest.get("event_id") else 0.0,
                "report_export_success": None,
            }
        )
        for key, value in result.telemetry.items():
            metrics.setdefault(key, value)
        return sanitize_obj(
            {
                "id": trial_id,
                "run_id": run_id,
                "case_id": case_id,
                "repetition_index": repetition_index,
                "status": "ok",
                "input": {"prompt_hash": _hash_text(prompt), "system_hash": _hash_text(system or ""), "case": case},
                "adapter_result": result_dict,
                "ingest": {
                    "event_id": ingest.get("event_id"),
                    "ledger_entry_id": (ingest.get("ledger_entry") or {}).get("entry_id"),
                    "chat_message_id": (ingest.get("chat_message") or {}).get("id"),
                    "digest": ingest.get("digest"),
                    "replay": ingest.get("replay"),
                    "compression": ingest.get("compression"),
                    "quality_eval": ingest.get("quality_eval"),
                },
                "metrics": metrics,
                "warnings": result.warnings,
                "manifest_fragment": {
                    "adapter_id": profile.get("adapter_id"),
                    "model_ref": session.model_ref,
                    "seed": result.seed_actual,
                    "sampler": result.sampler_config_actual,
                    "prompt_hash": _hash_text(prompt),
                    "system_hash": _hash_text(system or ""),
                },
            }
        )

    def _summarize(self, profile: dict[str, Any], policy: BenchmarkPolicyResult, trials: list[dict[str, Any]], warnings: list[str]) -> dict[str, Any]:
        ok_trials = [item for item in trials if item.get("status") == "ok"]
        summary = {
            "status": "ok" if ok_trials and len(ok_trials) == len(trials) else ("blocked" if any(item.get("status") == "blocked" for item in trials) else "error"),
            "benchmark_version": BENCHMARK_VERSION,
            "profile_id": profile.get("id"),
            "profile_name": profile.get("name"),
            "mode": profile.get("mode"),
            "strict_result": False,
            "policy": policy.to_dict(),
            "trial_count": len(trials),
            "ok_trial_count": len(ok_trials),
            "warnings": warnings + [warning for trial in trials for warning in trial.get("warnings", [])],
        }
        runtime = runtime_summary(trials)
        determinism = determinism_metrics(trials)
        state_quality = {
            "invariant_violation_rate": _mean_metric(trials, "invariant_violation_rate"),
            "replay_consistency_score": _mean_metric(trials, "replay_consistency_score"),
            "determinism_score": _mean_metric(trials, "determinism_score"),
            "provenance_coverage": _mean_metric(trials, "provenance_coverage"),
            "commit_accept_rate": 1.0 if ok_trials else 0.0,
            "rollback_or_reject_rate": 0.0 if ok_trials else 1.0,
            "branch_contamination_rate": 0.0,
            "supersession_accuracy": None,
            "workflow_node_success_rate": 1.0 if ok_trials else 0.0,
            "end_to_end_pipeline_success": _mean_metric(trials, "end_to_end_pipeline_success"),
            "chat_publish_success": _mean_metric(trials, "chat_publish_success"),
            "ledger_commit_success": _mean_metric(trials, "ledger_commit_success"),
            "replay_snapshot_success": _mean_metric(trials, "replay_snapshot_success"),
            "provenance_link_success": _mean_metric(trials, "provenance_link_success"),
            "benchmark_profile_repeatability": determinism.get("end_to_end_determinism_score"),
        }
        compression_keys = [
            "raw_to_canonical_ratio",
            "canonical_to_state_ratio",
            "overall_compression_ratio",
            "duplicate_items_removed",
            "contradiction_candidates_found",
            "schema_fields_extracted",
            "void_token_count",
        ]
        compression_summary = {key: _mean_metric(trials, key) for key in compression_keys}
        summary.update(runtime)
        summary.update(determinism)
        summary.update(state_quality)
        summary.update(compression_summary)
        summary["verdict"] = verdict(summary, profile.get("thresholds") or {})
        if not policy.eligible:
            summary["verdict"]["passed"] = False
        summary["strict_result"] = bool(policy.strict_result and summary["status"] == "ok" and summary["verdict"].get("passed"))
        return sanitize_obj(summary)

    def _finish_run(
        self,
        run_id: str,
        profile: dict[str, Any],
        manifest: dict[str, Any],
        trials: list[dict[str, Any]],
        summary: dict[str, Any],
        report_dir: Path,
    ) -> dict[str, Any]:
        paths = self.report_paths(run_id, report_dir)
        summary["report_export_success"] = 1.0 if paths else 0.0
        report = {
            "run_id": run_id,
            "profile": profile,
            "manifest": manifest | {"completed_at": utc_now(), "trial_count": len(trials)},
            "summary": summary,
            "trials": trials,
            "report_paths": paths,
        }
        paths = self.write_reports(report, report_dir)
        report["report_paths"] = paths
        self.core.db.finish_benchmark_run(run_id, summary.get("status", "ok"), report["manifest"], summary, report, paths)
        return sanitize_obj(report | {"report_paths": paths})

    def report_paths(self, run_id: str, report_dir: Path) -> dict[str, str]:
        return {
            "json": str(report_dir / f"{run_id}.json"),
            "markdown": str(report_dir / f"{run_id}.md"),
            "csv": str(report_dir / f"{run_id}.csv"),
        }

    def write_reports(self, report: dict[str, Any], report_dir: Path) -> dict[str, str]:
        report_dir.mkdir(parents=True, exist_ok=True)
        run_id = str(report["run_id"])
        paths = report.get("report_paths") or self.report_paths(run_id, report_dir)
        report["report_paths"] = paths
        json_path = Path(paths["json"])
        md_path = Path(paths["markdown"])
        csv_path = Path(paths["csv"])
        json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
        lines = [
            f"# Direct Runtime Benchmark Run {run_id}",
            "",
            f"Profile: **{report['profile'].get('name')}**",
            f"Status: **{report['summary'].get('status')}**",
            f"Strict result: **{report['summary'].get('strict_result')}**",
            f"Verdict: **{report['summary'].get('verdict', {}).get('passed')}**",
            "",
            "## Key Metrics",
            "",
            "| Metric | Value |",
            "|---|---:|",
        ]
        for key in (
            "exact_output_repeat_rate",
            "exact_token_sequence_repeat_rate",
            "replay_consistency_score",
            "invariant_violation_rate",
            "overall_compression_ratio",
            "total_ms",
            "decode_tps",
        ):
            lines.append(f"| {key} | {report['summary'].get(key)} |")
        lines.extend(["", "## Warnings", ""])
        for warning in report["summary"].get("warnings", []) or []:
            lines.append(f"- {warning}")
        md_path.write_text("\n".join(lines), encoding="utf-8")
        with csv_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["run_id", "case_id", "repetition_index", "status", "output_hash", "token_trace_hash", "ledger_entry_id"])
            for trial in report.get("trials", []):
                writer.writerow(
                    [
                        run_id,
                        trial.get("case_id"),
                        trial.get("repetition_index"),
                        trial.get("status"),
                        trial.get("adapter_result", {}).get("output_hash"),
                        trial.get("adapter_result", {}).get("token_trace_hash"),
                        trial.get("ingest", {}).get("ledger_entry_id"),
                    ]
                )
        return paths

    def _build_hash(self) -> str:
        basis = {
            "benchmark_version": BENCHMARK_VERSION,
            "python": os.sys.version.split()[0],
            "cwd": str(Path.cwd()),
        }
        return stable_hash(basis)


def report_as_text(report: dict[str, Any], fmt: str) -> str:
    fmt = fmt.lower()
    if fmt == "json":
        return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True)
    if fmt in {"md", "markdown"}:
        summary = report.get("summary", {})
        return "\n".join(
            [
                f"# Direct Runtime Benchmark Run {report.get('run_id')}",
                "",
                f"Profile: **{report.get('profile', {}).get('name')}**",
                f"Status: **{summary.get('status')}**",
                f"Strict result: **{summary.get('strict_result')}**",
                f"Verdict: **{summary.get('verdict', {}).get('passed')}**",
            ]
        )
    if fmt == "csv":
        rows = ["run_id,case_id,repetition_index,status,output_hash,token_trace_hash,ledger_entry_id"]
        for trial in report.get("trials", []):
            rows.append(
                ",".join(
                    [
                        str(report.get("run_id")),
                        str(trial.get("case_id")),
                        str(trial.get("repetition_index")),
                        str(trial.get("status")),
                        str(trial.get("adapter_result", {}).get("output_hash")),
                        str(trial.get("adapter_result", {}).get("token_trace_hash")),
                        str(trial.get("ingest", {}).get("ledger_entry_id")),
                    ]
                )
            )
        return "\n".join(rows)
    raise ValueError(f"Unsupported report format: {fmt}")
