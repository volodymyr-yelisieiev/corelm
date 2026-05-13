export type CoreLMBranch = string;

export type ConnectorMetadata = {
  source_id: string;
  source_type: string;
  timestamp: string;
  content_type: string;
  branch: string;
  workspace: string;
  trust_level: "low" | "medium" | "high" | string;
  schema_tag?: string | null;
  provider_metrics?: ProviderMetrics | null;
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

export type ChatBusMessage = {
  id: string;
  origin: string;
  role: "user" | "assistant" | "system" | string;
  content: string;
  format: string;
  branch: CoreLMBranch;
  provenance_id?: string | null;
  ledger_entry_id?: string | null;
};
