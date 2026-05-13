export type HealthState = {
  status: string;
  service: string;
  state: StudioState;
};

export type SessionRecord = {
  id: string;
  name: string;
  seed: number;
  current_branch: string;
  created_at: string;
  updated_at: string;
};

export type StudioState = {
  session_id: string;
  digest: string;
  health: "healthy" | "attention" | string;
  branches: string[];
  stats: {
    durable_facts: number;
    current_facts: number;
    ledger_entries: number;
    invariant_violations: number;
    max_state_norm: number;
    mean_state_norm: number;
    provenance_coverage: number;
  };
  replay: {
    expected_digest: string;
    replay_digest: string;
    ok: boolean;
  };
  latest_ledger?: LedgerEntryCore | null;
};

export type ChatMessage = {
  id: string;
  session_id: string;
  origin: string;
  role: string;
  content: string;
  format: string;
  branch: string;
  workflow_id?: string | null;
  provenance_id?: string | null;
  ledger_entry_id?: string | null;
  badges: Record<string, unknown>;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type ConnectorRecord = {
  id: string;
  name: string;
  direction: "inbound" | "outbound" | string;
  type: string;
  config: Record<string, unknown>;
  secret_refs: string[];
  enabled: boolean;
  secrets_metadata?: Array<Record<string, unknown>>;
};

export type ConnectorRunResult = {
  raw_payload: string;
  normalized_payload: string;
  metadata: Record<string, unknown>;
};

export type ProviderMetrics = {
  version: string;
  provider: string;
  provider_metrics_available: boolean;
  native: Record<string, unknown>;
  local: Record<string, number | null>;
  derived: Record<string, number | null>;
  metric_sources: Record<string, string>;
  raw_usage: Record<string, unknown>;
};

export type QualityEvaluation = {
  version: string;
  modes: string[];
  summary_score: number | null;
  checks: Record<string, { passed: boolean | null; value: unknown; applicable: boolean; detail?: string | null }>;
  booleans: Record<string, boolean>;
  numeric_values: Record<string, number>;
  reference_provided: boolean;
  notes: string;
};

export type LocalRuntimeStatus = {
  provider: string;
  base_url: string;
  healthy: boolean;
  managed?: boolean;
  adopted?: boolean;
  owned?: boolean;
  command?: string[] | null;
  last_error?: string | null;
};

export type CompressionPreview = {
  raw_text: string;
  sanitized_text?: string | null;
  cleaned_text?: string | null;
  deduped_text?: string | null;
  canonicalized_text?: string | null;
  canonical_text: string;
  steps: string[];
  annotations: Array<Record<string, unknown>>;
  structured_extraction?: Array<Record<string, unknown>>;
  digest: string;
  compression_ratio: number;
  raw_length?: number;
  canonical_length?: number;
  token_proxy_before?: number;
  token_proxy_after?: number;
  contradiction_candidates: string[];
};

export type CompressionLookup = {
  session_id: string;
  target_type: string;
  target_id: string;
  packets: Array<{ label: string; packet: CompressionPreview }>;
};

export type LedgerEntryCore = {
  entry_id: string;
  event_id: string;
  branch: string;
  raw_text: string;
  admitted_claims: string[];
  deduped_claims: string[];
  rejected_claims: string[];
  current_norm: number;
  energy: number;
  csi: number;
  energy_drift: number;
  invariant_violations: string[];
};

export type LedgerMirror = {
  entry_id: string;
  session_id: string;
  event_id: string;
  branch: string;
  raw_text: string;
  created_at: string;
  corelm: LedgerEntryCore;
  metadata: Record<string, unknown>;
};

export type MetricRecord = {
  id: string;
  session_id: string;
  event_id: string;
  created_at: string;
  metric: Record<string, unknown>;
};

export type WorkflowNode = {
  id: string;
  type: string;
  position: { x: number; y: number };
  config: Record<string, unknown>;
};

export type WorkflowEdge = {
  id: string;
  source: string;
  target: string;
};

export type Workflow = {
  id: string;
  name: string;
  description?: string;
  schedule?: { enabled: boolean; cron?: string };
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
};

export type WorkflowRunResult = {
  workflow_id: string;
  run_id?: string | null;
  status: "ok" | "error" | string;
  trace: Array<Record<string, unknown>>;
  outputs: Record<string, Record<string, unknown>>;
  final: string;
  quality_eval?: QualityEvaluation;
};

export type WorkflowRunRecord = {
  id: string;
  workflow_id: string;
  session_id: string;
  status: string;
  trace: Array<Record<string, unknown>>;
  outputs: Record<string, Record<string, unknown>>;
  final_output: string;
  created_at: string;
};

export type ReplaySnapshot = {
  id: string;
  session_id: string;
  digest: string;
  ok: boolean;
  snapshot: Record<string, unknown>;
  created_at: string;
};
