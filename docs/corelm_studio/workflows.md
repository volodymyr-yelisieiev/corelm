# Workflows

Flow Studio workflows are JSON documents with nodes and directed edges.

```json
{
  "id": "canonical-core-flow",
  "name": "Canonical Core Flow",
  "nodes": [
    { "id": "manual", "type": "manual_text_input", "position": { "x": 48, "y": 96 }, "config": {} },
    { "id": "core", "type": "core_lm", "position": { "x": 300, "y": 96 }, "config": {} }
  ],
  "edges": [
    { "id": "e1", "source": "manual", "target": "core" }
  ]
}
```

Supported node families:

- Input: manual text, OpenAI-compatible LLM, Ollama/local model, file, folder,
  web/API fetch, clipboard, REST, shell capture.
- Compression: cleaning, chunking, dedupe, summarization, schema extraction,
  key-value extraction, canonicalization, hash compression, state digest, and
  contradiction tagging.
- Core: `core_lm`.
- Output: formatting, chat, outbound prompt, file export, clipboard export.

Sample workflows live in `sample_workflows/`.

Workflow runs are persisted in SQLite and exposed at
`GET /api/workflows/runs?session_id=default`. Each run stores status, trace
events, node outputs, final output, and a run id. Flow Studio uses this history
for execution inspection.

Connector nodes preserve provider metrics in trace events and node outputs when
the provider returns them. `core_lm` nodes pass upstream provider metrics into
the canonical ingest path so ledger metadata, chat metadata, and metrics history
retain the same packet.

Each workflow run also receives a structural quality evaluation packet. The
workflow-level checks cover node success/failure counts, final output
availability, outbound delivery failures, and pipeline completeness. Node-level
ingest quality packets remain attached to their Core LM events.

Compression metadata from compression nodes and Core LM ingestion is inspectable
from Flow Studio run details and through:

```text
GET /api/compression?session_id=default&target_type=workflow_run&target_id=<run_id>
```

Current samples:

- `sample_workflows/canonical_core_flow.json`
- `sample_workflows/mock_llm_to_chat.json`
- `sample_workflows/mock_local_model_to_packet.json`
- `sample_workflows/file_ingest_to_replay.json`
