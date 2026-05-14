from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from .benchmarking import BenchmarkEngine, report_as_text
from .compression import preprocess_payload
from .connectors import connector_catalog, run_inbound_connector
from .direct_runtime import direct_runtime_registry
from .local_runtime import ensure_runtime, runtime_status, stop_owned_runtimes
from .outbound import route_outbound
from .schemas import (
    BenchmarkProfileSaveRequest,
    BenchmarkRunRequest,
    ChatPromoteRequest,
    CompressionPreviewRequest,
    ConnectorIngestRequest,
    ChatRouteRequest,
    ConnectorRunRequest,
    ConnectorSaveRequest,
    DirectRuntimeLoadRequest,
    IngestRequest,
    LocalRuntimeEnsureRequest,
    OutboundRouteRequest,
    SessionCreateRequest,
    SettingsUpdateRequest,
    WorkflowRunRequest,
    WorkflowSaveRequest,
)
from .security import sanitize_text
from .studio_core import StudioCore
from .workflow import WorkflowEngine


def safe_error(exc: Exception) -> str:
    return sanitize_text(str(exc))


def create_app(db_path: str | Path | None = None) -> FastAPI:
    core = StudioCore(db_path=db_path)
    engine = WorkflowEngine(core)
    benchmark_engine = BenchmarkEngine(core)
    runtime_registry = direct_runtime_registry()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.core = core
        try:
            yield
        finally:
            stop_owned_runtimes()
            core.close()

    app = FastAPI(title="Core LM Studio Sidecar", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "app://core-lm-studio", "null"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"status": "ok", "service": "core-lm-studio", "state": core.state_summary("default")}

    @app.get("/api/state")
    def state(session_id: str = "default") -> dict[str, Any]:
        return core.state_summary(session_id)

    @app.get("/api/sessions")
    def sessions() -> list[dict[str, Any]]:
        return core.list_sessions()

    @app.post("/api/sessions")
    def create_session(request: SessionCreateRequest) -> dict[str, Any]:
        return core.create_session(request.name, request.seed, request.current_branch, request.id)

    @app.post("/api/connectors/run")
    def run_connector(request: ConnectorRunRequest) -> dict[str, Any]:
        try:
            return run_inbound_connector(request.connector_type, request.config, request.branch).to_dict()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=safe_error(exc)) from exc

    @app.post("/api/connectors/run-ingest")
    def run_connector_ingest(request: ConnectorIngestRequest) -> dict[str, Any]:
        try:
            connector_result = run_inbound_connector(request.connector_type, request.config, request.branch)
            ingest = core.ingest(
                session_id=request.session_id,
                branch=request.branch,
                text=connector_result.normalized_payload or connector_result.raw_payload,
                source=connector_result.metadata | {"connector_type": request.connector_type},
                workflow_id=request.workflow_id,
                fmt=request.format,
                compression=request.compression,
                annotations=request.annotations,
                evaluator_config=request.evaluator_config or request.config.get("evaluator_config", {}),
            )
            return {"connector": connector_result.to_dict(), "ingest": ingest}
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=safe_error(exc)) from exc

    @app.get("/api/connectors/types")
    def connectors() -> dict[str, Any]:
        return {
            "inbound": [
                "openai_compatible_llm",
                "lm_studio",
                "ollama_local_model",
                "file_input",
                "folder_watcher",
                "generic_web_api_fetch",
                "clipboard_input",
                "generic_rest_input",
                "manual_text",
                "shell_cli_capture",
            ],
            "outbound": [
                "generic_http_rest",
                "openai_compatible_outbound",
                "local_model_outbound",
                "file_export",
                "clipboard_export",
                "shell_cli_handoff",
                "programming_agent_packet",
            ],
        }

    @app.get("/api/connectors/catalog")
    def connectors_catalog() -> dict[str, Any]:
        return connector_catalog()

    @app.get("/api/connectors")
    def list_connectors() -> list[dict[str, Any]]:
        return core.db.list_connectors()

    @app.post("/api/connectors")
    def save_connector(request: ConnectorSaveRequest) -> dict[str, Any]:
        connector = request.connector
        if "id" not in connector:
            raise HTTPException(status_code=400, detail="connector.id is required")
        return core.db.upsert_connector(connector)

    @app.delete("/api/connectors/{connector_id}")
    def delete_connector(connector_id: str) -> dict[str, Any]:
        if not core.db.delete_connector(connector_id):
            raise HTTPException(status_code=404, detail="connector not found")
        return {"status": "deleted", "id": connector_id}

    @app.post("/api/ingest")
    def ingest(request: IngestRequest) -> dict[str, Any]:
        try:
            return core.ingest(
                session_id=request.session_id,
                branch=request.branch,
                text=request.text,
                source=request.source,
                workflow_id=request.workflow_id,
                fmt=request.format,
                compression=request.compression,
                annotations=request.annotations,
                evaluator_config=request.evaluator_config,
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=safe_error(exc)) from exc

    @app.post("/api/compression/preview")
    def compression_preview(request: CompressionPreviewRequest) -> dict[str, Any]:
        try:
            return preprocess_payload(
                request.text,
                request.branch,
                request.compression,
                request.annotations,
            ).to_dict()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=safe_error(exc)) from exc

    @app.get("/api/compression")
    def compression_lookup(target_type: str, target_id: str, session_id: str = "default") -> dict[str, Any]:
        try:
            return core.compression_packet(session_id, target_type, target_id)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=safe_error(exc)) from exc

    @app.get("/api/local-runtimes")
    def local_runtimes(provider: str = "ollama", base_url: str | None = None) -> dict[str, Any]:
        return runtime_status(provider, base_url)

    @app.post("/api/local-runtimes/{provider}/ensure")
    def ensure_local_runtime(provider: str, request: LocalRuntimeEnsureRequest) -> dict[str, Any]:
        target_provider = request.provider or provider
        default_base_url = "http://127.0.0.1:11434" if target_provider == "ollama" else "http://127.0.0.1:1234/v1"
        try:
            return ensure_runtime(target_provider, request.base_url or str(request.config.get("base_url") or default_base_url), request.config)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=safe_error(exc)) from exc

    @app.get("/api/direct-runtimes/adapters")
    def direct_runtime_adapters() -> list[dict[str, Any]]:
        return runtime_registry.adapters()

    @app.get("/api/direct-runtimes/models")
    def direct_runtime_models(adapter_id: str | None = None) -> list[dict[str, Any]]:
        return runtime_registry.list_models(adapter_id)

    @app.post("/api/direct-runtimes/sessions/load")
    def direct_runtime_load(request: DirectRuntimeLoadRequest) -> dict[str, Any]:
        try:
            return runtime_registry.load(request.adapter_id, request.model_ref, request.config)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=safe_error(exc)) from exc

    @app.post("/api/direct-runtimes/sessions/{session_id}/unload")
    def direct_runtime_unload(session_id: str) -> dict[str, Any]:
        try:
            return runtime_registry.unload(session_id)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=404, detail=safe_error(exc)) from exc

    @app.get("/api/benchmarks/profiles")
    def benchmark_profiles() -> list[dict[str, Any]]:
        return benchmark_engine.list_profiles()

    @app.post("/api/benchmarks/profiles")
    def save_benchmark_profile(request: BenchmarkProfileSaveRequest) -> dict[str, Any]:
        try:
            return benchmark_engine.save_profile(request.profile)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=safe_error(exc)) from exc

    @app.post("/api/benchmarks/run")
    def run_benchmark(request: BenchmarkRunRequest) -> dict[str, Any]:
        try:
            if request.profile:
                return benchmark_engine.run_profile(request.profile, request.session_id, request.branch)
            if request.profile_id:
                return benchmark_engine.run_profile_id(request.profile_id, request.session_id, request.branch)
            raise ValueError("profile_id or profile is required")
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=safe_error(exc)) from exc

    @app.get("/api/benchmarks/runs")
    def benchmark_runs(session_id: str = "default", limit: int = Query(default=100, ge=1, le=500)) -> list[dict[str, Any]]:
        return core.db.list_benchmark_runs(session_id, limit)

    @app.get("/api/benchmarks/runs/{run_id}")
    def benchmark_run(run_id: str) -> dict[str, Any]:
        run = core.db.get_benchmark_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="benchmark run not found")
        return run

    @app.get("/api/benchmarks/runs/{run_id}/report")
    def benchmark_run_report(run_id: str, format: str = "json") -> PlainTextResponse:
        run = core.db.get_benchmark_run(run_id)
        if not run:
            raise HTTPException(status_code=404, detail="benchmark run not found")
        try:
            text = report_as_text(run.get("report") or {}, format)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=safe_error(exc)) from exc
        media_type = "application/json" if format == "json" else ("text/csv" if format == "csv" else "text/markdown")
        return PlainTextResponse(text, media_type=media_type)

    @app.get("/api/chat")
    def chat(session_id: str = "default", limit: int = Query(default=100, ge=1, le=500)) -> list[dict[str, Any]]:
        return core.list_chat(session_id, limit)

    @app.post("/api/chat/{message_id}/route")
    def route_chat(message_id: str, request: ChatRouteRequest, session_id: str = "default") -> dict[str, Any]:
        message = core.get_chat_message(message_id)
        if not message:
            raise HTTPException(status_code=404, detail="chat message not found")
        try:
            receipt = route_outbound(
                request.target_type,
                message["content"],
                request.config,
                request.packet_type,
                {"message_id": message_id, "session_id": session_id, "branch": message["branch"]},
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=safe_error(exc)) from exc
        core.record_chat_message(
            session_id=session_id,
            origin="outbound",
            role="system",
            content=f"Outbound receipt: {receipt['status']} via {receipt['target_type']}",
            fmt="json",
            branch=message["branch"],
            workflow_id=message.get("workflow_id"),
            badges={"origin": "Outbound", "branch": message["branch"], "format": "json"},
            metadata={"receipt": receipt},
        )
        return receipt

    @app.post("/api/chat/{message_id}/promote")
    def promote_chat(message_id: str, request: ChatPromoteRequest, session_id: str = "default") -> dict[str, Any]:
        try:
            return core.promote_chat(session_id, message_id, request.branch, request.subject, request.attribute, request.tags)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=safe_error(exc)) from exc

    @app.get("/api/ledger")
    def ledger(session_id: str = "default", limit: int = Query(default=100, ge=1, le=500)) -> list[dict[str, Any]]:
        return core.ledger(session_id, limit)

    @app.get("/api/ledger/{entry_id}")
    def ledger_entry(entry_id: str, session_id: str = "default") -> dict[str, Any]:
        entry = core.db.get_ledger_entry(session_id, entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="ledger entry not found")
        return entry

    @app.get("/api/metrics")
    def metrics(session_id: str = "default", limit: int = Query(default=100, ge=1, le=500)) -> list[dict[str, Any]]:
        return core.metrics(session_id, limit)

    @app.get("/api/quality")
    def quality(
        session_id: str = "default",
        target_type: str | None = None,
        target_id: str | None = None,
        limit: int = Query(default=100, ge=1, le=500),
    ) -> list[dict[str, Any]]:
        return core.db.list_quality_evaluations(session_id, target_type, target_id, limit)

    @app.get("/api/provenance")
    def provenance(session_id: str = "default", branch: str = "corelm", subject: str = "project", attribute: str = "name") -> dict[str, Any]:
        return core.provenance(session_id, branch, subject, attribute)

    @app.get("/api/replay")
    def replay(session_id: str = "default") -> dict[str, Any]:
        return core.replay(session_id)

    @app.get("/api/replay/snapshots")
    def replay_snapshots(session_id: str = "default", limit: int = Query(default=50, ge=1, le=200)) -> list[dict[str, Any]]:
        return core.db.list_replay_snapshots(session_id, limit)

    @app.get("/api/settings")
    def settings() -> dict[str, Any]:
        return core.db.get_settings()

    @app.post("/api/settings")
    def update_settings(request: SettingsUpdateRequest) -> dict[str, Any]:
        return core.db.update_settings(request.settings)

    @app.get("/api/workflows")
    def list_workflows() -> list[dict[str, Any]]:
        return core.db.list_workflows()

    @app.get("/api/workflows/runs")
    def list_workflow_runs(session_id: str = "default", limit: int = Query(default=50, ge=1, le=200)) -> list[dict[str, Any]]:
        return core.db.list_workflow_runs(session_id, limit)

    @app.post("/api/workflows")
    def save_workflow(request: WorkflowSaveRequest) -> dict[str, Any]:
        workflow = request.workflow
        if "id" not in workflow:
            workflow["id"] = "workflow-" + workflow.get("name", "untitled").lower().replace(" ", "-")
        core.db.upsert_workflow(workflow)
        return core.db.get_workflow(workflow["id"]) or {}

    @app.get("/api/workflows/{workflow_id}")
    def get_workflow(workflow_id: str) -> dict[str, Any]:
        workflow = core.db.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="workflow not found")
        return workflow

    @app.post("/api/workflows/{workflow_id}/run")
    def run_workflow(workflow_id: str, request: WorkflowRunRequest) -> dict[str, Any]:
        workflow = request.workflow or core.db.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="workflow not found")
        try:
            return engine.run(workflow, request.session_id, request.branch, request.inputs)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=safe_error(exc)) from exc

    @app.post("/api/workflows/{workflow_id}/clone")
    def clone_workflow(workflow_id: str) -> dict[str, Any]:
        workflow = core.db.get_workflow(workflow_id)
        if not workflow:
            raise HTTPException(status_code=404, detail="workflow not found")
        workflow = dict(workflow)
        workflow["id"] = f"{workflow_id}-clone"
        workflow["name"] = f"{workflow.get('name', workflow_id)} Clone"
        core.db.upsert_workflow(workflow)
        return workflow

    @app.post("/api/outbound/route")
    def outbound_route(request: OutboundRouteRequest) -> dict[str, Any]:
        try:
            return route_outbound(request.target_type, request.content, request.config, request.packet_type, request.metadata)
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=400, detail=safe_error(exc)) from exc

    @app.get("/api/outbound/templates")
    def outbound_templates() -> list[str]:
        return [
            "markdown_brief",
            "engineering_task_packet",
            "json_job_spec",
            "code_review_packet",
            "bug_report_packet",
            "repo_handoff_packet",
            "implementation_packet",
            "prompt_packet",
            "prompt_for_coding_agent",
        ]

    return app


app = create_app()
