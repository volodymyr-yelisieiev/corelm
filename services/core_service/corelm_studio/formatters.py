from __future__ import annotations

import json
import html
from typing import Any

from .security import sanitize_obj, sanitize_text


def _yaml_lines(value: Any, indent: int = 0) -> list[str]:
    prefix = " " * indent
    if isinstance(value, dict):
        lines: list[str] = []
        for key, item in value.items():
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}{key}:")
                lines.extend(_yaml_lines(item, indent + 2))
            else:
                lines.append(f"{prefix}{key}: {json.dumps(item, ensure_ascii=False)}")
        return lines
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, (dict, list)):
                lines.append(f"{prefix}-")
                lines.extend(_yaml_lines(item, indent + 2))
            else:
                lines.append(f"{prefix}- {json.dumps(item, ensure_ascii=False)}")
        return lines
    return [f"{prefix}{json.dumps(value, ensure_ascii=False)}"]


def format_payload(content: str, fmt: str, metadata: dict[str, Any] | None = None) -> str:
    metadata = sanitize_obj(metadata or {})
    content = sanitize_text(content)
    fmt = fmt.lower().replace("-", "_")
    packet = {"content": content, "metadata": metadata}
    if fmt == "plain_text":
        return content
    if fmt == "json":
        return json.dumps(packet, ensure_ascii=False, indent=2)
    if fmt == "yaml":
        return "\n".join(_yaml_lines(packet))
    if fmt == "xml":
        meta_xml = "".join(
            f"<meta key=\"{html.escape(str(key))}\">{html.escape(str(value))}</meta>"
            for key, value in metadata.items()
        )
        return f"<corelm-output>{meta_xml}<content>{html.escape(content)}</content></corelm-output>"
    if fmt == "code_task_prompt":
        return (
            "You are a coding agent receiving a Core LM routed task.\n\n"
            "## Canonical Context\n"
            f"{content}\n\n"
            "## Constraints\n"
            "- Treat Core LM ledger/provenance as the source of truth.\n"
            "- Do not infer unrecorded facts as canonical.\n"
            "- Return implementation changes and verification steps.\n"
        )
    if fmt == "developer_handoff_packet":
        return (
            "# Core LM Developer Handoff Packet\n\n"
            f"## Canonical Output\n{content}\n\n"
            "## Provenance Metadata\n"
            f"```json\n{json.dumps(metadata, ensure_ascii=False, indent=2)}\n```\n\n"
            "## Handling Rules\n"
            "- Preserve branch isolation.\n"
            "- Route durable changes back through Core LM ingestion.\n"
            "- Do not treat chat text as canonical state.\n"
        )
    return f"## Core LM Output\n\n{content}\n"


def prompt_template(packet_type: str, content: str, metadata: dict[str, Any] | None = None) -> str:
    metadata = sanitize_obj(metadata or {})
    base = format_payload(content, "developer_handoff_packet", metadata)
    packet_type = packet_type.lower().replace("-", "_")
    if packet_type == "implementation_packet":
        return base + "\n## Requested Output\nImplement the change, preserve existing architecture, and include verification evidence.\n"
    if packet_type == "bug_report_packet":
        return base + "\n## Requested Output\nDiagnose the bug, propose a fix, and include tests.\n"
    if packet_type == "code_review_packet":
        return base + "\n## Requested Output\nReturn prioritized findings with file and line references.\n"
    if packet_type == "repo_handoff_packet":
        return base + "\n## Requested Output\nSummarize repo state, next actions, and verification gaps.\n"
    if packet_type == "prompt_packet" or packet_type == "prompt_for_coding_agent":
        return base + "\n## Requested Output\nConvert this into a concise, executable prompt for an external coding agent.\n"
    if packet_type == "json_job_spec":
        return json.dumps({"type": packet_type, "content": content, "metadata": metadata}, ensure_ascii=False, indent=2)
    if packet_type == "markdown_brief":
        return f"# Core LM Brief\n\n{content}\n"
    return base + "\n## Requested Output\nExecute the engineering task and report verification.\n"
