# Core LM Studio Implementation Plan

## Reusable Core LM Assets

The existing repository already contains the pieces that should remain canonical:

- `corelm/product.py`: local product wrapper with session persistence, fact
  ingestion, correction, branch listing, provenance, state export, and replay
  verification.
- `corelm/reference_kernel.py`: deterministic reference kernel with numeric
  state update, bounded invariant checks, append-only ledger entries,
  branch-aware fact records, deduplication, supersession, and provenance.
- `corelm/schema.py`: event, claim, query, fact, and ledger dataclasses.
- `corelm/vendor/lucid_mind_v15_core_ref.py`: bundled reference numeric Core LM
  implementation and deterministic text embedding source.
- `benches/scenarios/*.json`: regression and trace scenarios for Core LM
  behavior.
- `docs/sources/*.md`: state-space, perturbation, and orchestrator formalization
  documents. These are architectural inputs for the Studio sidecar, not UI copy.

The Studio implementation wraps these assets instead of replacing them.

## Assumptions

- The repository remains a local-first single-user app.
- Windows packaging is configured from macOS/Linux development environments but
  final signed installer validation is a Windows release step.
- External LLM and REST connectors ship with interfaces, config surfaces,
  deterministic mock transports, and documented real hookup paths.
- SQLite is the durable app store. Raw secret values are not persisted there.
- The Python sidecar is authoritative for Core LM state, workflows, ledger,
  provenance, replay, chat bus persistence, and connector execution.

## Phase 1 - Planning and Repo Guidance

- Add `AGENTS.md` to anchor repository-level guidance for future Codex work.
- Add this plan and `docs/architecture_decisions.md`.
- Preserve existing publication/reference tests.

## Phase 2 - Application and Service Scaffold

- Create `services/core_service/corelm_studio` as a local FastAPI sidecar.
- Add SQLite schema for sessions, workflows, workflow nodes, connectors, chat
  messages, ledger entries, replay snapshots, metrics, and secrets metadata.
- Add Electron + React + TypeScript desktop shell under `apps/desktop`.
- Add local run scripts so the desktop app can boot the sidecar automatically.

## Phase 3 - Core LM Integration

- Implement a `StudioCore` wrapper around `CoreLMProduct`.
- Expose APIs for ingestion, metrics, ledger, provenance, replay, sessions,
  branch state, and health.
- Persist Core LM ledger mirrors and replay snapshots to SQLite after admissible
  transitions.

## Phase 4 - Connectors, Compression, Workflow, Chat

- Implement plugin-style inbound connectors:
  OpenAI-compatible LLM, Ollama/local model, file, folder watcher metadata,
  generic web/API fetch, clipboard, REST, manual text, and shell/CLI capture.
- Implement preprocessing nodes: cleaning, chunking, dedupe, summarization,
  schema/key-value extraction, canonicalization, hash compression, digest
  generation, and contradiction candidate tagging.
- Implement workflow JSON save/load/run with deterministic trace logs.
- Persist global chat bus messages with origin, workflow, branch, format, and
  provenance references.

## Phase 5 - Outbound Routing and UI Completion

- Implement outbound adapters for HTTP/REST, OpenAI-compatible, local model,
  file export, clipboard export, shell/CLI handoff, and programming-agent packet
  export.
- Build Console Mode with calculator-inspired main interaction.
- Build Flow Studio Mode with draggable nodes, edges, inspector, trace,
  save/load/clone/import/export, and test run.
- Add ledger, provenance, replay, history, connectors, settings, branch/session
  controls, command palette, keyboard shortcuts, and drag/drop file ingestion.

## Phase 6 - Packaging, Tests, Documentation

- Add unit and integration tests for sidecar contracts and Core LM flow.
- Add UI smoke checks for launch surfaces and chat/workflow behavior.
- Add Windows packaging configuration with `electron-builder`.
- Write README, quickstart, architecture, connector, workflow, security, replay,
  Windows build, sample workflows, sample connector configs, and prompt
  templates.
- Run tests/builds and fix failures until the repo is buildable and demonstrable.

## Definition of Done Mapping

- Desktop app launches locally through `npm run desktop:dev`.
- Electron main process starts and stops the Python sidecar.
- Manual/file/mock LLM/local connector ingestion reaches Core LM.
- Compression/canonicalization runs before durable Core LM commit.
- Ledger, provenance, metrics, replay snapshot, and chat bus entries are visible
  through APIs and UI.
- A chat message routes to at least one programming-oriented outbound adapter.
- Tests pass for the old reference bundle and new Studio service/frontend
  surfaces.
