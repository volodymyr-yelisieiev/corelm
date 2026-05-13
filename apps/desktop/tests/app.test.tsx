import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import App from "../src/App";

const workflow = {
  id: "demo-canonical-flow",
  name: "Canonical Core LM Flow",
  nodes: [
    { id: "n1", type: "manual_text_input", position: { x: 48, y: 96 }, config: { text: "project.name = Core LM Studio" } },
    { id: "n2", type: "core_lm", position: { x: 292, y: 96 }, config: {} }
  ],
  edges: [{ id: "e1", source: "n1", target: "n2" }]
};

beforeEach(() => {
  vi.restoreAllMocks();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/api/health")) {
        return Response.json({
          status: "ok",
          service: "core-lm-studio",
          state: {
            session_id: "default",
            digest: "abcdef0123456789",
            health: "healthy",
            branches: ["corelm"],
            stats: {
              durable_facts: 1,
              current_facts: 1,
              ledger_entries: 1,
              invariant_violations: 0,
              max_state_norm: 1,
              mean_state_norm: 1,
              provenance_coverage: 1
            },
            replay: { expected_digest: "abc", replay_digest: "abc", ok: true }
          }
        });
      }
      if (url.includes("/api/chat")) {
        return Response.json([]);
      }
      if (url.includes("/api/ledger")) {
        return Response.json([]);
      }
      if (url.includes("/api/metrics")) {
        return Response.json([
          {
            id: "metric-1",
            session_id: "default",
            event_id: "evt-1",
            created_at: "2026-05-13T00:00:00Z",
            metric: {
              state_norm: 1,
              drift: 0.1,
              energy: 0.2,
              provider_metrics_available: true,
              provider_total_latency_ms: 12.34,
              provider_load_latency_ms: 2.5,
              prompt_tokens: 3,
              completion_tokens: 4,
              total_tokens: 7,
              generation_tokens_per_second: 22.2,
              prompt_tokens_per_second: 30.1,
              end_to_end_tokens_per_second: 18.4,
              compression_ratio_proxy: 0.75,
              quality_eval: { version: "quality_eval.v1", modes: ["general_text"], summary_score: 0.9, checks: {}, booleans: {}, numeric_values: {}, reference_provided: false, notes: "" }
            }
          }
        ]);
      }
      if (url.includes("/api/quality")) {
        return Response.json([
          {
            id: "quality-1",
            target_type: "ledger_entry",
            target_id: "l1",
            evaluation: {
              version: "quality_eval.v1",
              modes: ["general_text"],
              summary_score: 0.9,
              checks: {},
              booleans: {},
              numeric_values: {},
              reference_provided: false,
              notes: ""
            }
          }
        ]);
      }
      if (url.includes("/api/local-runtimes/ollama/ensure")) {
        return Response.json({ provider: "ollama", base_url: "http://127.0.0.1:11434", healthy: true, managed: true });
      }
      if (url.includes("/api/local-runtimes")) {
        return Response.json({ provider: "ollama", base_url: "http://127.0.0.1:11434", healthy: false, last_error: null });
      }
      if (url.includes("/api/compression/preview")) {
        return Response.json({
          raw_text: " project.name = Core LM Studio \n project.name = Core LM Studio ",
          canonical_text: "sha256:preview\nbytes:29\npreview:project.name = Core LM Studio",
          steps: ["sanitize", "clean", "dedupe", "canonicalize", "schema_extract", "hash_compress"],
          annotations: [{ subject: "project", attribute: "name", value: "Core LM Studio" }],
          digest: "abcdef0123456789abcdef",
          compression_ratio: 0.75,
          contradiction_candidates: []
        });
      }
      if (url.includes("/api/connectors/run-ingest")) {
        return Response.json({
          connector: {
            raw_payload: "local_model.name = gemma-4",
            normalized_payload: "local_model.name = gemma-4",
            metadata: {}
          },
          ingest: {
            event_id: "evt-lmstudio",
            digest: "digest-lmstudio"
          }
        });
      }
      if (url.includes("/api/connectors")) {
        return Response.json([]);
      }
      if (url.includes("/api/settings")) {
        return Response.json({ console_density: "comfortable" });
      }
      if (url.includes("/api/replay/snapshots")) {
        return Response.json([]);
      }
      if (url.includes("/api/workflows/") && url.includes("/run") && !url.includes("/runs")) {
        return Response.json({
          workflow_id: "demo-canonical-flow",
          run_id: "run-1",
          status: "ok",
          final: "done",
          outputs: {},
          quality_eval: { version: "quality_eval.v1", modes: ["workflow"], summary_score: 1, checks: {}, booleans: {}, numeric_values: {}, reference_provided: false, notes: "" },
          trace: [
            {
              node_id: "n2",
              type: "core_lm",
              status: "ok",
              compression: {
                raw_text: "project.name = Core LM Studio",
                canonical_text: "sha256:flow\npreview:project.name = Core LM Studio",
                steps: ["sanitize", "hash_compress"],
                annotations: [],
                digest: "flowdigest",
                compression_ratio: 0.5,
                contradiction_candidates: []
              }
            }
          ]
        });
      }
      if (url.includes("/api/workflows/runs")) {
        return Response.json([]);
      }
      if (url.includes("/api/workflows")) {
        return Response.json([workflow]);
      }
      return Response.json({});
    })
  );
});

describe("Core LM Studio desktop shell", () => {
  it("renders console mode and switches to flow studio", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText("Core LM Studio")).toBeInTheDocument());
    expect(screen.getByTestId("console-mode")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Flow Studio/i }));
    expect(screen.getByTestId("flow-mode")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Canonical Core LM Flow" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /^Core$/i }));
    expect(screen.getAllByText("core_lm").length).toBeGreaterThan(0);
  });

  it("renders connector controls in the console drawer", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByTestId("console-mode")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /Connectors/i }));
    expect(screen.getByRole("button", { name: /Run through Core/i })).toBeInTheDocument();
    expect(screen.getByDisplayValue("Mock ingress")).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "LM Studio gemma-4" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "File input" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "REST input" })).toBeInTheDocument();
  });

  it("opens the compression inspector from the console action pad", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByTestId("console-mode")).toBeInTheDocument());

    fireEvent.click(screen.getByRole("button", { name: /^Compress$/i }));

    await waitFor(() => expect(screen.getByText("ratio 0.750")).toBeInTheDocument());
    expect(screen.getByText("Raw -> Canonical")).toBeInTheDocument();
    expect(screen.getByText("hash_compress")).toBeInTheDocument();
    expect(screen.getAllByText(/sha256:preview/).length).toBeGreaterThan(0);

    const runCall = vi.mocked(fetch).mock.calls.find(([input]) => String(input).includes("/api/compression/preview"));
    const body = JSON.parse(String(runCall?.[1]?.body));
    expect(body.branch).toBe("corelm");
    expect(body.compression.steps).toContain("schema_extract");
    expect(body.compression.steps).toContain("hash_compress");
  });

  it("renders provider metrics and quality summary cards", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByRole("status", { name: "Run metrics" })).toBeInTheDocument());
    expect(screen.getByText("12.3 ms")).toBeInTheDocument();
    expect(screen.getByText("22.2")).toBeInTheDocument();
    expect(screen.getByText("90%")).toBeInTheDocument();
    expect(screen.getByText("available")).toBeInTheDocument();
  });

  it("runs the LM Studio preset with local OpenAI-compatible config", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByTestId("console-mode")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /Connectors/i }));

    fireEvent.change(screen.getByDisplayValue("OpenAI-compatible"), { target: { value: "lm_studio" } });
    expect(screen.getAllByDisplayValue("LM Studio gemma-4").some((element) => element.tagName === "INPUT")).toBe(true);

    fireEvent.click(screen.getByRole("button", { name: /Run through Core/i }));

    await waitFor(() => {
      const calls = vi.mocked(fetch).mock.calls;
      expect(calls.some(([input]) => String(input).includes("/api/connectors/run-ingest"))).toBe(true);
    });
    const runCall = vi.mocked(fetch).mock.calls.find(([input]) => String(input).includes("/api/connectors/run-ingest"));
    const body = JSON.parse(String(runCall?.[1]?.body));
    expect(body.connector_type).toBe("lm_studio");
    expect(body.config.base_url).toBe("http://127.0.0.1:1234/v1");
    expect(body.config.model).toBe("gemma-4-e4b-uncensored-hauhaucs-aggressive");
    expect(body.config.mock).toBe(false);
  });

  it("applies the Ollama deterministic benchmark preset", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByTestId("console-mode")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /Connectors/i }));

    fireEvent.change(screen.getByDisplayValue("OpenAI-compatible"), { target: { value: "ollama_local_model" } });
    fireEvent.click(screen.getByRole("button", { name: /Benchmark Preset/i }));
    expect(screen.getByText("non-default sampling")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Run through Core/i }));

    await waitFor(() => {
      const calls = vi.mocked(fetch).mock.calls;
      expect(calls.some(([input]) => String(input).includes("/api/connectors/run-ingest"))).toBe(true);
    });
    const runCalls = vi.mocked(fetch).mock.calls.filter(([input]) => String(input).includes("/api/connectors/run-ingest"));
    const runCall = runCalls[runCalls.length - 1];
    const body = JSON.parse(String(runCall?.[1]?.body));
    expect(body.connector_type).toBe("ollama_local_model");
    expect(body.config.stream).toBe(false);
    expect(body.config.seed).toBe(0);
    expect(body.config.temperature).toBe(0);
    expect(body.config.top_p).toBe(1);
    expect(body.config.top_k).toBe(40);
    expect(body.config.num_predict).toBe(128);
    expect(body.config.mock).toBe(false);
    expect(body.config.auto_start).toBe(true);
  });

  it("shows and starts the managed Ollama runtime from connector settings", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByTestId("console-mode")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /Connectors/i }));
    fireEvent.change(screen.getByDisplayValue("OpenAI-compatible"), { target: { value: "ollama_local_model" } });

    expect(screen.getByText("Ollama not running")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Start Local Server/i }));

    await waitFor(() => {
      const calls = vi.mocked(fetch).mock.calls;
      expect(calls.some(([input]) => String(input).includes("/api/local-runtimes/ollama/ensure"))).toBe(true);
    });
  });

  it("opens flow compression inspection by switching to the visible inspector", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByTestId("console-mode")).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: /Flow Studio/i }));
    fireEvent.click(screen.getByRole("button", { name: /Test Run/i }));

    await waitFor(() => expect(screen.getByText("Inspect compression")).toBeInTheDocument());
    fireEvent.click(screen.getByText("Inspect compression"));

    await waitFor(() => expect(screen.getByTestId("console-mode")).toBeInTheDocument());
    expect(screen.getByText("workflow:run-1.n2")).toBeInTheDocument();
    expect(screen.getByText("Raw -> Canonical")).toBeInTheDocument();
  });

  it("keeps the console online when an auxiliary endpoint fails", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url.includes("/api/settings")) {
          return new Response("settings unavailable", { status: 503 });
        }
        if (url.includes("/api/health")) {
          const state = {
              session_id: "default",
              digest: "abcdef0123456789",
              health: "healthy",
              branches: ["corelm"],
              stats: {
                durable_facts: 1,
                current_facts: 1,
                ledger_entries: 1,
                invariant_violations: 0,
                max_state_norm: 1,
                mean_state_norm: 1,
                provenance_coverage: 1
              },
              replay: { expected_digest: "abc", replay_digest: "abc", ok: true }
            };
          return Response.json({
            status: "ok",
            service: "core-lm-studio",
            state
          });
        }
        if (url.includes("/api/state")) {
          return Response.json({
            session_id: "default",
            digest: "abcdef0123456789",
            health: "healthy",
            branches: ["corelm"],
            stats: {
              durable_facts: 1,
              current_facts: 1,
              ledger_entries: 1,
              invariant_violations: 0,
              max_state_norm: 1,
              mean_state_norm: 1,
              provenance_coverage: 1
            },
            replay: { expected_digest: "abc", replay_digest: "abc", ok: true }
          });
        }
        if (url.includes("/api/sessions")) {
          return Response.json([]);
        }
        if (url.includes("/api/workflows")) {
          return Response.json([workflow]);
        }
        return Response.json([]);
      })
    );
    render(<App />);
    await waitFor(() => expect(screen.getByText("online")).toBeInTheDocument());
  });
});
