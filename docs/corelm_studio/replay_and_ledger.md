# Replay And Ledger

Core LM Studio mirrors the existing Core LM append-only ledger into SQLite while
preserving the Python reference kernel as the canonical authority.

## Ledger

Each Core LM ingestion creates a reference kernel ledger entry containing:

- ledger entry id;
- source event id;
- branch;
- raw canonicalized text;
- admitted, deduped, and rejected claims;
- numeric state norm;
- energy, CSI, and energy drift;
- invariant violations.

## Provenance

Structured claims include source event id and source text. The sidecar exposes
`/api/provenance` for value, provenance, and supersession inspection.

## Replay

The sidecar calls `CoreLMProduct.replay_verify()` after ingestion and stores a
replay snapshot. A replay is consistent when the replay digest matches the
current digest.
