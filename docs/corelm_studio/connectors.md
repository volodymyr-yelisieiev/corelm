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
    "schema_tag": "optional",
    "provider_metrics": "optional provider/native + local timing packet"
  }
}
```

`raw_payload` remains inspectable as external input. `normalized_payload` is the
connector-level deterministic normalization result and still is not canonical
truth. Durable state changes must use `/api/connectors/run-ingest` or
`/api/ingest`, both of which pass through preprocessing and `CoreLMProduct`.

Supported inbound connector types:

- `openai_compatible_llm`
- `lm_studio`
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

`lm_studio` is an OpenAI-compatible local adapter preset. It defaults to
`http://127.0.0.1:1234/v1`, runs with `mock=false`, and does not require an API
key for localhost endpoints.

## Ollama Sampling And Metrics

`ollama_local_model` accepts typed runtime controls:

- connection and prompt: `base_url`, `model`, `system`, `prompt`, `format`,
  `raw`, `stream`, `keep_alive`;
- sampling/runtime options: `seed`, `temperature`, `top_p`, `top_k`, `min_p`,
  `repeat_penalty`, `repeat_last_n`, `num_ctx`, `num_predict`, `stop`.

The connector sends Ollama runtime options under the provider `options` object
and records warnings for unsupported fields instead of silently dropping them.
Deterministic benchmark mode requires `seed`, forces `stream=false`, and sends
explicit temperature/top-p/top-k/num-predict settings.

For non-streaming Ollama responses, the sidecar stores provider-native usage
fields when present: `total_duration`, `load_duration`, `prompt_eval_count`,
`prompt_eval_duration`, `eval_count`, `eval_duration`, `done_reason`, `model`,
and `created_at`. Derived latency and throughput metrics are nullable; missing
provider fields stay `null` with `provider_metrics_available=false`.

## Managed Local Runtime

The desktop app starts the Python sidecar automatically. For real local model
runs, the sidecar can also ensure an Ollama server is available before the
connector call:

- `GET /api/local-runtimes?provider=ollama&base_url=http://127.0.0.1:11434`
  reports health, managed/adopted state, detected command, and last error.
- `POST /api/local-runtimes/ollama/ensure` starts `ollama serve` when the target
  URL is loopback, the server is not already healthy, and the `ollama` binary is
  available through `OLLAMA_BIN`, `ollama_bin`, `runtime_command`, or `PATH`.
- `ollama_local_model` and `local_model_outbound` use `auto_start=true` by
  default. Set `auto_start=false` for tests or for externally managed runtimes.
- Remote base URLs are never auto-started.

This does not download Ollama, pull model weights, or bundle a model server.
Real local Ollama calls still require an installed Ollama binary and an
available model. If another Ollama server is already running, Core LM Studio
adopts it instead of owning the process.

LM Studio endpoints are probed and can be adopted when already healthy, but the
sidecar does not launch the LM Studio GUI or enable its server. Treat LM Studio
as externally managed until a stable app launch contract is added.

## Useful API Routes

- `GET /api/connectors/catalog` returns UI-ready inbound and outbound capability
  metadata.
- `POST /api/connectors/run` executes a connector and returns raw plus
  normalized payloads without committing state.
- `POST /api/connectors/run-ingest` executes a connector and then commits the
  normalized payload through the canonical Core LM ingestion path.
- `GET /api/metrics` includes provider latency, token count, throughput,
  compression, and quality summary fields for ingested runs.
- `GET /api/quality` lists persisted quality evaluation packets.
- `GET /api/compression?target_type=...&target_id=...` returns persisted
  compression packets for chat messages, ledger entries, and workflow runs.
- `GET /api/local-runtimes` reports managed/adopted local model runtime health.
- `POST /api/local-runtimes/{provider}/ensure` starts or adopts a supported
  loopback runtime.
- `POST /api/chat/{message_id}/route` routes a chat message to an outbound
  target and records a delivery receipt in the global chat.
