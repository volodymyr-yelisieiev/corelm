# Core LM Developer Handoff Packet

## Canonical Output
workflow.kind = deterministic local Core LM flow

## Provenance Metadata
```json
{
  "branch": "corelm",
  "ledger_entry_id": "l2",
  "source_type": "ollama_local_model"
}
```

## Handling Rules
- Preserve branch isolation.
- Route durable changes back through Core LM ingestion.
- Do not treat chat text as canonical state.

## Requested Output
Implement the change, preserve existing architecture, and include verification evidence.
