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
  metric: Record<string, number | string | boolean>;
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
  status: "ok" | "error" | string;
  trace: Array<Record<string, unknown>>;
  outputs: Record<string, Record<string, unknown>>;
  final: string;
};
