# Core LM Studio Repository Guidance

This repository is being extended from the Core LM full-spectrum research kit into
Core LM Studio, a local-first Windows desktop application.

## Product Boundary

- Core LM is the canonical state authority.
- External LLMs, files, APIs, clipboard, shell output, and local models are
  perturbation/input sources or outbound targets. They are not truth holders.
- The global chat timeline is an interaction and routing bus. It never owns
  canonical truth.
- Durable state changes must flow through normalization, compression,
  Core LM ingestion, invariant checks, ledger commit, provenance, and metrics.
- No connector may directly mutate canonical state.

## Architecture

- Desktop shell: Electron + React + TypeScript in `apps/desktop`.
- Core sidecar: Python 3.11+ FastAPI-compatible local service in
  `services/core_service`.
- Shared contracts and TypeScript helpers live under `packages`.
- Local persistence uses SQLite through the sidecar service.
- Existing `corelm/` reference code is canonical and should be wrapped, not
  reimplemented or ported, unless there is a documented blocker.

## Implementation Rules

- Preserve append-only ledger behavior, provenance, branch isolation,
  contradiction/supersession semantics, deterministic replay where possible,
  bounded source mixing, and invariant reporting.
- Prefer deterministic mocks for demos and tests over brittle network
  dependencies.
- Keep secrets out of chat messages, logs, exports, crash reports, workflow JSON,
  and ledger metadata. Store only secret metadata in normal SQLite tables.
- Use sample placeholder configs for external services.
- Keep the application offline-capable except when a workflow explicitly uses a
  network connector.

## UI Direction

- Console Mode is the default. It should use an original dark, tactile,
  calculator-inspired composition with a large canonical readout, a central Core
  LM state widget, and large rounded controls.
- Flow Studio Mode should provide a drag-and-drop node canvas, edge routing,
  inspector, execution trace, save/load, clone, import/export, and test run.
- The Core LM state, branch, health, replay, ledger, and provenance affordances
  must be visible and reachable from the main product surface.

## Quality Bar

- Add focused Python tests for service contracts, connector contracts,
  compression/formatters, workflow execution, ledger/replay, and outbound mocks.
- Add frontend tests or smoke checks for app boot surfaces and workflow/chat
  behavior where feasible.
- Keep scripts and docs runnable from a clean checkout.
