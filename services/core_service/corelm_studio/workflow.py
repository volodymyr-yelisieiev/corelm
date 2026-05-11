from __future__ import annotations

import copy
import uuid
from typing import Any

from .compression import preprocess_payload
from .connectors import run_inbound_connector
from .formatters import format_payload
from .outbound import route_outbound


def _incoming(edges: list[dict[str, Any]], node_id: str) -> list[str]:
    return [edge["source"] for edge in edges if edge["target"] == node_id]


def _topological_nodes(workflow: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = list(workflow.get("nodes", []))
    edges = list(workflow.get("edges", []))
    by_id = {node["id"]: node for node in nodes}
    indegree = {node["id"]: 0 for node in nodes}
    outgoing: dict[str, list[str]] = {node["id"]: [] for node in nodes}
    for edge in edges:
        if edge["source"] in by_id and edge["target"] in by_id:
            indegree[edge["target"]] += 1
            outgoing.setdefault(edge["source"], []).append(edge["target"])
    ready = [node_id for node_id, count in indegree.items() if count == 0]
    ordered: list[dict[str, Any]] = []
    while ready:
        node_id = ready.pop(0)
        ordered.append(by_id[node_id])
        for target in outgoing.get(node_id, []):
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
    if len(ordered) != len(nodes):
        return nodes
    return ordered


class WorkflowEngine:
    def __init__(self, core: Any) -> None:
        self.core = core

    def run(self, workflow: dict[str, Any], session_id: str, branch: str, inputs: dict[str, Any] | None = None) -> dict[str, Any]:
        workflow = copy.deepcopy(workflow)
        workflow_id = workflow.get("id") or f"workflow-{uuid.uuid4().hex[:8]}"
        workflow["id"] = workflow_id
        inputs = inputs or {}
        outputs: dict[str, dict[str, Any]] = {}
        trace: list[dict[str, Any]] = []
        edges = workflow.get("edges", [])
        last_value = str(inputs.get("text") or "")
        for node in _topological_nodes(workflow):
            node_id = node["id"]
            node_type = str(node["type"]).lower()
            config = dict(node.get("config", {}))
            parent_values = [outputs[parent]["value"] for parent in _incoming(edges, node_id) if parent in outputs]
            current = parent_values[-1] if parent_values else last_value
            event: dict[str, Any] = {"node_id": node_id, "type": node_type, "status": "ok"}
            try:
                if node_type in {
                    "manual_text_input",
                    "openai_compatible_llm",
                    "ollama_local_model",
                    "file_input",
                    "folder_watcher",
                    "generic_web_api_fetch",
                    "clipboard_input",
                    "generic_rest_input",
                    "shell_cli_capture",
                }:
                    connector_type = "manual_text" if node_type == "manual_text_input" else node_type
                    connector_config = config | {"text": inputs.get("text", config.get("text", ""))}
                    result = run_inbound_connector(connector_type, connector_config, branch=branch)
                    value = result.raw_payload
                    event["metadata"] = result.metadata
                    outputs[node_id] = {"value": value, "metadata": result.metadata}
                elif node_type in {
                    "clean_text",
                    "chunking",
                    "dedupe_text",
                    "summarization",
                    "schema_extraction",
                    "key_value_extraction",
                    "canonicalize",
                    "hash_compress",
                    "state_digest_generation",
                    "contradiction_detection",
                }:
                    step_map = {
                        "clean_text": ["clean"],
                        "chunking": ["chunking"],
                        "dedupe_text": ["dedupe"],
                        "summarization": ["summarize"],
                        "schema_extraction": ["schema_extract"],
                        "key_value_extraction": ["key_value_extract"],
                        "canonicalize": ["canonicalize"],
                        "hash_compress": ["hash_compress"],
                        "state_digest_generation": ["hash_compress"],
                        "contradiction_detection": ["contradiction_tag"],
                    }
                    defaults = {"hash_only": True} if node_type in {"hash_compress", "state_digest_generation"} else {}
                    result = preprocess_payload(str(current), branch, {"steps": step_map[node_type]} | defaults | config)
                    value = result.canonical_text
                    event["compression"] = result.to_dict()
                    outputs[node_id] = {"value": value, "compression": result.to_dict()}
                elif node_type == "core_lm":
                    ingest = self.core.ingest(
                        session_id=session_id,
                        branch=branch,
                        text=str(current),
                        source={"source_id": node_id, "source_type": "workflow_node", "trust_level": config.get("trust_level", "medium")},
                        workflow_id=workflow_id,
                        fmt=str(config.get("format") or "markdown"),
                        compression=config.get("compression", {}),
                        annotations=config.get("annotations", []),
                    )
                    value = ingest["chat_message"]["content"]
                    event["event_id"] = ingest["event_id"]
                    event["ledger_entry_id"] = ingest["ledger_entry"]["entry_id"]
                    outputs[node_id] = {"value": value, "ingest": ingest}
                elif node_type in {"format", "formatting"}:
                    fmt = str(config.get("format") or "markdown")
                    value = format_payload(str(current), fmt, {"workflow_id": workflow_id, "node_id": node_id})
                    outputs[node_id] = {"value": value, "format": fmt}
                elif node_type == "chat":
                    message = self.core.record_chat_message(
                        session_id=session_id,
                        origin="workflow",
                        role="assistant",
                        content=str(current),
                        fmt=str(config.get("format") or "markdown"),
                        branch=branch,
                        workflow_id=workflow_id,
                        badges={"origin": "Workflow", "workflow": workflow_id, "branch": branch},
                        metadata={"node_id": node_id},
                    )
                    value = message["content"]
                    event["message_id"] = message["id"]
                    outputs[node_id] = {"value": value, "chat_message": message}
                elif node_type in {"outbound_prompt", "outbound", "file_export", "clipboard_export"}:
                    target_type = str(config.get("target_type") or ("file_export" if node_type == "file_export" else "programming_agent_packet"))
                    receipt = route_outbound(
                        target_type,
                        str(current),
                        config=config,
                        packet_type=str(config.get("packet_type") or "engineering_task_packet"),
                        metadata={"workflow_id": workflow_id, "node_id": node_id, "branch": branch},
                    )
                    value = receipt.get("packet") or receipt.get("path") or receipt.get("status")
                    event["receipt"] = receipt
                    outputs[node_id] = {"value": str(value), "receipt": receipt}
                else:
                    outputs[node_id] = {"value": str(current), "warning": f"Unknown node type: {node_type}"}
                    event["status"] = "warning"
                    event["warning"] = outputs[node_id]["warning"]
            except Exception as exc:  # noqa: BLE001 - workflow trace should preserve node failures
                outputs[node_id] = {"value": str(current), "error": str(exc)}
                event["status"] = "error"
                event["error"] = str(exc)
            trace.append(event)
            last_value = str(outputs[node_id].get("value") or last_value)
        return {
            "workflow_id": workflow_id,
            "status": "ok" if all(item["status"] != "error" for item in trace) else "error",
            "trace": trace,
            "outputs": outputs,
            "final": last_value,
        }
