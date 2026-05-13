# Quickstart

## Run The Desktop App

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
npm install
npm run desktop:dev
```

On Windows:

```powershell
scripts\start_corelm_studio.ps1
```

The Electron app starts the Python sidecar at `http://127.0.0.1:8765` and opens
the React desktop shell. In packaged builds, service data is stored under the
app user-data directory instead of the repository working tree.

## Real Local Model Runs

Mock connector mode works without any external service. For real Ollama runs:

1. Install Ollama and pull the model you want to use.
2. Open the Connectors drawer.
3. Choose `Ollama/local`, set `mock=false`, and keep `auto_start=true`.
4. Press `Start Local Server` or run the connector. The sidecar probes
   `http://127.0.0.1:11434/api/tags` and starts `ollama serve` when needed.

If Ollama is already running, Core LM Studio adopts it. If the binary or model
is missing, the UI reports the runtime error instead of silently falling back to
mock behavior.

LM Studio remains externally managed: start its local server in LM Studio first,
then point the connector at `http://127.0.0.1:1234/v1`.

## Run The Sidecar Only

```bash
PYTHONPATH=. python -m services.core_service.corelm_studio
```

Smoke check:

```bash
curl http://127.0.0.1:8765/api/health
```

## Run Tests

```bash
PYTHONPATH=. python -m pytest -q
npm run desktop:test
```

## First Demo

1. Open Console Mode.
2. Enter `project.name = Core LM Studio`.
3. Press `Compress` to open the Compression Inspector. Inspect the raw input,
   compressed output, pipeline steps, extracted annotations, digest, and ratio.
4. Press `Core LM`.
5. Inspect the chat message, ledger entry, metrics, provenance, and replay state.
6. Press `Route` to prepare a programming-agent handoff packet.

## Connector Demo

1. Open the Connectors drawer.
2. Choose `OpenAI-compatible` or `Ollama/local`.
3. Keep `mock` mode enabled through the default payload.
4. Press `Run through Core`.
5. Inspect the resulting Core LM chat message, ledger entry, replay snapshot,
   and route receipt.
