import type { Workflow } from "./types";

export const defaultWorkflow: Workflow = {
  id: "demo-canonical-flow",
  name: "Canonical Core LM Flow",
  description: "Manual text through Core LM and outbound packet export.",
  schedule: { enabled: false, cron: "" },
  nodes: [
    { id: "n1", type: "manual_text_input", position: { x: 48, y: 96 }, config: { text: "project.name = Core LM Studio" } },
    { id: "n2", type: "clean_text", position: { x: 292, y: 96 }, config: {} },
    { id: "n3", type: "canonicalize", position: { x: 536, y: 96 }, config: {} },
    { id: "n4", type: "core_lm", position: { x: 780, y: 96 }, config: { format: "markdown" } },
    { id: "n5", type: "chat", position: { x: 1024, y: 96 }, config: {} },
    { id: "n6", type: "outbound_prompt", position: { x: 1268, y: 96 }, config: { target_type: "programming_agent_packet" } }
  ],
  edges: [
    { id: "e1", source: "n1", target: "n2" },
    { id: "e2", source: "n2", target: "n3" },
    { id: "e3", source: "n3", target: "n4" },
    { id: "e4", source: "n4", target: "n5" },
    { id: "e5", source: "n5", target: "n6" }
  ]
};

export const defaultOllamaConfig: Record<string, unknown> = {
  mock: true,
  base_url: "http://127.0.0.1:11434",
  model: "llama3.1",
  format: "plain",
  raw: false,
  stream: false,
  keep_alive: "5m",
  seed: "",
  temperature: 0.2,
  top_p: 0.9,
  top_k: 40,
  min_p: 0,
  repeat_penalty: 1.1,
  repeat_last_n: 64,
  num_ctx: 4096,
  num_predict: 128,
  stop: ""
};
