from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .security import sanitize_obj


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def dumps_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def loads_json(value: str | None, fallback: Any = None) -> Any:
    if not value:
        return fallback
    return json.loads(value)


class StudioDB:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self.init_schema()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def init_schema(self) -> None:
        with self._lock:
            self._conn.executescript(
                """
                PRAGMA journal_mode = WAL;
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    seed INTEGER NOT NULL DEFAULT 0,
                    current_branch TEXT NOT NULL DEFAULT 'corelm',
                    core_state_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS workflows (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    workflow_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS workflow_nodes (
                    workflow_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    node_type TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    position_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (workflow_id, node_id),
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS workflow_edges (
                    workflow_id TEXT NOT NULL,
                    edge_id TEXT NOT NULL,
                    source_node_id TEXT NOT NULL,
                    target_node_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (workflow_id, edge_id),
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS connectors (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    direction TEXT NOT NULL,
                    type TEXT NOT NULL,
                    config_json TEXT NOT NULL,
                    secret_refs_json TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    origin TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    format TEXT NOT NULL,
                    branch TEXT NOT NULL,
                    workflow_id TEXT,
                    provenance_id TEXT,
                    ledger_entry_id TEXT,
                    badges_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS ledger_entries (
                    entry_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    event_id TEXT NOT NULL,
                    branch TEXT NOT NULL,
                    raw_text TEXT NOT NULL,
                    corelm_json TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (session_id, entry_id),
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS replay_snapshots (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    digest TEXT NOT NULL,
                    ok INTEGER NOT NULL,
                    snapshot_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS metrics (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    event_id TEXT,
                    metric_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS workflow_runs (
                    id TEXT PRIMARY KEY,
                    workflow_id TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    trace_json TEXT NOT NULL,
                    outputs_json TEXT NOT NULL,
                    final_output TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value_json TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS secrets_metadata (
                    id TEXT PRIMARY KEY,
                    connector_id TEXT NOT NULL,
                    secret_name TEXT NOT NULL,
                    storage_backend TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (connector_id) REFERENCES connectors(id) ON DELETE CASCADE
                );
                """
            )
            self._conn.commit()

    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            cursor = self._conn.execute(sql, tuple(params))
            self._conn.commit()
            return cursor

    def query_one(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Row | None:
        with self._lock:
            return self._conn.execute(sql, tuple(params)).fetchone()

    def query_all(self, sql: str, params: Iterable[Any] = ()) -> list[sqlite3.Row]:
        with self._lock:
            return list(self._conn.execute(sql, tuple(params)).fetchall())

    def upsert_session(self, session_id: str, name: str, seed: int, current_branch: str, state: dict[str, Any]) -> None:
        now = utc_now()
        existing = self.query_one("SELECT id FROM sessions WHERE id = ?", (session_id,))
        if existing:
            self.execute(
                """
                UPDATE sessions
                SET name = ?, seed = ?, current_branch = ?, core_state_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (name, seed, current_branch, dumps_json(state), now, session_id),
            )
            return
        self.execute(
            """
            INSERT INTO sessions (id, name, seed, current_branch, core_state_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (session_id, name, seed, current_branch, dumps_json(state), now, now),
        )

    def list_sessions(self) -> list[dict[str, Any]]:
        rows = self.query_all("SELECT * FROM sessions ORDER BY updated_at DESC")
        return [dict(row) | {"core_state": loads_json(row["core_state_json"], {})} for row in rows]

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        row = self.query_one("SELECT * FROM sessions WHERE id = ?", (session_id,))
        if not row:
            return None
        payload = dict(row)
        payload["core_state"] = loads_json(row["core_state_json"], {})
        return payload

    def upsert_workflow(self, workflow: dict[str, Any]) -> None:
        workflow = sanitize_obj(workflow)
        now = utc_now()
        workflow_id = workflow["id"]
        existing = self.query_one("SELECT id FROM workflows WHERE id = ?", (workflow_id,))
        if existing:
            self.execute(
                "UPDATE workflows SET name = ?, description = ?, workflow_json = ?, updated_at = ? WHERE id = ?",
                (
                    workflow.get("name", workflow_id),
                    workflow.get("description", ""),
                    dumps_json(workflow),
                    now,
                    workflow_id,
                ),
            )
        else:
            self.execute(
                """
                INSERT INTO workflows (id, name, description, workflow_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    workflow_id,
                    workflow.get("name", workflow_id),
                    workflow.get("description", ""),
                    dumps_json(workflow),
                    now,
                    now,
                ),
            )
        self.execute("DELETE FROM workflow_nodes WHERE workflow_id = ?", (workflow_id,))
        self.execute("DELETE FROM workflow_edges WHERE workflow_id = ?", (workflow_id,))
        for node in workflow.get("nodes", []):
            self.execute(
                """
                INSERT INTO workflow_nodes
                (workflow_id, node_id, node_type, config_json, position_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    workflow_id,
                    node["id"],
                    node["type"],
                    dumps_json(sanitize_obj(node.get("config", {}))),
                    dumps_json(node.get("position", {})),
                    now,
                    now,
                ),
            )
        for edge in workflow.get("edges", []):
            self.execute(
                """
                INSERT INTO workflow_edges
                (workflow_id, edge_id, source_node_id, target_node_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    workflow_id,
                    edge.get("id") or f"{edge['source']}->{edge['target']}",
                    edge["source"],
                    edge["target"],
                    now,
                    now,
                ),
            )

    def list_workflows(self) -> list[dict[str, Any]]:
        rows = self.query_all("SELECT workflow_json FROM workflows ORDER BY updated_at DESC")
        return [loads_json(row["workflow_json"], {}) for row in rows]

    def get_workflow(self, workflow_id: str) -> dict[str, Any] | None:
        row = self.query_one("SELECT workflow_json FROM workflows WHERE id = ?", (workflow_id,))
        return loads_json(row["workflow_json"], None) if row else None

    def upsert_connector(self, connector: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        connector_id = connector["id"]
        safe_config = sanitize_obj(connector.get("config", {}))
        secret_refs = [str(item) for item in connector.get("secret_refs", [])]
        existing = self.query_one("SELECT id FROM connectors WHERE id = ?", (connector_id,))
        params = (
            connector_id,
            connector.get("name", connector_id),
            connector.get("direction", "inbound"),
            connector.get("type", "manual_text"),
            dumps_json(safe_config),
            dumps_json(secret_refs),
            1 if connector.get("enabled", True) else 0,
        )
        if existing:
            self.execute(
                """
                UPDATE connectors
                SET name = ?, direction = ?, type = ?, config_json = ?, secret_refs_json = ?,
                    enabled = ?, updated_at = ?
                WHERE id = ?
                """,
                (params[1], params[2], params[3], params[4], params[5], params[6], now, connector_id),
            )
        else:
            self.execute(
                """
                INSERT INTO connectors
                (id, name, direction, type, config_json, secret_refs_json, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (*params, now, now),
            )
        self.execute("DELETE FROM secrets_metadata WHERE connector_id = ?", (connector_id,))
        for secret_name in secret_refs:
            secret_id = f"{connector_id}:{secret_name}"
            self.execute(
                """
                INSERT OR REPLACE INTO secrets_metadata
                (id, connector_id, secret_name, storage_backend, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (secret_id, connector_id, secret_name, connector.get("secret_backend", "environment"), now, now),
            )
        return self.get_connector(connector_id) or {}

    def get_connector(self, connector_id: str) -> dict[str, Any] | None:
        row = self.query_one("SELECT * FROM connectors WHERE id = ?", (connector_id,))
        if not row:
            return None
        payload = dict(row)
        payload["config"] = loads_json(row["config_json"], {})
        payload["secret_refs"] = loads_json(row["secret_refs_json"], [])
        payload["enabled"] = bool(row["enabled"])
        secrets = self.query_all("SELECT secret_name, storage_backend FROM secrets_metadata WHERE connector_id = ?", (connector_id,))
        payload["secrets_metadata"] = [dict(item) for item in secrets]
        return payload

    def list_connectors(self) -> list[dict[str, Any]]:
        rows = self.query_all("SELECT id FROM connectors ORDER BY updated_at DESC")
        return [connector for row in rows if (connector := self.get_connector(row["id"]))]

    def delete_connector(self, connector_id: str) -> bool:
        existing = self.query_one("SELECT id FROM connectors WHERE id = ?", (connector_id,))
        if not existing:
            return False
        self.execute("DELETE FROM secrets_metadata WHERE connector_id = ?", (connector_id,))
        self.execute("DELETE FROM connectors WHERE id = ?", (connector_id,))
        return True

    def list_replay_snapshots(self, session_id: str, limit: int = 50) -> list[dict[str, Any]]:
        rows = self.query_all(
            "SELECT * FROM replay_snapshots WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
            (session_id, limit),
        )
        output = []
        for row in reversed(rows):
            payload = dict(row)
            payload["ok"] = bool(row["ok"])
            payload["snapshot"] = loads_json(row["snapshot_json"], {})
            output.append(payload)
        return output

    def get_ledger_entry(self, session_id: str, entry_id: str) -> dict[str, Any] | None:
        row = self.query_one(
            "SELECT * FROM ledger_entries WHERE session_id = ? AND entry_id = ?",
            (session_id, entry_id),
        )
        if not row:
            return None
        payload = dict(row)
        payload["corelm"] = loads_json(row["corelm_json"], {})
        payload["metadata"] = loads_json(row["metadata_json"], {})
        return payload

    def record_workflow_run(
        self,
        workflow_id: str,
        session_id: str,
        status: str,
        trace: list[dict[str, Any]],
        outputs: dict[str, Any],
        final_output: str,
    ) -> dict[str, Any]:
        now = utc_now()
        run_id = f"run-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}"
        self.execute(
            """
            INSERT INTO workflow_runs
            (id, workflow_id, session_id, status, trace_json, outputs_json, final_output, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                workflow_id,
                session_id,
                status,
                dumps_json(sanitize_obj(trace)),
                dumps_json(sanitize_obj(outputs)),
                sanitize_obj(final_output),
                now,
            ),
        )
        return self.get_workflow_run(run_id) or {}

    def get_workflow_run(self, run_id: str) -> dict[str, Any] | None:
        row = self.query_one("SELECT * FROM workflow_runs WHERE id = ?", (run_id,))
        if not row:
            return None
        payload = dict(row)
        payload["trace"] = loads_json(row["trace_json"], [])
        payload["outputs"] = loads_json(row["outputs_json"], {})
        return payload

    def list_workflow_runs(self, session_id: str = "default", limit: int = 50) -> list[dict[str, Any]]:
        rows = self.query_all(
            "SELECT id FROM workflow_runs WHERE session_id = ? ORDER BY created_at DESC LIMIT ?",
            (session_id, limit),
        )
        runs = [run for row in rows if (run := self.get_workflow_run(row["id"]))]
        return list(reversed(runs))

    def get_settings(self) -> dict[str, Any]:
        rows = self.query_all("SELECT key, value_json FROM settings ORDER BY key")
        return {row["key"]: loads_json(row["value_json"], None) for row in rows}

    def update_settings(self, patch: dict[str, Any]) -> dict[str, Any]:
        now = utc_now()
        for key, value in sanitize_obj(patch).items():
            self.execute(
                """
                INSERT INTO settings (key, value_json, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, updated_at = excluded.updated_at
                """,
                (str(key), dumps_json(value), now),
            )
        return self.get_settings()
