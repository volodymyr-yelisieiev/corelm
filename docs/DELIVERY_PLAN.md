# Core LM Studio Delivery Plan

This plan keeps the existing repository architecture and works forward from the
current Studio skeleton. The sidecar remains the owner of durable state and all
canonical mutations continue to flow through Core LM.

## Phase 1 - Audit And Baseline

- Read the required repository guidance and implementation surfaces.
- Write `docs/GAP_ANALYSIS.md` and this delivery plan.
- Run:
  - `PYTHONPATH=. python -m services.core_service.corelm_studio`
  - `PYTHONPATH=. python -m pytest -q`
  - `npm run desktop:test`
  - `npm run desktop:build`
  - `npm run desktop:package:win` where feasible
- Record concrete failures in docs and fix the underlying command paths.

## Phase 2 - Boot Reliability

- Stabilize sidecar import and launch from source.
- Confirm Electron main process starts the sidecar and renderer reliably.
- Ensure default SQLite bootstrap creates a usable default session and workflow.
- Keep `CORELM_STUDIO_SERVICE_CMD`, `CORELM_STUDIO_DATA_DIR`, host, and port
  overrides functional for Windows development and packaged runs.

## Phase 3 - Core LM API Hardening

- Keep `StudioCore.ingest()` as the only durable mutation path.
- Add or harden endpoints for:
  - state summaries;
  - ledger details;
  - provenance and supersession;
  - replay snapshots;
  - metrics;
  - connector run-to-ingest flow;
  - settings and persisted UI preferences.
- Expand tests around branch isolation, dedupe, correction/supersession,
  provenance, replay consistency, and secret redaction.

## Phase 4 - Console Mode Completion

- Preserve the dark calculator-inspired visual system.
- Improve the main Core LM readout, state widget, branch/session selectors,
  connection status, command palette, and action pad.
- Make side drawers operational for:
  - searchable global chat history;
  - sessions;
  - connector management;
  - settings;
  - ledger;
  - provenance;
  - replay.
- Add route/copy/export actions on chat messages and show outbound receipts in
  the chat timeline.

## Phase 5 - Flow Studio Completion

- Add node palette insertion for inbound, preprocessing, Core LM, format, chat,
  and outbound node families.
- Add edge creation/removal, node deletion, and workflow validation.
- Persist workflow save/load/clone/import/export.
- Persist and display execution trace details, node errors, final output, and
  route receipts.
- Keep manual test runs deterministic by default.

## Phase 6 - Connectors, Compression, And Outbound Routes

- Complete inbound connector contracts with raw payload, normalized payload,
  source id, source type, timestamp, content type, branch/workspace, trust level,
  and schema tag.
- Provide UI and tests for:
  - manual text;
  - file input;
  - folder watcher metadata;
  - clipboard input;
  - generic REST/API fetch;
  - OpenAI-compatible mock and real path;
  - Ollama/local model mock and real path;
  - shell/CLI capture in mock-first mode.
- Keep preprocessing configurable and observable before Core LM ingestion.
- Complete outbound adapters for REST, OpenAI-compatible, local model, file,
  clipboard, shell, and programming-agent packet export.
- Extend prompt template support for markdown brief, JSON job spec, bug report,
  repo handoff, code review, implementation, and external coding-agent prompts.

## Phase 7 - Validation, Packaging, And Documentation

- Strengthen Python and frontend tests before final validation.
- Add integration tests for:
  `input -> compression -> Core LM -> ledger/provenance/replay/metrics -> chat -> outbound`.
- Run the required command set again and fix failures.
- Validate Windows package build locally if feasible; otherwise document the
  exact platform blocker with the command output and the remaining release step.
- Update README and `docs/corelm_studio/*` to match actual commands and
  behavior.
- Add sample workflows, connector configs, and sample outbound programming
  packets that exercise the delivered surfaces.

## Completion Criteria

- Desktop app launches.
- Python sidecar launches reliably.
- Text and file ingestion work.
- Mock OpenAI-compatible and mock local-model connectors work end to end.
- Preprocessing/compression is visible and happens before Core LM ingestion.
- Canonical state, ledger entries, provenance, replay, and metrics are visible.
- Chat receives Core LM outputs and outbound delivery receipts.
- At least one chat message routes to a programming-agent packet target.
- Python tests, frontend tests, desktop build, and feasible packaging checks pass
  or have a precise documented platform blocker.
