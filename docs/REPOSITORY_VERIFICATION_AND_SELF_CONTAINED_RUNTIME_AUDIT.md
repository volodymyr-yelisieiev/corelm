# Repository Verification And Self-Contained Runtime Audit

Date: 2026-05-13

Scope:

- verify the current repository after the Ollama metrics / sampling / quality /
  Compression Inspector implementation;
- identify correctness, cleanup, standardization, and documentation gaps;
- define the next fixes needed to make Core LM Studio more self-contained,
  especially for local model serving;
- preserve the product boundary: Core LM remains canonical state authority,
  connectors remain perturbation/input sources, and chat remains a routing bus.

## Executive Summary

The latest metrics/compression task is materially implemented and verified by
tests. The sidecar now captures Ollama provider-native usage fields, computes
nullable latency and throughput metrics, persists quality evaluations, exposes
compression lookup APIs, and the desktop surfaces these details through Console,
History, Flow Studio, and a richer Compression Inspector.

Current green checks after the follow-up fix pass:

- `PYTHONPATH=. .venv/bin/python -m pytest -q` passed with 36 tests.
- `npm run desktop:test` passed with 9 tests.
- `npm run test:studio` passed.
- `npm run desktop:build` completed successfully.

Primary product gap addressed in this pass:

- The Electron app already started the Python Core LM sidecar. The sidecar now
  also probes and can start `ollama serve` on demand for loopback Ollama runs
  when the `ollama` binary is installed. This closes the first practical version
  of the "open only this app" behavior for Ollama.

Primary remaining cleanup gap:

- The desktop implementation is still concentrated in `apps/desktop/src/App.tsx`.
  This pass extracted defaults, shared UI helpers, and the Compression Inspector
  into separate files, but connector settings, history, and Flow Studio should
  still be split into focused components.

## Current Repository State

Uncommitted implementation files include:

- backend sidecar files under `services/core_service/corelm_studio/`;
- desktop files under `apps/desktop/src/`;
- shared contracts under `packages/`;
- service and desktop tests;
- new and updated docs.

This audit intentionally does not revert any existing changes. The current
working tree reflects the latest implementation work.

## Verification Of Latest Task

## Parallel Audit Findings To Fix In This Pass

Backend audit returned these high-priority issues:

- Workflow transform nodes drop connector provider metrics/sampling metadata
  before `core_lm` ingestion.
- Connector `secret_refs` can currently persist actual secret-looking strings
  as metadata.
- API and workflow exception strings are returned/stored without redaction.
- Chat message metadata points to the ledger quality row rather than the chat
  quality row.
- Quality is evaluated against pre-ingest raw text, while the canonical commit
  uses the preprocessed text.
- Secret redaction misses keys like `Authorization` and Basic auth values.
- Boolean parsing for `mock` and `deterministic_benchmark` treats string
  `"false"` as truthy in some paths.

Frontend audit returned these high-priority issues:

- Flow Studio compression inspection updates hidden Console drawer state and is
  not visible in Flow mode.
- Failed compression lookups can show stale preview data under a missing-target
  label.
- Console metrics can pair latest provider metrics with a different latest
  quality record.
- Compression Inspector still does some full-payload render-time work.
- Pipeline stages bypass truncation.
- Clickable cards need keyboard semantics.
- Dialog/tabs/status accessibility needs improvement.
- Ollama numeric controls need frontend constraints and safer parsing.
- Flow Studio lacks manual edge add/delete/reroute controls.

Self-contained runtime audit initially confirmed:

- The app manages only the Python Core LM sidecar.
- Ollama and LM Studio are assumed to be already-running services.
- A sidecar-owned runtime supervisor is the correct integration point because
  direct connector runs, run-ingest, workflows, and outbound routing all pass
  through the sidecar.

Follow-up fixes implemented:

- Added `services/core_service/corelm_studio/local_runtime.py` for runtime
  probing, owned process start/stop, and sanitized status reporting.
- Added `GET /api/local-runtimes` and
  `POST /api/local-runtimes/{provider}/ensure`.
- Wired Ollama connector and local-model outbound paths to auto-start the
  loopback runtime by default unless `auto_start=false`.
- Added desktop runtime status and a `Start Local Server` action in the Ollama
  connector settings.
- Fixed metadata propagation, redaction, boolean parsing, quality attachment,
  Flow Studio compression inspection, stale compression preview behavior,
  keyboard accessibility for clickable history cards, numeric sampling input
  constraints, and manual Flow Studio edge add/delete controls.

### Ollama Provider Metrics

Implemented:

- `services/core_service/corelm_studio/metrics.py` captures provider-native
  Ollama fields and computes nullable derived metrics.
- `services/core_service/corelm_studio/connectors.py` stores provider metrics in
  connector metadata for `ollama_local_model`.
- `services/core_service/corelm_studio/studio_core.py` flattens provider metrics
  into persisted metric records and keeps the structured packet in ledger and
  chat metadata.
- `services/core_service/corelm_studio/workflow.py` propagates upstream connector
  provider metrics into `core_lm` ingestion.

Verified:

- Provider fields are parsed from mocked non-streaming Ollama responses.
- Missing metrics produce `provider_metrics_available=false`.
- Zero durations produce nullable TPS instead of divide-by-zero.
- Metrics survive connector -> ingest -> ledger -> chat -> `/api/metrics`.

Risks:

- Live Ollama was not exercised in this environment. Tests use deterministic
  mocks.
- Streaming TTFB is best-effort only. Non-streaming benchmark mode remains the
  authoritative path for provider-native usage.

### Ollama Sampling Controls

Implemented:

- `build_ollama_generate_payload()` validates and sends supported fields:
  `base_url`, `model`, `system`, `prompt`, `format`, `raw`, `stream`,
  `keep_alive`, `seed`, `temperature`, `top_p`, `top_k`, `min_p`,
  `repeat_penalty`, `repeat_last_n`, `num_ctx`, `num_predict`, and `stop`.
- Unsupported config fields become warnings in metadata.
- Deterministic benchmark mode requires `seed`, forces `stream=false`, and sets
  explicit runtime options.
- Desktop connector UI exposes Ollama settings and advanced sampling controls.

Verified:

- Sampling payload shape is tested.
- Invalid deterministic benchmark mode without seed is tested.
- Range validation is tested.
- Desktop benchmark preset behavior is tested.

Risks:

- The desktop stores numeric inputs as numbers, but empty inputs become empty
  strings in local state. The backend tolerates this for optional fields.
- `think` / reasoning toggles are intentionally not sent because the current
  provider path does not enable them.

### Quality Evaluation

Implemented:

- `services/core_service/corelm_studio/quality.py` produces `quality_eval.v1`
  packets.
- Fake `quality_score = 0.5` was removed from the main path.
- Structural/process checks now feed `quality_score` / `quality_summary_score`.
- Quality packets persist in `quality_evaluations` and are exposed by
  `GET /api/quality`.
- Ingested quality packets are attached to ledger metadata, chat metadata, and
  metric history.
- Workflow-level quality packets are recorded for workflow runs.

Verified:

- Exact match, keyword coverage, JSON parse validity, schema validity, required
  key coverage, and end-to-end persistence are tested.

Risks:

- This is structural/process quality, not semantic truth. The docs correctly say
  the evaluator does not claim semantic truth without a reference.
- Schema validation is intentionally lightweight and should not be presented as
  full JSON Schema conformance.

### Compression Inspector

Implemented:

- Compression packets now include intermediate fields: sanitized, cleaned,
  deduped, canonicalized, structured extraction, lengths, and token proxies.
- `GET /api/compression` returns packets for chat messages, ledger entries, and
  workflow runs.
- Desktop Compression Inspector shows metrics, pipeline stages, diff, copy
  actions, contradiction markers, annotations, and compare.
- History items, ledger entries, chat messages, and workflow traces can open the
  inspector when metadata exists.

Verified:

- Compression preview and inspector rendering are covered by desktop tests.
- Compression packet lookup is covered by service tests.

Risks:

- Large-payload performance is improved by truncating the rendered diff unless
  expanded, but the diff itself is still line-index based rather than a proper
  minimal diff algorithm.
- Ledger metadata intentionally redacts pre-commit raw text, so ledger inspector
  views cannot always show the exact original raw payload. Chat and preview
  packets retain sanitized raw text.

### UI Metrics Surfacing

Implemented:

- Console mode has metrics pills for provider availability, latency, load,
  tokens, generation TPS, prompt TPS, end-to-end TPS, compression, and quality.
- History adds provider metrics and quality evaluation sections.
- Flow Studio trace details show provider metrics and compression entry points
  where relevant.

Verified:

- Desktop tests assert metrics cards, provider availability, and quality summary.

Risks:

- The current Console metrics strip is dense. It stays inside the dark
  calculator visual system, but a future UI refactor should isolate it into a
  dedicated component and add tooltips.

## Self-Contained Runtime Gap

Desired product behavior:

- The user opens Core LM Studio.
- The app starts the Python sidecar.
- The app ensures a local model runtime is available when a real local model run
  is requested.
- The user does not need to manually keep Ollama or LM Studio open.

Behavior before this pass:

- `apps/desktop/electron/main.ts` starts and stops the Python sidecar.
- `services/core_service/corelm_studio/connectors.py` calls Ollama
  `POST /api/generate` when `mock=false`.
- If Ollama is not already serving at `http://127.0.0.1:11434`, the connector
  fails.
- LM Studio is treated as an OpenAI-compatible endpoint, but the app does not
  launch LM Studio or its server.

Implemented target:

- Managed Ollama is supported first.
- The app does not bundle a model or server binary in this pass.
- The sidecar auto-detects `ollama` through `OLLAMA_BIN`, `ollama_bin`,
  `runtime_command`, or `PATH`.
- If `base_url` is loopback and not healthy, the sidecar starts `ollama serve`
  process from the sidecar.
- The sidecar waits for `/api/tags` health before connector execution.
- Runtime status is exposed through API and desktop UI.
- Remote URLs are never auto-started.
- LM Studio is documented as unmanaged until a safe app-specific launch strategy
  is added.

Remaining limitations:

- A clean machine still needs Ollama installed and a model pulled before real
  local model execution can succeed.
- Core LM Studio does not download binaries or weights automatically.
- LM Studio can be adopted when its server is already healthy, but it is not
  launched by Core LM Studio.
- Runtime API has no separate authentication token yet; it is bound to the same
  local sidecar trust model as the rest of the development API.

Previous target details retained for traceability:

- Support managed Ollama first.
- Do not bundle a model or server binary in this pass.
- Auto-detect `ollama` through `OLLAMA_BIN` or `PATH`.
- If `base_url` is local and not healthy, start `ollama serve` as a child
  process from the sidecar.
- Wait for `/api/tags` health before connector execution.
- Expose runtime status through API and desktop UI.
- Keep remote URLs opt-in and never attempt to start a local process for remote
  base URLs.
- Document LM Studio as unmanaged until a safe app-specific launch strategy is
  added.

Acceptance criteria for this runtime fix:

- `GET /api/local-runtimes` reports provider, base URL, health, binary
  discovery, managed process state, and last error.
- `POST /api/local-runtimes/{provider}/ensure` starts Ollama if the binary
  exists and the server is not already healthy.
- `ollama_local_model` with `mock=false` uses auto-start by default for local
  `base_url` unless `auto_start=false`.
- Desktop Connectors drawer shows local runtime status and has a start action.
- Tests cover healthy runtime, missing binary, auto-start path, and connector
  integration without launching a real server.

## Standardization And Cleanup Findings

### Docs

Issues:

- `docs/METRICS_AND_COMPRESSION_GAP_PLAN.md` was required as a pre-implementation
  gap plan. It still reads as a gap plan, not as a completed implementation
  report. It should remain for traceability but should gain a final status
  section.
- Root docs `docs/CONNECTORS.md` and `docs/WORKFLOWS.md` are wrappers around
  `docs/corelm_studio/...`. This satisfies the requested paths but introduces
  duplication risk.
- Quickstart currently says connector demo keeps mock mode enabled. It should
  mention managed Ollama once implemented.

Fix plan:

- Add final status notes to the gap plan.
- Keep root wrapper docs short and point to canonical docs.
- Add a dedicated managed runtime section to quickstart and connector docs.

### Backend

Issues:

- Runtime management is missing.
- `connectors.py` is growing into transport, validation, runtime, and metadata
  responsibilities. Ollama-specific code should eventually move into an adapter
  module.
- `db.py` uses additive schema creation but does not have named migrations.
  This remains acceptable for local-first SQLite but should be tracked.

Fix plan:

- Add `local_model_runtime.py` for runtime health/start/stop logic.
- Keep connector auto-start calls thin.
- Add tests around the manager and connector integration.

### Desktop

Issues:

- `App.tsx` has become a large all-in-one file. This is the biggest cleanup
  candidate after runtime behavior is correct.
- Compression Inspector and Connector Panel are good candidates for separate
  files.
- Sampling controls need better affordances, such as tooltips and disabled
  states when runtime is unavailable.

Fix plan:

- For this pass, add runtime status and start action in the existing connector
  panel to keep the change focused.
- In a later pass, split `App.tsx` into components:
  `MetricsStrip`, `HistoryPanel`, `CompressionPanel`, `ConnectorPanel`,
  `FlowStudio`, and shared helpers.

### Packaging / Windows

Issues:

- Python sidecar packaging exists through embedded Python.
- Ollama itself is not bundled.
- The app cannot guarantee model availability on a clean machine.

Fix plan:

- Managed Ollama auto-start if installed.
- Clear UI state if missing.
- Document installation as a prerequisite for real local model runs until a
  bundled runtime decision is made.

## Work Plan From This Audit

Phase 1:

- Add managed local model runtime service for Ollama.
- Add runtime API endpoints.
- Wire connector auto-start.
- Add desktop runtime status and start button.
- Add tests and docs.

Phase 2:

- Re-run full Python, desktop test, and desktop build suites. Completed.
- Fix any failures. Completed for the failures observed in this pass.
- Update this audit with completed status. Completed.

Phase 3:

- Componentize the desktop UI.
- Move Ollama adapter logic out of `connectors.py`.
- Add migration/version metadata for DB schema.

## Current Decision Log

- Managed Ollama is the first self-contained runtime target because it has a
  documented CLI server mode and HTTP health surface.
- LM Studio is not auto-started in this pass because it is a GUI application and
  the repository has no stable app launch contract for enabling its server.
- The app should not silently download models or binaries yet. That is a
  product/security decision because it affects disk usage, licenses, and network
  behavior.

## Final Status For This Pass

Completed:

- Managed Ollama runtime supervisor and API.
- Connector/outbound runtime adoption and auto-start wiring.
- Desktop runtime status/start controls.
- First desktop cleanup extraction:
  `apps/desktop/src/defaults.ts`, `apps/desktop/src/uiUtils.ts`, and
  `apps/desktop/src/CompressionPanel.tsx`.
- Metadata propagation fixes through workflow compression and Core LM ingest.
- Redaction fixes for secret refs, authorization-like values, Basic auth, API
  errors, and workflow exception storage.
- Quality evaluation attachment now points chat metadata at the chat quality row
  and evaluates the committed canonical text.
- Frontend Compression Inspector visibility and stale-preview fixes.
- Frontend accessibility and sampling input validation improvements.
- Flow Studio manual edge add/delete controls.
- Packaging cleanup for production dependencies, Python 3.11 metadata,
  packaged service data directory, and `runtime/` release-tree exclusion.

Verified:

```bash
PYTHONPATH=. .venv/bin/python -m pytest -q
npm run desktop:test
npm run test:studio
npm run desktop:build
```

Deferred:

- Bundling or downloading Ollama/model weights.
- Launching or configuring the LM Studio GUI server.
- Adding a sidecar auth token / ephemeral port handshake for packaged local IPC.
- Further splitting `apps/desktop/src/App.tsx` into focused connector, history,
  metrics, and Flow Studio components.
- Moving Ollama connector logic into a dedicated adapter module.
- Replacing additive SQLite schema setup with named migrations.
