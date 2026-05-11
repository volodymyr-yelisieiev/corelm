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
the React desktop shell.

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
3. Press `Core LM`.
4. Inspect the chat message, ledger entry, metrics, provenance, and replay state.
5. Press `Route` to prepare a programming-agent handoff packet.

## Connector Demo

1. Open the Connectors drawer.
2. Choose `OpenAI-compatible` or `Ollama/local`.
3. Keep `mock` mode enabled through the default payload.
4. Press `Run through Core`.
5. Inspect the resulting Core LM chat message, ledger entry, replay snapshot,
   and route receipt.
