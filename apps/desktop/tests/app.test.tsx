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
        return Response.json([]);
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
    expect(screen.getByRole("option", { name: "File input" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "REST input" })).toBeInTheDocument();
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
