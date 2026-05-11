# Architecture

Core LM Studio keeps the verified Python Core LM reference implementation at the
center of the product.

## Process Model

- Electron main process starts the Python sidecar.
- React renderer talks to the sidecar over localhost HTTP.
- The sidecar owns Core LM sessions, SQLite, workflow execution, connectors,
  chat bus persistence, ledger mirrors, replay snapshots, and metrics.

## Main Packages

- `corelm/`: existing reference kernel, product wrapper, schemas, benchmarks.
- `services/core_service/corelm_studio/`: FastAPI sidecar, SQLite store,
  connectors, compression, workflow execution, outbound routing.
- `apps/desktop/`: Electron + React + TypeScript desktop shell.
- `packages/shared`: shared TypeScript contracts.
- `packages/connectors`: connector contract types.
- `packages/workflow_engine`: workflow contract types.
- `packages/ui`: shared UI theme constants.

## Canonical Dataflow

Inbound source -> normalization -> compression -> Core LM ingestion -> state
update -> ledger/provenance/metrics -> formatting -> global chat bus -> outbound
adapter.

Connectors never mutate canonical state directly. Durable state changes go
through Core LM ingestion and invariant checks.
