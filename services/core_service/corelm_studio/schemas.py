from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ConnectorMetadata(BaseModel):
    source_id: str
    source_type: str
    timestamp: str
    content_type: str = "text/plain"
    branch: str = "corelm"
    workspace: str = "default"
    trust_level: str = "medium"
    schema_tag: str | None = None


class ConnectorRunRequest(BaseModel):
    connector_type: str
    config: dict[str, Any] = Field(default_factory=dict)
    branch: str = "corelm"


class ConnectorIngestRequest(BaseModel):
    connector_type: str
    config: dict[str, Any] = Field(default_factory=dict)
    session_id: str = "default"
    branch: str = "corelm"
    workflow_id: str | None = None
    format: str = "markdown"
    compression: dict[str, Any] = Field(default_factory=dict)
    annotations: list[dict[str, Any]] = Field(default_factory=list)
    evaluator_config: dict[str, Any] = Field(default_factory=dict)


class ConnectorSaveRequest(BaseModel):
    connector: dict[str, Any]


class IngestRequest(BaseModel):
    session_id: str = "default"
    branch: str = "corelm"
    text: str
    source: dict[str, Any] = Field(default_factory=dict)
    workflow_id: str | None = None
    format: str = "markdown"
    compression: dict[str, Any] = Field(default_factory=dict)
    annotations: list[dict[str, Any]] = Field(default_factory=list)
    evaluator_config: dict[str, Any] = Field(default_factory=dict)


class CompressionPreviewRequest(BaseModel):
    text: str
    branch: str = "corelm"
    compression: dict[str, Any] = Field(default_factory=dict)
    annotations: list[dict[str, Any]] = Field(default_factory=list)


class ChatRouteRequest(BaseModel):
    target_type: str
    config: dict[str, Any] = Field(default_factory=dict)
    packet_type: str = "engineering_task_packet"


class WorkflowSaveRequest(BaseModel):
    workflow: dict[str, Any]


class WorkflowRunRequest(BaseModel):
    workflow: dict[str, Any] | None = None
    session_id: str = "default"
    branch: str = "corelm"
    inputs: dict[str, Any] = Field(default_factory=dict)


class OutboundRouteRequest(BaseModel):
    target_type: str
    content: str
    config: dict[str, Any] = Field(default_factory=dict)
    packet_type: str = "engineering_task_packet"
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionCreateRequest(BaseModel):
    id: str | None = None
    name: str = "Core LM Studio Session"
    seed: int = 0
    current_branch: str = "corelm"


class ChatPromoteRequest(BaseModel):
    branch: str = "corelm"
    subject: str = "chat"
    attribute: str = "note"
    tags: list[str] = Field(default_factory=lambda: ["promoted-from-chat"])


class SettingsUpdateRequest(BaseModel):
    settings: dict[str, Any] = Field(default_factory=dict)


class LocalRuntimeEnsureRequest(BaseModel):
    provider: str | None = None
    base_url: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)


FormatName = Literal[
    "markdown",
    "plain_text",
    "json",
    "yaml",
    "xml",
    "code_task_prompt",
    "developer_handoff_packet",
]
