# Connectors

## Inbound Contract

Every inbound connector returns:

```json
{
  "raw_payload": "text or serialized payload",
  "normalized_payload": "cleaned deterministic payload passed toward preprocessing",
  "metadata": {
    "source_id": "stable source id",
    "source_type": "manual_text",
    "timestamp": "ISO-8601",
    "content_type": "text/plain",
    "branch": "corelm",
    "workspace": "default",
    "trust_level": "medium",
    "schema_tag": "optional"
  }
}
```

`raw_payload` remains inspectable as external input. `normalized_payload` is the
connector-level deterministic normalization result and still is not canonical
truth. Durable state changes must use `/api/connectors/run-ingest` or
`/api/ingest`, both of which pass through preprocessing and `CoreLMProduct`.

Supported inbound connector types:

- `openai_compatible_llm`
- `ollama_local_model`
- `file_input`
- `folder_watcher`
- `generic_web_api_fetch`
- `clipboard_input`
- `generic_rest_input`
- `manual_text`
- `shell_cli_capture`

## Outbound Adapters

Supported outbound target types:

- `generic_http_rest`
- `openai_compatible_outbound`
- `local_model_outbound`
- `file_export`
- `clipboard_export`
- `shell_cli_handoff`
- `programming_agent_packet`

Mocks are enabled by default for network/model adapters so demos and tests stay
deterministic. Real API keys should be supplied through environment variables or
OS secure storage integration, not workflow JSON.

## Useful API Routes

- `GET /api/connectors/catalog` returns UI-ready inbound and outbound capability
  metadata.
- `POST /api/connectors/run` executes a connector and returns raw plus
  normalized payloads without committing state.
- `POST /api/connectors/run-ingest` executes a connector and then commits the
  normalized payload through the canonical Core LM ingestion path.
- `POST /api/chat/{message_id}/route` routes a chat message to an outbound
  target and records a delivery receipt in the global chat.
