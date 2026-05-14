# Metrics

Core LM Studio stores run metrics in SQLite and exposes them through
`GET /api/metrics?session_id=default`.

Provider-native Ollama fields are captured from non-streaming `/api/generate`
responses when present:

- `total_duration`
- `load_duration`
- `prompt_eval_count`
- `prompt_eval_duration`
- `eval_count`
- `eval_duration`
- `done_reason`
- `model`
- `created_at`

Locally instrumented fields:

- `request_start_ns`
- `request_end_ns`
- `local_wall_time_ms`
- `time_to_first_byte_ms` when streaming makes it feasible

Derived fields are nullable and include provider latency, load latency, prompt
tokens, completion tokens, total tokens, prompt tokens/sec, generation
tokens/sec, provider end-to-end tokens/sec, and local end-to-end tokens/sec when
provider duration is unavailable.

No metric is fabricated. Missing provider fields remain `null`, and the packet
sets `provider_metrics_available=false`.

Deterministic benchmark mode for Ollama requires `seed`, forces `stream=false`,
and sends explicit `temperature`, `top_p`, `top_k`, and `num_predict` values.

## Direct Runtime Benchmark Metrics

Direct benchmark runs add adapter/runtime/model metadata, token traces,
sampler config, determinism scores, real compression metrics, Core LM state
metrics, profile verdicts, and report export status. The full catalog is in
`docs/METRIC_CATALOG.md`.

Strict direct results only come from direct adapters that pass
`docs/STRICT_BENCHMARK_POLICY.md`. Ollama, LM Studio, and other provider-style
HTTP connectors remain bridge mode and are labeled non-strict.
