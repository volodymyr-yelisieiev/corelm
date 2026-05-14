from __future__ import annotations

import pytest

from services.core_service.corelm_studio.compression import chunk_text, preprocess_payload
from fastapi.testclient import TestClient

from services.core_service.corelm_studio.app import create_app
from services.core_service.corelm_studio.benchmarking import BenchmarkEngine, evaluate_policy
from services.core_service.corelm_studio import connectors
from services.core_service.corelm_studio.direct_runtime import DirectRuntimeAdapter, direct_runtime_registry
from services.core_service.corelm_studio.metrics import build_provider_metrics
from services.core_service.corelm_studio.quality import evaluate_quality
from services.core_service.corelm_studio.studio_core import StudioCore


def test_ingest_updates_chat_ledger_metrics_and_replay(tmp_path):
    app = create_app(tmp_path / "studio.sqlite")
    with TestClient(app) as client:
        response = client.post(
            "/api/ingest",
            json={
                "session_id": "default",
                "branch": "corelm",
                "text": "project.name = Core LM Studio",
                "format": "markdown",
                "source": {"source_id": "test", "source_type": "manual_text"},
                "compression": {"allow_raw_commit": True},
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["ledger_entry"]["entry_id"] == "l1"
        assert payload["metrics"]["determinism_score"] == 1.0

        chat = client.get("/api/chat").json()
        ledger = client.get("/api/ledger").json()
        replay = client.get("/api/replay").json()
        provenance = client.get("/api/provenance?branch=corelm&subject=project&attribute=name").json()
        assert len(chat) == 1
        assert len(ledger) == 1
        assert replay["ok"] is True
        assert provenance["value"].lower() == "core lm studio"


def test_compression_preview_does_not_commit_to_ledger(tmp_path):
    app = create_app(tmp_path / "studio.sqlite")
    with TestClient(app) as client:
        response = client.post(
            "/api/compression/preview",
            json={
                "branch": "corelm",
                "text": " project.name = Core LM Studio \n project.name = Core LM Studio ",
                "compression": {"steps": ["clean", "dedupe", "schema_extract", "hash_compress"], "allow_raw_commit": True},
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["raw_text"] == " project.name = Core LM Studio \n project.name = Core LM Studio "
        assert payload["canonical_text"].startswith("sha256:")
        assert payload["steps"] == ["sanitize", "clean", "dedupe", "schema_extract", "hash_compress"]
        assert payload["annotations"][0]["subject"] == "project"
        assert payload["compression_ratio"] > 0
        assert client.get("/api/ledger").json() == []


def test_workflow_runs_source_to_core_to_outbound(tmp_path):
    app = create_app(tmp_path / "studio.sqlite")
    workflow = {
        "id": "test-flow",
        "name": "Test Flow",
        "nodes": [
            {"id": "n1", "type": "manual_text_input", "position": {"x": 0, "y": 0}, "config": {"text": "pipeline.order = source to core"}},
            {"id": "n2", "type": "canonicalize", "position": {"x": 200, "y": 0}, "config": {}},
            {"id": "n3", "type": "core_lm", "position": {"x": 400, "y": 0}, "config": {"format": "markdown"}},
            {"id": "n4", "type": "outbound_prompt", "position": {"x": 600, "y": 0}, "config": {"target_type": "programming_agent_packet"}},
        ],
        "edges": [
            {"id": "e1", "source": "n1", "target": "n2"},
            {"id": "e2", "source": "n2", "target": "n3"},
            {"id": "e3", "source": "n3", "target": "n4"},
        ],
    }
    with TestClient(app) as client:
        response = client.post("/api/workflows/test-flow/run", json={"workflow": workflow, "session_id": "default", "branch": "corelm"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "ok"
        assert payload["trace"][-1]["receipt"]["status"] == "prepared"
        assert client.get("/api/ledger").json()[0]["corelm"]["entry_id"] == "l1"


def test_connector_and_outbound_mocks_are_deterministic(tmp_path):
    app = create_app(tmp_path / "studio.sqlite")
    with TestClient(app) as client:
        connector = client.post(
            "/api/connectors/run",
            json={"connector_type": "openai_compatible_llm", "branch": "corelm", "config": {"prompt": "hello", "mock": True}},
        )
        assert connector.status_code == 200
        assert connector.json()["raw_payload"] == "[mock-openai] hello"
        assert connector.json()["normalized_payload"] == "[mock-openai] hello"

        rest = client.post(
            "/api/connectors/run",
            json={"connector_type": "generic_rest_input", "branch": "corelm", "config": {"url": "https://example.invalid/api"}},
        )
        assert rest.status_code == 200
        assert rest.json()["metadata"]["source_type"] == "generic_rest_input"
        assert rest.json()["normalized_payload"].startswith("{")

        outbound = client.post(
            "/api/outbound/route",
            json={
                "target_type": "programming_agent_packet",
                "content": "project.name = Core LM Studio",
                "packet_type": "engineering_task_packet",
                "config": {"mock": True},
            },
        )
        assert outbound.status_code == 200
        assert outbound.json()["status"] == "prepared"
        assert "Core LM Developer Handoff Packet" in outbound.json()["packet"]


def test_ollama_provider_metrics_and_sampling_controls(monkeypatch):
    observed = {}

    def fake_ollama_generate(url, payload, timeout, request_start_ns):
        observed["url"] = url
        observed["payload"] = payload
        observed["timeout"] = timeout
        assert request_start_ns > 0
        return (
            {
                "model": "llama3.1",
                "created_at": "2026-05-13T00:00:00Z",
                "response": "project.name = Core LM Studio",
                "done": True,
                "done_reason": "stop",
                "total_duration": 2_000_000_000,
                "load_duration": 100_000_000,
                "prompt_eval_count": 10,
                "prompt_eval_duration": 500_000_000,
                "eval_count": 20,
                "eval_duration": 1_000_000_000,
            },
            None,
        )

    monkeypatch.setattr(connectors, "_post_ollama_generate", fake_ollama_generate)
    result = connectors.run_inbound_connector(
        "ollama_local_model",
        {
            "mock": False,
            "base_url": "http://127.0.0.1:11434",
            "model": "llama3.1",
            "prompt": "Return a fact.",
            "seed": 7,
            "temperature": 0,
            "top_p": 1,
            "top_k": 40,
            "min_p": 0,
            "repeat_penalty": 1.1,
            "repeat_last_n": 64,
            "num_ctx": 4096,
            "num_predict": 128,
            "stop": ["\n\n"],
            "auto_start": False,
        },
    )

    assert observed["url"] == "http://127.0.0.1:11434/api/generate"
    assert observed["payload"]["stream"] is False
    assert observed["payload"]["options"]["seed"] == 7
    assert observed["payload"]["options"]["temperature"] == 0
    metrics = result.metadata["provider_metrics"]
    assert metrics["provider_metrics_available"] is True
    assert metrics["native"]["total_duration"] == 2_000_000_000
    assert metrics["derived"]["provider_total_latency_ms"] == 2000.0
    assert metrics["derived"]["provider_load_latency_ms"] == 100.0
    assert metrics["derived"]["prompt_tokens"] == 10
    assert metrics["derived"]["completion_tokens"] == 20
    assert metrics["derived"]["total_tokens"] == 30
    assert metrics["derived"]["prompt_tokens_per_second"] == 20.0
    assert metrics["derived"]["generation_tokens_per_second"] == 20.0
    assert metrics["derived"]["end_to_end_tokens_per_second"] == 15.0
    assert metrics["metric_sources"]["provider_total_latency_ms"] == "provider_native_derived"


def test_provider_metrics_missing_and_zero_durations_are_nullable():
    missing = build_provider_metrics("ollama", {}, 100, 200)
    assert missing["provider_metrics_available"] is False
    assert missing["derived"]["provider_total_latency_ms"] is None
    assert missing["derived"]["prompt_tokens"] is None

    zero = build_provider_metrics(
        "ollama",
        {"prompt_eval_count": 4, "prompt_eval_duration": 0, "eval_count": 6, "eval_duration": 0, "total_duration": 0},
        100,
        1_000_100,
    )
    assert zero["derived"]["prompt_tokens_per_second"] is None
    assert zero["derived"]["generation_tokens_per_second"] is None
    assert zero["derived"]["end_to_end_tokens_per_second"] is None


def test_ollama_sampling_validation():
    with pytest.raises(ValueError, match="requires seed"):
        connectors.build_ollama_generate_payload({"deterministic_benchmark": True})
    with pytest.raises(ValueError, match="top_p"):
        connectors.build_ollama_generate_payload({"top_p": 2})

    payload, metadata, warnings = connectors.build_ollama_generate_payload(
        {"deterministic_benchmark": True, "seed": 0, "unsupported": "ignored"}
    )
    assert payload["stream"] is False
    assert payload["options"]["seed"] == 0
    assert payload["options"]["temperature"] == 0.0
    assert metadata["deterministic_benchmark"] is True
    assert warnings and "Unsupported" in warnings[0]


def test_lm_studio_connector_uses_local_openai_endpoint_without_api_key(monkeypatch):
    observed = {}

    def fake_post_json(url, payload, headers, timeout=30.0):
        observed["url"] = url
        observed["payload"] = payload
        observed["headers"] = headers
        observed["timeout"] = timeout
        return {"choices": [{"message": {"content": "local_model.name = gemma-4"}}]}

    monkeypatch.setattr(connectors, "_post_json", fake_post_json)
    result = connectors.run_inbound_connector(
        "lm_studio",
        {
            "base_url": "http://127.0.0.1:1234/v1",
            "model": "gemma-4-e4b-uncensored-hauhaucs-aggressive",
            "prompt": "Return local model fact.",
            "mock": False,
            "auto_start": False,
        },
    )

    assert observed["url"] == "http://127.0.0.1:1234/v1/chat/completions"
    assert observed["payload"]["model"] == "gemma-4-e4b-uncensored-hauhaucs-aggressive"
    assert observed["headers"] == {}
    assert result.metadata["source_type"] == "lm_studio"
    assert result.normalized_payload == "local_model.name = gemma-4"


def test_connector_run_ingest_preserves_core_lm_boundary(tmp_path):
    app = create_app(tmp_path / "studio.sqlite")
    with TestClient(app) as client:
        response = client.post(
            "/api/connectors/run-ingest",
            json={
                "connector_type": "ollama_local_model",
                "session_id": "default",
                "branch": "corelm",
                "config": {"prompt": "model.role = local perturbation", "mock": True},
                "compression": {"steps": ["clean", "schema_extract"], "allow_raw_commit": True},
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["connector"]["metadata"]["source_type"] == "ollama_local_model"
        assert payload["ingest"]["ledger_entry"]["entry_id"] == "l1"
        assert payload["ingest"]["chat_message"]["origin"] == "core_lm"
        assert client.get("/api/chat").json()[0]["ledger_entry_id"] == "l1"


def test_connector_run_ingest_persists_provider_metrics_quality_and_compression(tmp_path, monkeypatch):
    def fake_ollama_generate(url, payload, timeout, request_start_ns):
        return (
            {
                "model": "llama3.1",
                "created_at": "2026-05-13T00:00:00Z",
                "response": "project.name = Core LM Studio",
                "done_reason": "stop",
                "total_duration": 1_000_000_000,
                "load_duration": 10_000_000,
                "prompt_eval_count": 2,
                "prompt_eval_duration": 100_000_000,
                "eval_count": 4,
                "eval_duration": 200_000_000,
            },
            None,
        )

    monkeypatch.setattr(connectors, "_post_ollama_generate", fake_ollama_generate)
    app = create_app(tmp_path / "studio.sqlite")
    with TestClient(app) as client:
        response = client.post(
            "/api/connectors/run-ingest",
            json={
                "connector_type": "ollama_local_model",
                "session_id": "default",
                "branch": "corelm",
                "config": {"prompt": "Return project fact.", "mock": False, "seed": 1, "auto_start": False},
                "compression": {"steps": ["clean", "schema_extract", "hash_compress"], "allow_raw_commit": True},
                "evaluator_config": {"expected_terms": ["Core LM Studio"]},
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["connector"]["metadata"]["provider_metrics"]["provider_metrics_available"] is True
        assert payload["ingest"]["metrics"]["provider_total_latency_ms"] == 1000.0
        assert payload["ingest"]["metrics"]["quality_score"] != 0.5
        assert payload["ingest"]["quality_eval"]["checks"]["keyword_coverage"]["passed"] is True

        ledger = client.get("/api/ledger/l1").json()
        assert ledger["metadata"]["provider_metrics"]["derived"]["total_tokens"] == 6
        assert ledger["metadata"]["quality_eval"]["version"] == "quality_eval.v1"
        chat = client.get("/api/chat").json()[0]
        assert chat["metadata"]["provider_metrics"]["derived"]["generation_tokens_per_second"] == 20.0
        metrics = client.get("/api/metrics").json()[-1]["metric"]
        assert metrics["provider_metrics_available"] is True
        assert metrics["total_tokens"] == 6
        quality = client.get("/api/quality?target_type=ledger_entry&target_id=l1").json()
        assert quality[-1]["evaluation"]["version"] == "quality_eval.v1"


def test_direct_runtime_registry_contract_reports_strict_and_smoke_adapters():
    registry = direct_runtime_registry()
    adapters = registry.adapters()
    by_id = {item["adapter_id"]: item for item in adapters}
    assert by_id["transformers_direct"]["strict_eligible"] is True
    assert by_id["llamacpp_direct"]["strict_eligible"] is True
    assert by_id["deterministic_direct_smoke"]["strict_eligible"] is False
    assert by_id["deterministic_direct_smoke"]["supports_token_ids"] is True


def test_strict_policy_rejects_bridge_and_non_strict_smoke_adapter():
    bridge = evaluate_policy(
        {
            "mode": "strict_direct",
            "strict": True,
            "adapter_id": "bridge:ollama_local_model",
            "model_ref": "llama3.1",
            "generation_config": {"seed": 0},
        },
        None,
    )
    assert bridge.eligible is False
    assert any("rejects bridge" in item for item in bridge.errors)

    smoke = evaluate_policy(
        {
            "mode": "strict_direct",
            "strict": True,
            "adapter_id": "deterministic_direct_smoke",
            "model_ref": "deterministic://corelm-smoke",
            "generation_config": {"seed": 0},
        },
        next(item for item in direct_runtime_registry().adapters() if item["adapter_id"] == "deterministic_direct_smoke"),
    )
    assert smoke.eligible is False
    assert any("not strict-benchmark eligible" in item for item in smoke.errors)


def test_benchmark_smoke_profile_runs_through_core_lm_and_exports_reports(tmp_path, monkeypatch):
    monkeypatch.setenv("CORELM_BENCHMARK_REPORT_DIR", str(tmp_path / "reports"))
    app = create_app(tmp_path / "studio.sqlite")
    with TestClient(app) as client:
        profiles = client.get("/api/benchmarks/profiles").json()
        assert any(profile["id"] == "builtin-runtime-conformance" for profile in profiles)

        response = client.post(
            "/api/benchmarks/run",
            json={"profile_id": "builtin-runtime-conformance", "session_id": "default", "branch": "corelm"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["summary"]["status"] == "ok"
        assert payload["summary"]["strict_result"] is False
        assert payload["trials"][0]["ingest"]["ledger_entry_id"] == "l1"
        assert payload["trials"][0]["adapter_result"]["token_trace_hash"]
        assert payload["summary"]["end_to_end_pipeline_success"] == 1.0
        assert payload["summary"]["report_export_success"] == 1.0
        assert payload["report_paths"]["json"].endswith(".json")

        runs = client.get("/api/benchmarks/runs").json()
        assert runs[-1]["id"] == payload["run_id"]
        report = client.get(f"/api/benchmarks/runs/{payload['run_id']}/report?format=csv")
        assert report.status_code == 200
        assert "token_trace_hash" in report.text


def test_benchmark_profile_id_honors_report_dir_and_creates_new_session(tmp_path, monkeypatch):
    monkeypatch.setenv("CORELM_BENCHMARK_REPORT_DIR", str(tmp_path / "api-reports"))
    app = create_app(tmp_path / "studio.sqlite")
    with TestClient(app) as client:
        response = client.post(
            "/api/benchmarks/run",
            json={"profile_id": "builtin-runtime-conformance", "session_id": "new-benchmark-session", "branch": "corelm"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["summary"]["status"] == "ok"
        assert any(item["id"] == "new-benchmark-session" for item in client.get("/api/sessions").json())

    core = StudioCore(db_path=tmp_path / "direct.sqlite")
    report_dir = tmp_path / "custom-reports"
    try:
        report = BenchmarkEngine(core).run_profile_id("builtin-runtime-conformance", "custom-session", "corelm", report_dir)
        assert report["report_paths"]["json"].startswith(str(report_dir))
        assert (report_dir / f"{report['run_id']}.json").exists()
    finally:
        core.close()


def test_failed_strict_runtime_does_not_produce_strict_result(tmp_path, monkeypatch):
    monkeypatch.setenv("CORELM_BENCHMARK_REPORT_DIR", str(tmp_path / "reports"))
    class FailingStrictAdapter(DirectRuntimeAdapter):
        adapter_id = "failing_strict_test"
        family = "failing_test"
        strict_eligible = True

        def load_model(self, model_ref, config=None):  # type: ignore[override]
            raise RuntimeError("expected load failure")

        def capability_report(self):
            return super().capability_report() | {
                "strict_eligible": True,
                "availability": "available",
                "support_classification": "DIRECT / STRICT-BENCH ELIGIBLE",
                "supports_seed": True,
            }

    direct_runtime_registry().register(FailingStrictAdapter())
    app = create_app(tmp_path / "studio.sqlite")
    with TestClient(app) as client:
        response = client.post(
            "/api/benchmarks/run",
            json={
                "session_id": "default",
                "branch": "corelm",
                "profile": {
                    "id": "strict-failing-test",
                    "name": "Strict Failing Test",
                    "mode": "strict_direct",
                    "strict": True,
                    "adapter_id": "failing_strict_test",
                    "model_ref": "local://missing",
                    "repetitions": 1,
                    "cases": [{"id": "case-1", "prompt": "strict.fact = value"}],
                    "generation_config": {"seed": 0, "temperature": 0},
                    "thresholds": {"end_to_end_pipeline_success": 1.0},
                },
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["summary"]["status"] == "blocked"
        assert payload["summary"]["strict_result"] is False


def test_topk_candidate_trace_is_not_redacted():
    from services.core_service.corelm_studio.direct_runtime import DirectGenerationResult

    result = DirectGenerationResult(
        final_text="x",
        token_ids=[1],
        decoded_tokens=["x"],
        per_token_timestamps_ms=[0.1],
        top_k_candidates=[[{"candidate_id": 7, "candidate_text": "x", "probability": 0.9}]],
    ).to_dict()
    assert result["top_k_candidates"][0][0]["candidate_id"] == 7
    assert result["top_k_candidates"][0][0]["candidate_text"] == "x"
    assert "REDACTED" not in str(result["top_k_candidates"])


def test_direct_runtime_session_load_and_unload_api(tmp_path):
    app = create_app(tmp_path / "studio.sqlite")
    with TestClient(app) as client:
        adapters = client.get("/api/direct-runtimes/adapters").json()
        assert any(item["adapter_id"] == "deterministic_direct_smoke" for item in adapters)
        models = client.get("/api/direct-runtimes/models?adapter_id=deterministic_direct_smoke").json()
        assert models[0]["model_ref"] == "deterministic://corelm-smoke"
        loaded = client.post(
            "/api/direct-runtimes/sessions/load",
            json={"adapter_id": "deterministic_direct_smoke", "model_ref": "deterministic://corelm-smoke", "config": {}},
        )
        assert loaded.status_code == 200
        session_id = loaded.json()["session_id"]
        unloaded = client.post(f"/api/direct-runtimes/sessions/{session_id}/unload")
        assert unloaded.status_code == 200
        assert unloaded.json()["status"] == "unloaded"


def test_strict_template_is_blocked_without_model_ref(tmp_path, monkeypatch):
    monkeypatch.setenv("CORELM_BENCHMARK_REPORT_DIR", str(tmp_path / "reports"))
    app = create_app(tmp_path / "studio.sqlite")
    with TestClient(app) as client:
        response = client.post(
            "/api/benchmarks/run",
            json={"profile_id": "builtin-strict-transformers-template", "session_id": "default", "branch": "corelm"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["summary"]["status"] == "blocked"
        assert payload["summary"]["strict_result"] is False
        assert any("model_ref" in item for item in payload["summary"]["errors"])


def test_replay_snapshots_workflow_runs_and_settings_are_persisted(tmp_path):
    app = create_app(tmp_path / "studio.sqlite")
    workflow = {
        "id": "persisted-run-flow",
        "name": "Persisted Run Flow",
        "nodes": [
            {"id": "n1", "type": "manual_text_input", "position": {"x": 0, "y": 0}, "config": {"text": "project.name = Core LM Studio"}},
            {"id": "n2", "type": "core_lm", "position": {"x": 200, "y": 0}, "config": {"compression": {"allow_raw_commit": True}}},
        ],
        "edges": [{"id": "e1", "source": "n1", "target": "n2"}],
    }
    with TestClient(app) as client:
        settings = client.post("/api/settings", json={"settings": {"console_density": "comfortable"}})
        assert settings.status_code == 200
        assert client.get("/api/settings").json()["console_density"] == "comfortable"

        run = client.post("/api/workflows/persisted-run-flow/run", json={"workflow": workflow})
        assert run.status_code == 200
        assert run.json()["run_id"].startswith("run-")
        runs = client.get("/api/workflows/runs").json()
        assert runs[-1]["workflow_id"] == "persisted-run-flow"
        assert runs[-1]["trace"][-1]["ledger_entry_id"] == "l1"

        snapshots = client.get("/api/replay/snapshots").json()
        assert snapshots[-1]["ok"] is True
        ledger_detail = client.get("/api/ledger/l1").json()
        assert ledger_detail["corelm"]["entry_id"] == "l1"


def test_workflow_uses_connector_normalized_payload_before_core_ingest(tmp_path):
    app = create_app(tmp_path / "studio.sqlite")
    workflow = {
        "id": "normalized-workflow",
        "name": "Normalized Workflow",
        "nodes": [
            {
                "id": "n1",
                "type": "manual_text_input",
                "position": {"x": 0, "y": 0},
                "config": {"text": "  project.name = Core LM Studio  \n\n"},
            },
            {"id": "n2", "type": "core_lm", "position": {"x": 200, "y": 0}, "config": {"compression": {"allow_raw_commit": True}}},
        ],
        "edges": [{"id": "e1", "source": "n1", "target": "n2"}],
    }
    with TestClient(app) as client:
        response = client.post("/api/workflows/normalized-workflow/run", json={"workflow": workflow})
        assert response.status_code == 200
        payload = response.json()
        assert payload["outputs"]["n1"]["raw_payload"] == "  project.name = Core LM Studio  \n\n"
        assert payload["outputs"]["n1"]["normalized_payload"] == "project.name = Core LM Studio"
        ledger = client.get("/api/ledger/l1").json()
        assert ledger["metadata"]["compression"]["raw_text"] == "[available-before-sanitized-commit]"
        assert "project.name = Core LM Studio" in ledger["metadata"]["compression"]["canonical_text"]
        assert "  project.name" not in ledger["raw_text"]


def test_quality_eval_exact_keyword_parse_and_schema_checks():
    exact = evaluate_quality("Core LM Studio", {"expected_answer": "Core LM Studio", "expected_terms": ["Studio"]})
    assert exact["checks"]["exact_match"]["passed"] is True
    assert exact["checks"]["keyword_coverage"]["passed"] is True
    assert exact["summary_score"] is not None

    structured = evaluate_quality(
        '{"name":"Core LM Studio","ok":true}',
        {
            "format_requirement": "json",
            "expected_keys": ["name", "ok"],
            "schema": {"required": ["name"], "properties": {"name": {"type": "string"}, "ok": {"type": "boolean"}}},
        },
    )
    assert structured["checks"]["parse_validity"]["passed"] is True
    assert structured["checks"]["schema_validity"]["passed"] is True
    assert structured["checks"]["required_key_coverage"]["value"] == 1.0


def test_workflow_preserves_provider_metrics_through_compression_nodes(tmp_path, monkeypatch):
    def fake_ollama_generate(url, payload, timeout, request_start_ns):
        return (
            {
                "model": "llama3.1",
                "response": "project.name = Core LM Studio",
                "done_reason": "stop",
                "total_duration": 1_000_000_000,
                "load_duration": 10_000_000,
                "prompt_eval_count": 2,
                "prompt_eval_duration": 100_000_000,
                "eval_count": 4,
                "eval_duration": 200_000_000,
            },
            None,
        )

    monkeypatch.setattr(connectors, "_post_ollama_generate", fake_ollama_generate)
    app = create_app(tmp_path / "studio.sqlite")
    workflow = {
        "id": "ollama-transform-core",
        "name": "Ollama Transform Core",
        "nodes": [
            {"id": "local", "type": "ollama_local_model", "position": {"x": 0, "y": 0}, "config": {"mock": False, "auto_start": False, "seed": 4}},
            {"id": "clean", "type": "clean_text", "position": {"x": 200, "y": 0}, "config": {}},
            {"id": "core", "type": "core_lm", "position": {"x": 400, "y": 0}, "config": {"compression": {"allow_raw_commit": True}}},
        ],
        "edges": [
            {"id": "e1", "source": "local", "target": "clean"},
            {"id": "e2", "source": "clean", "target": "core"},
        ],
    }
    with TestClient(app) as client:
        response = client.post("/api/workflows/ollama-transform-core/run", json={"workflow": workflow})
        assert response.status_code == 200
        payload = response.json()
        assert payload["trace"][1]["metadata"]["provider_metrics"]["derived"]["total_tokens"] == 6
        assert payload["trace"][2]["metrics"]["provider_metrics_available"] is True
        ledger = client.get("/api/ledger/l1").json()
        assert ledger["metadata"]["provider_metrics"]["derived"]["generation_tokens_per_second"] == 20.0


def test_connector_secret_refs_and_error_details_are_redacted(tmp_path, monkeypatch):
    app = create_app(tmp_path / "studio.sqlite")
    secret = "sk-SECRETREF1234567890"
    with TestClient(app) as client:
        saved = client.post(
            "/api/connectors",
            json={
                "connector": {
                    "id": "bad-secret-ref",
                    "name": "Bad Secret Ref",
                    "direction": "inbound",
                    "type": "manual_text",
                    "config": {},
                    "secret_refs": [secret, "OPENAI_API_KEY"],
                }
            },
        )
        assert saved.status_code == 200
        body = client.get("/api/connectors").text
        assert secret not in body
        assert "REDACTED_SECRET_REF" in body
        assert "secret_refs_json" not in body

    import services.core_service.corelm_studio.app as app_module

    def boom(connector_type, config, branch="corelm"):
        raise ValueError(f"provider failed with {secret}")

    monkeypatch.setattr(app_module, "run_inbound_connector", boom)
    app = app_module.create_app(tmp_path / "studio-errors.sqlite")
    with TestClient(app) as client:
        response = client.post("/api/connectors/run", json={"connector_type": "manual_text", "config": {}})
        assert response.status_code == 400
        assert secret not in response.text
        assert "[REDACTED_SECRET]" in response.text


def test_chat_quality_metadata_points_to_chat_quality_row(tmp_path):
    app = create_app(tmp_path / "studio.sqlite")
    with TestClient(app) as client:
        response = client.post(
            "/api/ingest",
            json={
                "text": "project.name = Core LM Studio",
                "compression": {"allow_raw_commit": True},
                "evaluator_config": {"expected_terms": ["Core LM Studio"]},
            },
        )
        assert response.status_code == 200
        chat = response.json()["chat_message"]
        quality_id = chat["metadata"]["quality_evaluation_id"]
        quality = client.get(f"/api/quality?target_type=chat_message&target_id={chat['id']}").json()
        assert quality[-1]["id"] == quality_id
        assert quality[-1]["target_type"] == "chat_message"


def test_string_false_mock_runs_real_ollama_path_without_autostart(monkeypatch):
    observed = {}

    def fake_ollama_generate(url, payload, timeout, request_start_ns):
        observed["called"] = True
        return ({"response": "ok", "eval_count": 1, "eval_duration": 1_000_000}, None)

    monkeypatch.setattr(connectors, "_post_ollama_generate", fake_ollama_generate)
    result = connectors.run_inbound_connector(
        "ollama",
        {"mock": "false", "auto_start": "false", "prompt": "hello"},
    )
    assert observed["called"] is True
    assert result.raw_payload == "ok"


def test_runtime_status_and_ensure_api_are_sanitized(tmp_path, monkeypatch):
    import services.core_service.corelm_studio.app as app_module

    def fake_runtime_status(provider="ollama", base_url=None, config=None):
        return {"provider": provider, "base_url": base_url or "http://127.0.0.1:11434", "healthy": False, "last_error": None}

    def fake_ensure(provider, base_url, config=None):
        return {"provider": provider, "base_url": base_url, "healthy": True, "managed": True}

    monkeypatch.setattr(app_module, "runtime_status", fake_runtime_status)
    monkeypatch.setattr(app_module, "ensure_runtime", fake_ensure)
    app = app_module.create_app(tmp_path / "studio.sqlite")
    with TestClient(app) as client:
        status = client.get("/api/local-runtimes").json()
        assert status["provider"] == "ollama"
        ensured = client.post("/api/local-runtimes/ollama/ensure", json={"config": {"base_url": "http://127.0.0.1:11434"}}).json()
        assert ensured["healthy"] is True
        lm_studio = client.post("/api/local-runtimes/lm_studio/ensure", json={"config": {"base_url": "http://127.0.0.1:1234/v1"}}).json()
        assert lm_studio["provider"] == "lm_studio"


def test_runtime_autostart_zero_string_is_disabled(monkeypatch):
    from services.core_service.corelm_studio import local_runtime

    monkeypatch.setattr(local_runtime, "probe_runtime", lambda provider, base_url: False)
    status = local_runtime.ensure_runtime("ollama", "http://127.0.0.1:11434", {"auto_start": "0"})
    assert status["healthy"] is False
    assert status["last_error"] == "runtime auto-start disabled"


def test_workflow_without_core_node_creates_session_before_run_persistence(tmp_path):
    app = create_app(tmp_path / "studio.sqlite")
    workflow = {
        "id": "no-core-workflow",
        "name": "No Core Workflow",
        "nodes": [
            {"id": "n1", "type": "manual_text_input", "position": {"x": 0, "y": 0}, "config": {"text": "hello"}},
        ],
        "edges": [],
    }
    with TestClient(app) as client:
        response = client.post(
            "/api/workflows/no-core-workflow/run",
            json={"workflow": workflow, "session_id": "new-session", "branch": "corelm"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        runs = client.get("/api/workflows/runs?session_id=new-session").json()
        assert runs[-1]["workflow_id"] == "no-core-workflow"
        sessions = client.get("/api/sessions").json()
        assert any(session["id"] == "new-session" for session in sessions)


def test_ingest_redacts_secrets_even_without_sanitize_step(tmp_path):
    app = create_app(tmp_path / "studio.sqlite")
    secret = "sk-testSECRET1234567890"
    with TestClient(app) as client:
        response = client.post(
            "/api/ingest",
            json={
                "session_id": "default",
                "branch": "corelm",
                "text": f"credential.api_key = {secret}",
                "format": "markdown",
                "source": {"source_id": "redaction", "source_type": "manual_text"},
                "compression": {"steps": ["clean", "schema_extract"], "allow_raw_commit": True},
            },
        )
        assert response.status_code == 200
        bodies = [
            response.text,
            client.get("/api/ledger").text,
            client.get("/api/replay").text,
            client.get("/api/provenance?branch=corelm&subject=credential&attribute=api_key").text,
        ]
        assert all(secret not in body for body in bodies)
        assert any("[REDACTED_SECRET]" in body for body in bodies)


def test_workflow_and_connector_persistence_redacts_secret_metadata(tmp_path):
    app = create_app(tmp_path / "studio.sqlite")
    secret = "sk-workflowSECRET1234567890"
    workflow = {
        "id": "secret-flow",
        "name": "Secret Flow",
        "nodes": [
            {
                "id": "n1",
                "type": "openai_compatible_llm",
                "position": {"x": 0, "y": 0},
                "config": {"api_key": secret, "prompt": "hello"},
            }
        ],
        "edges": [],
    }
    connector = {
        "id": "secret-connector",
        "name": "Secret Connector",
        "direction": "inbound",
        "type": "openai_compatible_llm",
        "config": {"api_key": secret, "model": "gpt"},
        "secret_refs": ["OPENAI_API_KEY"],
    }
    with TestClient(app) as client:
        saved_workflow = client.post("/api/workflows", json={"workflow": workflow})
        saved_connector = client.post("/api/connectors", json={"connector": connector})
        assert saved_workflow.status_code == 200
        assert saved_connector.status_code == 200
        assert secret not in client.get("/api/workflows/secret-flow").text
        assert secret not in client.get("/api/connectors").text
        assert "[REDACTED_SECRET]" in client.get("/api/workflows/secret-flow").text
        assert "OPENAI_API_KEY" in client.get("/api/connectors").text


def test_connector_secret_metadata_update_and_delete(tmp_path):
    app = create_app(tmp_path / "studio.sqlite")
    with TestClient(app) as client:
        first = {
            "id": "mutable-connector",
            "name": "Mutable Connector",
            "direction": "inbound",
            "type": "manual_text",
            "config": {},
            "secret_refs": ["SECRET_A", "SECRET_B"],
        }
        second = first | {"secret_refs": ["SECRET_C"]}
        assert client.post("/api/connectors", json={"connector": first}).status_code == 200
        assert client.post("/api/connectors", json={"connector": second}).status_code == 200
        connectors = client.get("/api/connectors").json()
        item = next(connector for connector in connectors if connector["id"] == "mutable-connector")
        assert item["secret_refs"] == ["SECRET_C"]
        assert [entry["secret_name"] for entry in item["secrets_metadata"]] == ["SECRET_C"]
        assert client.delete("/api/connectors/mutable-connector").status_code == 200
        assert "mutable-connector" not in client.get("/api/connectors").text


def test_chunk_and_hash_compression_are_effective_and_lossless_for_chunks() -> None:
    long_text = "a" * 2500
    chunks = chunk_text(long_text, max_chars=700)
    assert "".join(chunks) == long_text
    assert len(chunks) > 1

    chunked = preprocess_payload(long_text, "corelm", {"steps": ["chunking"], "max_chars": 700})
    assert "[chunk:1/" in chunked.canonical_text
    assert long_text[:700] in chunked.canonical_text

    hashed = preprocess_payload("project.name = Core LM Studio", "corelm", {"steps": ["hash_compress"]})
    assert hashed.canonical_text.startswith("sha256:")
    assert "preview:project.name = Core LM Studio" in hashed.canonical_text
