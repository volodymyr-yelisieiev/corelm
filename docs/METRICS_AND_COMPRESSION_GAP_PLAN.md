# Metrics And Compression Gap Plan

## Audit Summary

Core LM Studio already has the right high-level boundary:

- `services/core_service/corelm_studio/studio_core.py` keeps Core LM as the canonical state authority and records chat, ledger mirrors, replay snapshots, metrics, and compression metadata only after ingestion.
- `services/core_service/corelm_studio/connectors.py` separates connector runs from canonical ingestion. `/api/connectors/run` does not commit state; `/api/connectors/run-ingest` runs the connector and then calls the Core LM ingestion path.
- `services/core_service/corelm_studio/compression.py` has a deterministic preprocessing pipeline with sanitize, clean, dedupe, canonicalize, schema extraction, hash compression, contradiction tagging, digest, annotations, and compression ratio.
- `services/core_service/corelm_studio/workflow.py` runs input, compression, Core LM, chat, and outbound nodes and persists workflow traces through `StudioDB.record_workflow_run`.
- `services/core_service/corelm_studio/db.py` persists sessions, connectors, chat messages, ledger mirrors, replay snapshots, metrics, workflow definitions, workflow runs, settings, and secret metadata in SQLite.
- `apps/desktop/src/App.tsx` already has Console mode, Flow Studio mode, history, connector controls, settings, compression preview, workflow run history, and basic metrics display.
- Tests in `tests/core_service/test_studio_service.py` and `apps/desktop/tests/app.test.tsx` already cover ingestion, connector mocks, workflow persistence, secret redaction, compression preview, and desktop smoke behavior.

The referenced local Ollama validation plan confirms the current system can validate connectivity, canonical ingest, replay, workflow plumbing, and outbound packet preparation, but not provider performance or real quality evaluation yet.

## Placeholder Or Incomplete Areas

- Ollama metrics are discarded in `services/core_service/corelm_studio/connectors.py`. The non-streaming `/api/generate` response is reduced to `body["response"]`, so `total_duration`, `load_duration`, token counts, token durations, `done_reason`, `model`, and `created_at` do not survive connector, workflow, chat, ledger, or metrics history paths.
- Local request timing is not captured for connector calls. There is no `request_start_ns`, `request_end_ns`, `local_wall_time_ms`, or provider availability flag.
- Token throughput metrics do not exist. `services/core_service/corelm_studio/studio_core.py` only records Core LM state metrics plus `compression_ratio_proxy`.
- `quality_score` in `services/core_service/corelm_studio/studio_core.py` is a fake hard-coded `0.5` and must be replaced by a real evaluator packet.
- Ollama sampling controls are not typed or validated. The current connector only sends `model`, `prompt`, and `stream: false`.
- The desktop connector UI has no full Ollama settings drawer, advanced sampling controls, deterministic benchmark preset, save-as-profile flow, or non-default sampling badge.
- Compression metadata exists after ingest, but the UI mostly exposes a preview-only panel. It does not open authoritative compression packets from history, workflow runs, ledger entries, or chat messages, and does not support compare.
- There are no dedicated `/api/quality` or `/api/compression` lookup endpoints by run/message/ledger entry.
- Workflow runs persist trace and outputs only. They do not persist top-level provider metrics, compression packets, or quality summaries in query-friendly fields.

## Exact Files To Modify

Backend:

- `services/core_service/corelm_studio/connectors.py`
- `services/core_service/corelm_studio/metrics.py` (new)
- `services/core_service/corelm_studio/quality.py` (new)
- `services/core_service/corelm_studio/compression.py`
- `services/core_service/corelm_studio/studio_core.py`
- `services/core_service/corelm_studio/workflow.py`
- `services/core_service/corelm_studio/db.py`
- `services/core_service/corelm_studio/app.py`
- `services/core_service/corelm_studio/schemas.py`
- `packages/shared/index.ts`
- `packages/connectors/index.ts`

Desktop:

- `apps/desktop/src/types.ts`
- `apps/desktop/src/api.ts`
- `apps/desktop/src/App.tsx`
- `apps/desktop/src/styles.css`
- `apps/desktop/tests/app.test.tsx`

Tests:

- `tests/core_service/test_studio_service.py`

Docs:

- `README.md`
- `docs/corelm_studio/connectors.md`
- `docs/corelm_studio/workflows.md`
- `docs/METRICS.md` (new)
- `docs/COMPRESSION_INSPECTOR.md` (new)
- `docs/QUALITY_EVAL.md` (new)

## Acceptance Criteria

### Gap 1: Provider Latency Metrics

- Ollama non-streaming connector runs capture provider-native usage fields when present: `total_duration`, `load_duration`, `prompt_eval_count`, `prompt_eval_duration`, `eval_count`, `eval_duration`, `done_reason`, `model`, and `created_at`.
- Connector metadata stores a structured `provider_metrics` packet with raw usage, native metrics, local timings, derived nullable metrics, and per-metric source labels.
- Missing provider metrics are stored as `null` with `provider_metrics_available=false`; no heuristic provider-native values are fabricated.
- Divide-by-zero returns `null`.
- Metrics propagate into connector run result, workflow trace/output, chat metadata, ledger metadata for ingested runs, and `/api/metrics`.
- `/api/metrics` exposes provider latency, load latency, token counts, and tokens/sec fields where available.

### Gap 2: Ollama Sampling Controls

- Ollama connector config validates `base_url`, `model`, `system`, `prompt`, `format`, `raw`, `stream`, `keep_alive`, `seed`, `temperature`, `top_p`, `top_k`, `min_p`, `repeat_penalty`, `repeat_last_n`, `num_ctx`, `num_predict`, and `stop`.
- Only Ollama-supported fields are sent to `/api/generate`; unsupported user-configured fields produce warnings in metadata.
- Deterministic benchmark mode applies `stream=false`, requires a seed, and sends explicit `temperature`, `top_p`, `top_k`, and `num_predict`.
- Desktop connector controls expose basic and advanced Ollama sampling fields, reset defaults, save connector profile, and show a non-default sampling badge.

### Gap 3: Real Quality Eval Layer

- `quality_score: 0.5` is removed from the main path.
- A real evaluator returns a versioned packet with summary score, per-check booleans, numeric values, and mode-specific details.
- General text eval supports nonempty output, output length, repetition ratio, contradiction flag count, format compliance, keyword coverage, exact match, normalized/fuzzy match, and unsafe/invalid placeholder hook.
- Structured eval supports parse validity, schema validity for simple provided schemas, required key coverage, field completeness, and formatting compliance.
- Compression-aware eval supports compression ratio, duplicate line reduction, canonicalization applied, contradiction candidates found, and raw-vs-canonical diff size.
- Workflow eval supports node success/failure counts, final output availability, outbound delivery status, and pipeline completeness.
- When no reference is supplied, only structural/process quality is reported.
- Evaluation packets persist per run, are reachable through API, and are visible in the desktop UI.

### Gap 4: Compression Inspector UI

- Desktop has a real Compression Inspector that can render authoritative metadata from preview, chat messages, ledger entries, workflow traces, and workflow outputs.
- The inspector shows raw input, sanitized text, cleaned text, deduped text, canonical text, digest/hash, steps, annotations, contradiction candidates, structured extraction, compression ratio, raw/canonical lengths, and token proxy before/after when available.
- The inspector includes split raw-to-canonical view, pipeline panel, diff view, copy buttons, long-payload expand/collapse, badges, and a clear unavailable state.
- Clicking history items, ledger entries, workflow runs, or chat messages with compression metadata opens the inspector for that exact item.
- Quick compare between two compression packets is available.

### Gap 5: Metrics In UI

- Console mode shows minimal pills/cards for provider latency, load latency, prompt/completion/total tokens, generation/prompt/end-to-end tokens/sec, compression ratio, quality summary, and provider metrics availability.
- Flow Studio run details show per-node provider metrics, per-run quality summary, compression inspector entry points, and raw/canonical preview entry points.
- History/inspection views show provider metrics, quality eval, compression, provenance, ledger, and replay links without cluttering the calculator-style main surface.

## Verification Plan

- Run focused Python tests for Ollama metrics parsing, safe derived metrics, missing metrics, zero durations, sampling validation, connector-to-ingest propagation, quality checks, and compression packet lookup.
- Run desktop tests for Compression Inspector rendering/opening, metrics cards, sampling controls persistence, and deterministic benchmark preset.
- Run the existing service and desktop smoke suites after implementation:
  - `PYTHONPATH=. .venv/bin/python -m pytest -q tests/core_service`
  - `npm run desktop:test`

## Implementation Status

Status as of 2026-05-13:

- Ollama non-streaming provider usage is captured in
  `services/core_service/corelm_studio/metrics.py` and attached to connector,
  workflow, ledger, chat, and metric-history metadata.
- Provider-native and local-derived metrics are nullable and source-labelled.
  Missing provider fields stay unavailable instead of being fabricated.
- Ollama sampling controls are typed and validated in the connector path, and
  the desktop connector drawer exposes benchmark defaults, advanced controls,
  reset, profile save, and non-default sampling state.
- The fake `quality_score = 0.5` main-path placeholder has been replaced by
  versioned structural/process quality packets in
  `services/core_service/corelm_studio/quality.py`.
- Compression packets now persist intermediate stages and are inspectable from
  Console, History, ledger/chat details, and Flow Studio run details.
- Metrics and quality summaries are visible in Console, History, and workflow
  trace details.
- The follow-up verification pass added sidecar-managed Ollama runtime probing
  and on-demand `ollama serve` startup through `/api/local-runtimes`.

Verified commands:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q
npm run desktop:test
npm run desktop:build
```

Remaining limitations:

- Live Ollama/model execution was not performed in this repository run; tests
  use deterministic provider mocks and runtime probes.
- LM Studio remains externally managed.
- Core LM Studio does not download model binaries or model weights.
- The desktop implementation still needs component extraction after this
  feature pass because `apps/desktop/src/App.tsx` is too large.
