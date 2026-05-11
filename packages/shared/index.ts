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
