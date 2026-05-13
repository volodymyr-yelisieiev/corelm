from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

from corelm.product import CoreLMProduct
from corelm.schema import Event

from .compression import preprocess_payload
from .db import StudioDB, dumps_json, loads_json, utc_now
from .formatters import format_payload
from .metrics import flatten_provider_metrics
from .quality import evaluate_quality
from .security import sanitize_obj, sanitize_text


def default_data_dir() -> Path:
    return Path(os.getenv("CORELM_STUDIO_DATA_DIR", ".corelm_studio")).expanduser()


class StudioCore:
    def __init__(self, db_path: str | Path | None = None) -> None:
        data_dir = default_data_dir()
        self.db = StudioDB(db_path or data_dir / "corelm_studio.sqlite")
        self._products: dict[str, CoreLMProduct] = {}
        self.ensure_session("default", "Default Core LM Studio Session", 0, "corelm")
        self.ensure_seed_data()

    def close(self) -> None:
        self.db.close()

    def ensure_session(self, session_id: str, name: str, seed: int, branch: str) -> dict[str, Any]:
        existing = self.db.get_session(session_id)
        if existing:
            return existing
        product = CoreLMProduct(seed=seed)
        self._products[session_id] = product
        self.db.upsert_session(session_id, name, seed, branch, sanitize_obj(product.export_state()))
        return self.db.get_session(session_id) or {}

    def create_session(self, name: str, seed: int = 0, current_branch: str = "corelm", session_id: str | None = None) -> dict[str, Any]:
        session_id = session_id or f"session-{uuid.uuid4().hex[:10]}"
        return self.ensure_session(session_id, name, seed, current_branch)

    def list_sessions(self) -> list[dict[str, Any]]:
        return self.db.list_sessions()

    def _product_from_state(self, state: dict[str, Any]) -> CoreLMProduct:
        product = CoreLMProduct(seed=int(state.get("seed", 0)))
        product.reset(seed=int(state.get("seed", 0)))
        for raw_event in state.get("events", []):
            event = Event(**raw_event)
            product.kernel.step(event)
            product.events.append(event)
            product._counter = max(product._counter, int(event.timestamp))
        return product

    def product_for(self, session_id: str) -> CoreLMProduct:
        if session_id in self._products:
            return self._products[session_id]
        session = self.db.get_session(session_id)
        if not session:
            session = self.ensure_session(session_id, f"Session {session_id}", 0, "corelm")
        product = self._product_from_state(session["core_state"])
        self._products[session_id] = product
        return product

    def _save_product(self, session_id: str, branch: str) -> None:
        session = self.db.get_session(session_id) or {}
        product = self.product_for(session_id)
        self.db.upsert_session(
            session_id,
            session.get("name") or f"Session {session_id}",
            int(product.seed),
            branch,
            sanitize_obj(product.export_state()),
        )

    def ensure_seed_data(self) -> None:
        if self.db.get_workflow("demo-canonical-flow"):
            return
        workflow = {
            "id": "demo-canonical-flow",
            "name": "Canonical Core LM Flow",
            "description": "Manual text through cleaning, canonicalization, Core LM, chat, and programming-agent packet output.",
            "schedule": {"enabled": False, "cron": ""},
            "nodes": [
                {"id": "n1", "type": "manual_text_input", "position": {"x": 40, "y": 80}, "config": {"text": "project.name = Core LM Studio"}},
                {"id": "n2", "type": "clean_text", "position": {"x": 280, "y": 80}, "config": {}},
                {"id": "n3", "type": "canonicalize", "position": {"x": 520, "y": 80}, "config": {}},
                {"id": "n4", "type": "core_lm", "position": {"x": 760, "y": 80}, "config": {"format": "markdown"}},
                {"id": "n5", "type": "chat", "position": {"x": 1000, "y": 80}, "config": {}},
                {"id": "n6", "type": "outbound_prompt", "position": {"x": 1240, "y": 80}, "config": {"target_type": "programming_agent_packet"}},
            ],
            "edges": [
                {"id": "e1", "source": "n1", "target": "n2"},
                {"id": "e2", "source": "n2", "target": "n3"},
                {"id": "e3", "source": "n3", "target": "n4"},
                {"id": "e4", "source": "n4", "target": "n5"},
                {"id": "e5", "source": "n5", "target": "n6"},
            ],
        }
        self.db.upsert_workflow(workflow)

    def state_summary(self, session_id: str = "default") -> dict[str, Any]:
        product = self.product_for(session_id)
        replay = product.replay_verify()
        stats = product.kernel.stats()
        latest_ledger = product.kernel.ledger[-1].to_dict() if product.kernel.ledger else None
        branches = sorted(product.kernel.branch_slots.keys()) or ["corelm"]
        return {
            "session_id": session_id,
            "digest": product.kernel.digest(),
            "stats": stats,
            "replay": replay,
            "latest_ledger": latest_ledger,
            "branches": branches,
            "health": "healthy" if replay["ok"] and stats["invariant_violations"] == 0 else "attention",
        }

    def _metric_packet(
        self,
        product: CoreLMProduct,
        event_id: str,
        compression_ratio: float,
        previous_norm: float,
        source_input_norm: float,
        provider_metrics: dict[str, Any] | None = None,
        quality_eval: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        stats = product.kernel.stats()
        latest = product.kernel.ledger[-1]
        replay = product.replay_verify()
        ledger_count = max(1, int(stats.get("ledger_entries", 1)))
        violations = int(stats.get("invariant_violations", 0))
        state_norm = float(latest.current_norm)
        drift = abs(state_norm - previous_norm)
        stability_proxy = 1.0 / (1.0 + abs(float(latest.energy_drift)))
        quality_score = None
        if quality_eval:
            quality_score = quality_eval.get("summary_score")
        return {
            "event_id": event_id,
            "state_norm": state_norm,
            "drift": drift,
            "source_input_norm": source_input_norm,
            "invariant_violation_rate": violations / ledger_count,
            "determinism_score": 1.0 if replay["ok"] else 0.0,
            "replay_consistency_score": 1.0 if replay["ok"] else 0.0,
            "quality_score": quality_score,
            "quality_summary_score": quality_score,
            "quality_eval_version": quality_eval.get("version") if quality_eval else None,
            "quality_eval": quality_eval,
            "compression_ratio_proxy": compression_ratio,
            "energy": float(latest.energy),
            "stability_proxy": stability_proxy,
            "csi": float(latest.csi),
        } | flatten_provider_metrics(provider_metrics)

    def record_chat_message(
        self,
        session_id: str,
        origin: str,
        role: str,
        content: str,
        fmt: str,
        branch: str,
        workflow_id: str | None = None,
        provenance_id: str | None = None,
        ledger_entry_id: str | None = None,
        badges: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        message_id = f"msg-{uuid.uuid4().hex[:12]}"
        created_at = utc_now()
        self.db.execute(
            """
            INSERT INTO chat_messages
            (id, session_id, origin, role, content, format, branch, workflow_id, provenance_id,
             ledger_entry_id, badges_json, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                session_id,
                origin,
                role,
                sanitize_text(content),
                fmt,
                branch,
                workflow_id,
                provenance_id,
                ledger_entry_id,
                dumps_json(sanitize_obj(badges or {})),
                dumps_json(sanitize_obj(metadata or {})),
                created_at,
            ),
        )
        return self.get_chat_message(message_id) or {}

    def get_chat_message(self, message_id: str) -> dict[str, Any] | None:
        row = self.db.query_one("SELECT * FROM chat_messages WHERE id = ?", (message_id,))
        if not row:
            return None
        payload = dict(row)
        payload["badges"] = loads_json(row["badges_json"], {})
        payload["metadata"] = loads_json(row["metadata_json"], {})
        return payload

    def list_chat(self, session_id: str = "default", limit: int = 100) -> list[dict[str, Any]]:
        rows = self.db.query_all(
            "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
            (session_id, limit),
        )
        messages = []
        for row in reversed(rows):
            payload = dict(row)
            payload["badges"] = loads_json(row["badges_json"], {})
            payload["metadata"] = loads_json(row["metadata_json"], {})
            messages.append(payload)
        return messages

    def ingest(
        self,
        session_id: str,
        branch: str,
        text: str,
        source: dict[str, Any] | None = None,
        workflow_id: str | None = None,
        fmt: str = "markdown",
        compression: dict[str, Any] | None = None,
        annotations: list[dict[str, Any]] | None = None,
        evaluator_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        product = self.product_for(session_id)
        previous_norm = float(product.kernel.ledger[-1].current_norm) if product.kernel.ledger else 0.0
        preprocessed = preprocess_payload(text, branch, compression, annotations)
        source_meta = sanitize_obj(source or {})
        provider_metrics = source_meta.get("provider_metrics") if isinstance(source_meta.get("provider_metrics"), dict) else None
        inherited_eval_config = source_meta.get("evaluator_config", {})
        if not isinstance(inherited_eval_config, dict):
            inherited_eval_config = {}
        quality_eval = evaluate_quality(
            preprocessed.canonical_text,
            evaluator_config or inherited_eval_config,
            preprocessed.to_dict(),
        )
        meta = {
            "source": source_meta,
            "compression": preprocessed.to_dict() | {"raw_text": "[available-before-sanitized-commit]"},
            "provider_metrics": provider_metrics,
            "quality_eval": quality_eval,
            "workflow_id": workflow_id,
        }
        result = product.ingest_text(
            branch=branch,
            text=preprocessed.canonical_text,
            annotations=preprocessed.annotations,
            event_type="message",
            meta=meta,
        )
        latest = product.kernel.ledger[-1]
        metric = self._metric_packet(
            product,
            result["event_id"],
            preprocessed.compression_ratio,
            previous_norm,
            float(len(preprocessed.canonical_text.split())),
            provider_metrics,
            quality_eval,
        )
        replay = product.replay_verify()
        snapshot_id = f"replay-{uuid.uuid4().hex[:12]}"
        created_at = utc_now()
        self.db.execute(
            """
            INSERT OR REPLACE INTO ledger_entries
            (entry_id, session_id, event_id, branch, raw_text, corelm_json, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                latest.entry_id,
                session_id,
                latest.event_id,
                latest.branch,
                sanitize_text(preprocessed.canonical_text),
                dumps_json(sanitize_obj(latest.to_dict())),
                dumps_json(sanitize_obj(meta)),
                created_at,
            ),
        )
        self.db.execute(
            "INSERT INTO metrics (id, session_id, event_id, metric_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (f"metric-{uuid.uuid4().hex[:12]}", session_id, result["event_id"], dumps_json(metric), created_at),
        )
        quality_record = self.db.record_quality_evaluation(session_id, "ledger_entry", latest.entry_id, quality_eval, result["event_id"])
        self.db.execute(
            """
            INSERT INTO replay_snapshots (id, session_id, digest, ok, snapshot_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (snapshot_id, session_id, replay["expected_digest"], 1 if replay["ok"] else 0, dumps_json(sanitize_obj(replay)), created_at),
        )
        self._save_product(session_id, branch)
        rendered = format_payload(
            preprocessed.canonical_text,
            fmt,
            {
                "session_id": session_id,
                "branch": branch,
                "event_id": result["event_id"],
                "ledger_entry_id": latest.entry_id,
                "digest": product.kernel.digest(),
                "admitted_claims": result["result"]["admitted_claims"],
                "deduped_claims": result["result"]["deduped_claims"],
            },
        )
        chat_metadata = {
            "metrics": metric,
            "source": source_meta,
            "compression": preprocessed.to_dict(),
            "provider_metrics": provider_metrics,
            "quality_eval": quality_eval,
            "ledger_quality_evaluation_id": quality_record.get("id"),
        }
        chat = self.record_chat_message(
            session_id=session_id,
            origin="core_lm",
            role="assistant",
            content=rendered,
            fmt=fmt,
            branch=branch,
            workflow_id=workflow_id,
            provenance_id=result["event_id"],
            ledger_entry_id=latest.entry_id,
            badges={"origin": "Core LM", "branch": branch, "format": fmt, "workflow": workflow_id},
            metadata=chat_metadata,
        )
        chat_quality_record = self.db.record_quality_evaluation(session_id, "chat_message", chat["id"], quality_eval, result["event_id"])
        chat_metadata["quality_evaluation_id"] = chat_quality_record.get("id")
        self.db.execute(
            "UPDATE chat_messages SET metadata_json = ? WHERE id = ?",
            (dumps_json(sanitize_obj(chat_metadata)), chat["id"]),
        )
        chat = self.get_chat_message(chat["id"]) or chat
        return {
            "status": "ok",
            "session_id": session_id,
            "branch": branch,
            "event_id": result["event_id"],
            "ledger_entry": sanitize_obj(latest.to_dict()),
            "metrics": metric,
            "quality_eval": quality_eval,
            "replay": replay,
            "chat_message": chat,
            "digest": product.kernel.digest(),
            "core_result": result,
            "compression": preprocessed.to_dict(),
        }

    def ledger(self, session_id: str = "default", limit: int = 100) -> list[dict[str, Any]]:
        rows = self.db.query_all(
            "SELECT * FROM ledger_entries WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
            (session_id, limit),
        )
        entries = []
        for row in reversed(rows):
            payload = dict(row)
            payload["corelm"] = loads_json(row["corelm_json"], {})
            payload["metadata"] = loads_json(row["metadata_json"], {})
            entries.append(payload)
        return entries

    def metrics(self, session_id: str = "default", limit: int = 100) -> list[dict[str, Any]]:
        rows = self.db.query_all(
            "SELECT * FROM metrics WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
            (session_id, limit),
        )
        output = []
        for row in reversed(rows):
            payload = dict(row)
            payload["metric"] = loads_json(row["metric_json"], {})
            output.append(payload)
        return output

    def compression_packet(self, session_id: str, target_type: str, target_id: str) -> dict[str, Any]:
        target_type = target_type.lower().replace("-", "_")
        packets: list[dict[str, Any]] = []

        def add(packet: Any, label: str) -> None:
            if isinstance(packet, dict) and packet.get("canonical_text") is not None:
                packets.append({"label": label, "packet": sanitize_obj(packet)})

        def collect(value: Any, label: str) -> None:
            if isinstance(value, dict):
                if value.get("canonical_text") is not None and value.get("digest") is not None:
                    add(value, label)
                    return
                for key, item in value.items():
                    collect(item, f"{label}.{key}")
            elif isinstance(value, list):
                for index, item in enumerate(value):
                    collect(item, f"{label}[{index}]")

        if target_type in {"ledger", "ledger_entry"}:
            entry = self.db.get_ledger_entry(session_id, target_id)
            if entry:
                add(entry.get("metadata", {}).get("compression"), f"ledger:{target_id}")
        elif target_type in {"chat", "chat_message", "message"}:
            message = self.get_chat_message(target_id)
            if message and message.get("session_id") == session_id:
                add(message.get("metadata", {}).get("compression"), f"chat:{target_id}")
        elif target_type in {"workflow", "workflow_run", "run"}:
            run = self.db.get_workflow_run(target_id)
            if run and run.get("session_id") == session_id:
                collect(run.get("trace", []), f"workflow:{target_id}.trace")
                collect(run.get("outputs", {}), f"workflow:{target_id}.outputs")
        else:
            raise ValueError(f"Unsupported compression target_type: {target_type}")

        return {"session_id": session_id, "target_type": target_type, "target_id": target_id, "packets": packets}

    def replay(self, session_id: str = "default") -> dict[str, Any]:
        product = self.product_for(session_id)
        return sanitize_obj(product.replay_verify() | {"snapshot": product.export_state()})

    def provenance(self, session_id: str, branch: str, subject: str, attribute: str) -> dict[str, Any]:
        product = self.product_for(session_id)
        return {
            "branch": branch,
            "subject": subject,
            "attribute": attribute,
            "value": product.get_value(branch, subject, attribute),
            "provenance": sanitize_text(product.get_provenance(branch, subject, attribute)),
            "supersession": sanitize_text(product.get_supersession(branch, subject, attribute)),
        }

    def promote_chat(self, session_id: str, message_id: str, branch: str, subject: str, attribute: str, tags: list[str]) -> dict[str, Any]:
        message = self.get_chat_message(message_id)
        if not message:
            raise ValueError(f"Unknown chat message: {message_id}")
        return self.ingest(
            session_id=session_id,
            branch=branch,
            text=message["content"],
            source={"source_id": message_id, "source_type": "chat_promote", "trust_level": "medium"},
            annotations=[
                {
                    "branch": branch,
                    "subject": subject,
                    "attribute": attribute,
                    "value": message["content"][:500],
                    "claim_type": "note",
                    "tags": tags,
                }
            ],
            fmt=message["format"] or "markdown",
            compression={"allow_raw_commit": False},
        )
