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
