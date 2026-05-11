# Core LM Studio Architecture Decisions

## ADR-001: Wrap the Python Reference Kernel

Decision: Core LM Studio wraps `CoreLMProduct` and `ReferenceKernel` in a Python
sidecar instead of porting the algorithm to TypeScript.

Reason: The existing Python code is the verified reference implementation and
already provides ledger, provenance, replay, branch isolation, supersession, and
numeric state metrics.

## ADR-002: Sidecar Owns Durable State

Decision: The Python sidecar owns SQLite persistence, Core LM sessions,
workflows, chat bus records, ledger mirrors, replay snapshots, and metrics.

Reason: This keeps canonical state transitions in one process and prevents UI or
connector code from bypassing Core LM invariants.

## ADR-003: Chat Is an Output Bus, Not Truth

Decision: Global chat messages persist rendered outputs, receipts, errors, and
user interactions, but canonical facts live only in Core LM state and ledger.

Reason: This preserves the Core LM principle that generated text and transport
messages are not truth holders.

## ADR-004: Connector Contract Is Payload Plus Metadata

Decision: All inbound connectors return `{raw_payload, metadata}`. Metadata must
include source id, source type, timestamp, content type, branch/workspace, trust
level, and optional schema tag.

Reason: Provenance and trust must survive normalization and compression.

## ADR-005: Deterministic Mocks Are First-Class

Decision: External LLM, local model, REST, shell, and outbound adapters include
mock modes that are used by tests and sample workflows.

Reason: The application must be demonstrable offline and tests must remain
deterministic.

## ADR-006: SQLite Uses Append-Friendly Tables

Decision: `ledger_entries`, `chat_messages`, `metrics`, and `replay_snapshots`
are append-oriented tables. Mutable workflow definitions and connector configs
are versionable JSON records.

Reason: Auditability and replay diagnostics are more important than compact
storage for this local single-user product.

## ADR-007: Electron Starts the Service in Development and Packaged Builds

Decision: Electron main process starts the sidecar with a module command by
default and supports override through `CORELM_STUDIO_SERVICE_CMD`.

Reason: Developers can run from source, while packaged Windows builds can point
to a bundled Python executable or service launcher without changing UI code.

## ADR-008: UI Is Original but Calculator-Inspired

Decision: Console Mode uses a dark, high-contrast, tactile layout with a large
readout, a central Core LM status orb, and large rounded controls without
copying Apple assets, colors, typography, or branding.

Reason: The product goal asks for calculator-like interaction principles, not a
clone of any proprietary interface.
