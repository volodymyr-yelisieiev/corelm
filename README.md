# Core LM Studio

Core LM Studio is a local-first Windows desktop application built on top of the
Core LM full-spectrum research kit. It combines:

- an Electron + React calculator-inspired console for Core LM operations;
- a Python sidecar service that wraps the existing deterministic Core LM
  reference product;
- SQLite persistence for sessions, workflows, chat bus messages, ledger mirrors,
  replay snapshots, connector metadata, and metrics;
- an n8n-like Flow Studio for node-based ingestion, compression, Core LM
  execution, chat output, and outbound routing;
- deterministic mocks for external LLM/local model/REST integrations.

Core LM remains the canonical state authority. External systems are perturbation
sources or outbound targets, and the global chat is an interaction bus rather
than a truth store.

## Studio quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
npm install
npm run desktop:dev
```

Windows:

```powershell
scripts\start_corelm_studio.ps1
```

Useful development commands:

```bash
PYTHONPATH=. python -m services.core_service.corelm_studio
npm run desktop:test
npm run desktop:build
PYTHONPATH=. python -m pytest -q
```

Primary Studio docs:

- `docs/corelm_studio/quickstart.md`
- `docs/corelm_studio/architecture.md`
- `docs/corelm_studio/connectors.md`
- `docs/corelm_studio/workflows.md`
- `docs/corelm_studio/security_notes.md`
- `docs/corelm_studio/replay_and_ledger.md`
- `docs/corelm_studio/windows_build.md`
- `docs/implementation_plan.md`
- `docs/architecture_decisions.md`

## Core LM Full-Spectrum Kit

Core LM is a deterministic memory architecture that separates text generation
from truth storage. This repository packages the project as one clean,
reproducible bundle with four aligned layers:

1. **Publication artifact** — formal specification, reference kernel, oracle kernel, benchmark suite.
2. **Archive package** — source snapshot, checksums, manifest, release notes, rebuild path.
3. **Sales package** — one-pager, FAQ, positioning, pricing template, objection handling.
4. **Local reference product** — installable Python package plus CLI for structured fact ingestion, provenance, replay, and session persistence.

## Claim boundary

This bundle supports these precise claims:
- publication-ready research artifact;
- archive-ready reproducible source bundle;
- sales-collateral-complete package for demos and evaluation conversations;
- complete **local reference product** for single-user deterministic operation.

It does **not** claim:
- audited security hardening;
- multi-tenant cloud operations;
- customer adoption proof;
- legal review of commercial terms.

## Quick start

### Local product use

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install .
corelm demo --session examples/demo_session.json
corelm get --session examples/demo_session.json --branch corelm --subject project --attribute name
```

### Development and full validation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
make release-check
```

## Common commands

```bash
# source mode
PYTHONPATH=. python -m pytest -q
PYTHONPATH=. python -m benches.runner --out reports/benchmark_latest.json --readiness-out reports/publication_readiness.json
PYTHONPATH=. python -m corelm.cli demo --session examples/demo_session.json

# editable install
pip install -e .
corelm demo --session examples/demo_session.json

# wheel build/install
python -m pip wheel . -w dist --no-deps
pip install dist/*.whl
corelm demo --session examples/demo_session.json
```

## Repository layout

- `corelm/` — kernels, baselines, product wrapper, CLI
- `benches/` — frozen benchmark traces and runner
- `tests/` — publication and product tests
- `docs/` — publication, archive, sales, product, maintenance, and handoff docs
- `reports/` — benchmark, readiness, and checksum reports
- `examples/` — reproducible demo session and command walkthrough
- `tools/` — cleanup and verification scripts
- `apps/desktop/` — Electron, React, and TypeScript desktop shell
- `services/core_service/` — Python Core LM Studio sidecar service
- `packages/` — shared TypeScript contracts and UI constants
- `sample_workflows/` — importable Flow Studio examples
- `sample_connectors/` — mock connector configuration examples
- `prompt_templates/` — programming-agent outbound packet templates
- `scripts/` — Windows and cross-platform local launch helpers

## Important companion docs

- `docs/quickstart.md`
- `docs/user_guide.md`
- `docs/reproducibility_guide.md`
- `docs/limitations_and_scope.md`
- `docs/maintenance_guide.md`
- `docs/release_notes.md`

## Packaging status

- Publication artifact: complete
- Archive package: complete
- Sales collateral: complete
- Local reference product: complete
- Hosted production service: intentionally out of scope for this bundle
