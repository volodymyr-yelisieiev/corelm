import type {
  BenchmarkProfile,
  BenchmarkRun,
  ChatMessage,
  CompressionLookup,
  CompressionPreview,
  ConnectorRecord,
  ConnectorRunResult,
  DirectRuntimeAdapterInfo,
  HealthState,
  LedgerMirror,
  LocalRuntimeStatus,
  MetricRecord,
  QualityEvaluation,
  ReplaySnapshot,
  SessionRecord,
  StudioState,
  Workflow,
  WorkflowRunRecord,
  WorkflowRunResult
} from "./types";

declare global {
  interface Window {
    corelmStudio?: {
      serviceUrl: string;
    };
  }
}

const SERVICE_URL = window.corelmStudio?.serviceUrl ?? "http://127.0.0.1:8765";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${SERVICE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {})
    }
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return response.json() as Promise<T>;
}

async function requestText(path: string): Promise<string> {
  const response = await fetch(`${SERVICE_URL}${path}`);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || response.statusText);
  }
  return response.text();
}

export const api = {
  serviceUrl: SERVICE_URL,
  health: () => request<HealthState>("/api/health"),
  state: (sessionId = "default") => request<StudioState>(`/api/state?session_id=${encodeURIComponent(sessionId)}`),
  sessions: () => request<SessionRecord[]>("/api/sessions"),
  createSession: (name: string) =>
    request<SessionRecord>("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ name, current_branch: "corelm" })
    }),
  chat: (sessionId = "default") => request<ChatMessage[]>(`/api/chat?session_id=${encodeURIComponent(sessionId)}&limit=200`),
  ledger: (sessionId = "default") => request<LedgerMirror[]>(`/api/ledger?session_id=${encodeURIComponent(sessionId)}&limit=200`),
  ledgerEntry: (entryId: string, sessionId = "default") =>
    request<LedgerMirror>(`/api/ledger/${encodeURIComponent(entryId)}?session_id=${encodeURIComponent(sessionId)}`),
  metrics: (sessionId = "default") => request<MetricRecord[]>(`/api/metrics?session_id=${encodeURIComponent(sessionId)}&limit=200`),
  localRuntime: (provider = "ollama", baseUrl?: string) => {
    const params = new URLSearchParams({ provider });
    if (baseUrl) {
      params.set("base_url", baseUrl);
    }
    return request<LocalRuntimeStatus>(`/api/local-runtimes?${params.toString()}`);
  },
  ensureLocalRuntime: (provider: string, config: Record<string, unknown>) =>
    request<LocalRuntimeStatus>(`/api/local-runtimes/${encodeURIComponent(provider)}/ensure`, {
      method: "POST",
      body: JSON.stringify({ provider, base_url: String(config.base_url ?? ""), config })
    }),
  quality: (sessionId = "default", targetType?: string, targetId?: string) => {
    const params = new URLSearchParams({ session_id: sessionId, limit: "200" });
    if (targetType) {
      params.set("target_type", targetType);
    }
    if (targetId) {
      params.set("target_id", targetId);
    }
    return request<Array<{ id: string; target_type: string; target_id: string; evaluation: QualityEvaluation }>>(`/api/quality?${params.toString()}`);
  },
  connectors: () => request<ConnectorRecord[]>("/api/connectors"),
  connectorCatalog: () => request<Record<string, Array<Record<string, unknown>>>>("/api/connectors/catalog"),
  saveConnector: (connector: ConnectorRecord) =>
    request<ConnectorRecord>("/api/connectors", {
      method: "POST",
      body: JSON.stringify({ connector })
    }),
  deleteConnector: (connectorId: string) =>
    request<Record<string, unknown>>(`/api/connectors/${encodeURIComponent(connectorId)}`, {
      method: "DELETE"
    }),
  runConnectorIngest: (payload: {
    connector_type: string;
    session_id: string;
    branch: string;
    config: Record<string, unknown>;
    format?: string;
    compression?: Record<string, unknown>;
    evaluator_config?: Record<string, unknown>;
  }) =>
    request<{ connector: ConnectorRunResult; ingest: Record<string, unknown> }>("/api/connectors/run-ingest", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  workflows: () => request<Workflow[]>("/api/workflows"),
  workflowRuns: (sessionId = "default") =>
    request<WorkflowRunRecord[]>(`/api/workflows/runs?session_id=${encodeURIComponent(sessionId)}&limit=100`),
  saveWorkflow: (workflow: Workflow) =>
    request<Workflow>("/api/workflows", {
      method: "POST",
      body: JSON.stringify({ workflow })
    }),
  runWorkflow: (workflow: Workflow, sessionId: string, branch: string, inputs: Record<string, unknown>) =>
    request<WorkflowRunResult>(`/api/workflows/${encodeURIComponent(workflow.id)}/run`, {
      method: "POST",
      body: JSON.stringify({ workflow, session_id: sessionId, branch, inputs })
    }),
  cloneWorkflow: (workflowId: string) =>
    request<Workflow>(`/api/workflows/${encodeURIComponent(workflowId)}/clone`, {
      method: "POST"
    }),
  ingest: (payload: {
    session_id: string;
    branch: string;
    text: string;
    format: string;
    compression?: Record<string, unknown>;
    source?: Record<string, unknown>;
    annotations?: Array<Record<string, unknown>>;
  }) =>
    request<Record<string, unknown>>("/api/ingest", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  compressionPreview: (payload: {
    text: string;
    branch: string;
    compression?: Record<string, unknown>;
    annotations?: Array<Record<string, unknown>>;
  }) =>
    request<CompressionPreview>("/api/compression/preview", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  compressionLookup: (sessionId: string, targetType: string, targetId: string) =>
    request<CompressionLookup>(
      `/api/compression?session_id=${encodeURIComponent(sessionId)}&target_type=${encodeURIComponent(targetType)}&target_id=${encodeURIComponent(targetId)}`
    ),
  routeChat: (messageId: string, sessionId: string, packetType = "engineering_task_packet") =>
    request<Record<string, unknown>>(`/api/chat/${encodeURIComponent(messageId)}/route?session_id=${encodeURIComponent(sessionId)}`, {
      method: "POST",
      body: JSON.stringify({
        target_type: "programming_agent_packet",
        packet_type: packetType,
        config: { mock: true }
      })
    }),
  promoteChat: (messageId: string, sessionId: string, branch: string) =>
    request<Record<string, unknown>>(`/api/chat/${encodeURIComponent(messageId)}/promote?session_id=${encodeURIComponent(sessionId)}`, {
      method: "POST",
      body: JSON.stringify({ branch, subject: "chat", attribute: "promoted_note" })
    }),
  replay: (sessionId = "default") => request<Record<string, unknown>>(`/api/replay?session_id=${encodeURIComponent(sessionId)}`),
  replaySnapshots: (sessionId = "default") =>
    request<ReplaySnapshot[]>(`/api/replay/snapshots?session_id=${encodeURIComponent(sessionId)}&limit=100`),
  provenance: (sessionId: string, branch: string, subject: string, attribute: string) =>
    request<Record<string, unknown>>(
      `/api/provenance?session_id=${encodeURIComponent(sessionId)}&branch=${encodeURIComponent(branch)}&subject=${encodeURIComponent(subject)}&attribute=${encodeURIComponent(attribute)}`
    ),
  settings: () => request<Record<string, unknown>>("/api/settings"),
  updateSettings: (settings: Record<string, unknown>) =>
    request<Record<string, unknown>>("/api/settings", {
      method: "POST",
      body: JSON.stringify({ settings })
    }),
  directRuntimeAdapters: () => request<DirectRuntimeAdapterInfo[]>("/api/direct-runtimes/adapters"),
  directRuntimeModels: (adapterId?: string) => {
    const params = new URLSearchParams();
    if (adapterId) {
      params.set("adapter_id", adapterId);
    }
    return request<Array<Record<string, unknown>>>(`/api/direct-runtimes/models${params.toString() ? `?${params.toString()}` : ""}`);
  },
  benchmarkProfiles: () => request<BenchmarkProfile[]>("/api/benchmarks/profiles"),
  saveBenchmarkProfile: (profile: BenchmarkProfile) =>
    request<BenchmarkProfile>("/api/benchmarks/profiles", {
      method: "POST",
      body: JSON.stringify({ profile })
    }),
  runBenchmark: (payload: { profile_id?: string; profile?: BenchmarkProfile; session_id: string; branch: string }) =>
    request<BenchmarkRun>("/api/benchmarks/run", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  benchmarkRuns: (sessionId = "default") => request<BenchmarkRun[]>(`/api/benchmarks/runs?session_id=${encodeURIComponent(sessionId)}&limit=100`),
  benchmarkReport: (runId: string, format = "markdown") =>
    requestText(`/api/benchmarks/runs/${encodeURIComponent(runId)}/report?format=${encodeURIComponent(format)}`)
};
