from __future__ import annotations

from services.core_service.corelm_studio.compression import chunk_text, preprocess_payload
from fastapi.testclient import TestClient

from services.core_service.corelm_studio.app import create_app


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
