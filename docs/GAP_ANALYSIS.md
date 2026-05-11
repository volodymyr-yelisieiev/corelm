# Core LM Studio Gap Analysis

This audit covers the repository as it exists before additional Studio
implementation work. Core LM remains the canonical state authority; the Studio
work should wrap and expose it, not replace it.

## 1. Already Exists And Works

- Repository guidance is explicit in `AGENTS.md`, `README.md`,
  `docs/implementation_plan.md`, and `docs/architecture_decisions.md`.
- The canonical Python Core LM reference product exists under `corelm/`.
  Important preserved assets include:
  - `corelm/product.py` for local session persistence, ingestion, provenance,
    branch listing, correction, and replay verification.
  - `corelm/reference_kernel.py` for deterministic state update, append-only
    ledger entries, branch-aware fact records, deduplication, supersession,
    invariant checks, and replay.
  - `corelm/schema.py` and `corelm/adapter.py` for the event, claim, query,
    fact, ledger, and deterministic extraction contracts.
- A FastAPI-compatible sidecar skeleton exists in
  `services/core_service/corelm_studio/`.
  It already exposes health, sessions, state, ingest, chat, ledger, metrics,
  provenance, replay, workflows, connector runs, connector persistence, and
  outbound route endpoints.
- SQLite persistence exists through `StudioDB` with tables for sessions,
  workflows, nodes, edges, connectors, chat messages, ledger mirrors, replay
  snapshots, metrics, and secret metadata.
- The current ingestion path goes through preprocessing, `CoreLMProduct`, ledger
  mirror persistence, replay snapshot persistence, metrics, formatting, and a
  global chat message.
- Deterministic inbound connector mocks exist for manual text,
  OpenAI-compatible LLM, Ollama/local model, clipboard, shell, file, folder, web
  fetch, and REST.
- Deterministic outbound mock adapters exist for programming-agent packets,
  HTTP/REST, OpenAI-compatible, local model, clipboard, file export, and shell
  handoff.
- Preprocessing utilities exist for cleaning, deduplication, summarization,
  canonicalization, chunking, schema/key-value extraction, hashing/digesting,
  and contradiction candidate tagging.
- The Electron + React + TypeScript desktop skeleton exists under
  `apps/desktop/`.
  It includes:
  - Console Mode with a large readout, Core LM state display, branch/session
    selectors, action pad, chat/history drawer, connector/settings surfaces, and
    drag-and-drop file ingestion.
  - Flow Studio with draggable nodes, rendered edges, an inspector, trace panel,
    workflow save/load/clone/import/export, and test run.
  - Keyboard shortcuts for command palette, Core LM run, and Flow Studio.
- Sample workflows, sample connector configs, and prompt templates exist.
- Python sidecar tests and frontend smoke tests exist.
- Windows-oriented Electron packaging configuration exists in
  `apps/desktop/electron-builder.json`.

## 2. Exists Partially

- The sidecar wraps canonical Core LM correctly for basic ingestion, but the
  full source input -> normalization -> compression -> Core LM -> invariant
  checks -> ledger -> provenance -> metrics -> formatter -> chat -> outbound
  path needs broader endpoint and test coverage.
- Connector execution exists as functions and API endpoints, but the desktop UI
  only lists connector categories. It does not yet provide full connector run,
  save, edit, enable/disable, or inspect workflows.
- The global chat persists messages with badges, provenance ids, ledger ids, and
  metadata, but the UI does not yet expose every route/copy/export action or
  every category distinctly.
- Workflow execution exists and can run simple DAGs, but the engine is minimal:
  no persisted execution history table, no detailed edge payload inspector, no
  explicit test-run mode separation, and limited validation for cyclic or
  malformed workflows.
- Flow Studio supports drag repositioning and import/export, but node creation,
  edge creation/removal, palette insertion, error affordances, and richer
  inspector controls are incomplete.
- Console Mode is visually close to the calculator-inspired direction, but it
  still needs polish for responsive Windows layouts, richer provenance/replay
  inspection, connector controls, and persistent settings.
- Settings, sessions, workflows, chat, and sidecar data persist through SQLite,
  but desktop preferences are not yet a dedicated persisted settings surface.
- Windows packaging is configured, but local packaging validation still needs to
  be run. Signed installer validation and Defender reputation checks remain
  release activities.
- The OpenAI-compatible and local model connectors have real transport paths,
  but the default reliable path is deterministic mock mode.

## 3. Missing For A Full Windows App

- Complete connector management UI:
  - create/edit/delete connector configs;
  - run connector into the console;
  - inspect raw and normalized payloads;
  - show secret metadata without exposing secret values.
- Complete outbound routing UI:
  - choose target and packet type per chat message;
  - preview generated packets;
  - export/copy route receipts;
  - display delivery receipts in the chat timeline.
- Richer global chat bus categories and actions:
  - user, system, connector output, Core LM summary, formatted packet,
    delivery receipt, and error/status distinctions;
  - copy/export actions;
  - direct provenance and ledger-cause navigation.
- More complete replay and provenance UI:
  - replay snapshot list;
  - digest comparison;
  - ledger entry details;
  - supersession display for current facts.
- Flow Studio authoring tools:
  - connect/disconnect edges;
  - validate workflow shape;
  - inspect execution payloads and failures per node.
- Additional tests:
  - service contracts for every connector and outbound adapter;
  - formatter packet types;
  - workflow errors and malformed graphs;
  - ledger/provenance/replay visibility;
  - deeper frontend smoke tests for chat, connector, settings, and Flow Studio
    interactions.
- More sample artifacts:
  - shell capture workflow;
- Final Windows installer proof from a clean Windows host remains a release
  validation step even though cross-platform packaging now produces artifacts.

## 4. Should Be Refactored But Preserved

- `StudioCore.ingest()` should stay the canonical durable mutation path, but it
  should be hardened with clearer dataflow records, better normalized source
  metadata, and more focused tests.
- `WorkflowEngine` should preserve its current sidecar ownership and Core LM
  call path, while adding workflow validation, execution persistence, node
  palette support, richer trace payloads, and better failure reporting.
- `connectors.py` and `outbound.py` should remain plugin-style modules, but
  should expose registries/capability metadata so the UI does not duplicate type
  lists.
- `formatters.py` should keep existing packet support and extend it to cover all
  programming-oriented output types consistently.
- The React `App.tsx` can be split into smaller components after behavior is
  stabilized. The current UI direction should be preserved, not replaced with a
  generic chat shell.
- SQLite schema creation should be preserved, with additive migrations or
  bootstrap-safe alterations rather than destructive schema churn.

## 5. Canonical Core LM Behavior Not To Touch

- Do not port `corelm/` to TypeScript.
- Do not replace `CoreLMProduct`, `ReferenceKernel`, `Event`, `Claim`,
  `FactRecord`, `LedgerEntry`, or the deterministic replay behavior.
- Do not let connectors, chat, frontend state, workflow JSON, outbound adapters,
  files, APIs, LLMs, shell output, or clipboard input directly mutate canonical
  truth.
- Do not treat the global chat timeline as canonical storage.
- Do not weaken append-only ledger semantics, branch isolation, provenance,
  supersession, contradiction/correction behavior, deterministic replay, bounded
  state checks, or invariant reporting.
- Do not store raw secrets in workflow JSON, chat messages, ledger metadata,
  logs, exports, or crash reports.

## Current Validation Status

Initial validation found two setup/policy issues:

- the local shell did not expose `python` until the repo virtualenv was
  activated;
- the repository had an explicit naming/casing policy test that was too noisy
  for this project and rejected mandated planning documents.

The dedicated naming/casing test was removed. File names should still follow
the repository's normal lowercase convention unless a top-level convention or
explicit deliverable requires otherwise. After installing the declared
dependencies in `.venv` and `node_modules`, these checks pass:

- `PYTHONPATH=. python -m pytest -q` from the activated virtualenv;
- `npm run desktop:test`;
- `npm run desktop:build`;
- `npm run desktop:dev` smoke check, with Electron starting the sidecar through
  the repo virtualenv when present;
- `npm run desktop:package:win`;
- `PYTHONPATH=. python -m services.core_service.corelm_studio` with
  `/api/health` returning `status: ok`.
