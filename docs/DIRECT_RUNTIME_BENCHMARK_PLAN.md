# Direct Runtime Benchmark Plan

## Audit Summary

Core LM Studio already has the right canonical mutation path in the Python
sidecar: input is normalized and compressed, ingested through `CoreLMProduct`,
checked by replay, mirrored to the append-only ledger tables, persisted as
metrics, and projected to chat. Existing connector execution is intentionally
separate from canonical state mutation unless it calls the ingest path.

The direct-runtime benchmark build extends that structure with a benchmark
orchestration layer. Runtime adapters produce perturbation text and trace data;
they never write canonical state. `StudioCore.ingest` remains the only durable
state mutation path used by benchmark trials.

## Implementation Shape

- `DirectRuntimeAdapter` defines load, warmup, generate, stream, unload, health,
  capability, and benchmark capability methods.
- `TransformersDirectAdapter` supports local Hugging Face/safetensors models
  when `transformers` and `torch` are installed.
- `LlamaCppDirectAdapter` supports local GGUF models when `llama-cpp-python` is
  installed.
- `deterministic_direct_smoke` is an in-process direct smoke adapter for local
  UI/API/CLI verification. It is explicitly non-strict and excluded from
  production strict claims.
- Benchmark profiles persist to SQLite and can run from API, CLI, and desktop.
- Benchmark runs persist manifests, trials, summaries, verdicts, report paths,
  adapter results, token traces, Core LM ingest links, metrics, and warnings.

## Canonical Trial Flow

1. Load direct runtime session.
2. Warm up the runtime.
3. Generate text and direct trace data.
4. Build a runtime source packet with token trace, sampler config, telemetry,
   model metadata, warnings, and benchmark ids.
5. Call `StudioCore.ingest`.
6. Persist ledger, replay, provenance, quality, compression, and metrics through
   the existing Core LM path.
7. Persist benchmark trial and summary.
8. Export JSON, Markdown, and CSV reports.

## Strict Completion Boundary

Strict direct benchmark results require a direct adapter, explicit model
reference, explicit seed, persisted sampler config, token trace, replay,
compression, state metrics, and policy eligibility. Bridge/API connectors and
the deterministic smoke adapter can run product smoke profiles, but their
results are non-strict.

## Verification

The build is verified with Python service tests, direct benchmark CLI smoke,
desktop tests, desktop build, and Windows packaging where feasible. If optional
runtime dependencies or local model weights are missing, strict live adapter
runs are classified as blocked; no placeholder strict scores are generated.
