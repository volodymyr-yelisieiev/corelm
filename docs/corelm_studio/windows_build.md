# Windows Build

## Development Run

```powershell
scripts\start_corelm_studio.ps1
```

The desktop shell starts the sidecar automatically. In source development,
Windows should have Python 3.11+ available through `.venv`, `PYTHON`, or
`CORELM_STUDIO_SERVICE_CMD`.

## Manual Setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
npm install
$env:PYTHON = ".\.venv\Scripts\python.exe"
npm run desktop:dev
```

## Build

```powershell
npm run desktop:build
```

## Package

```powershell
npm run desktop:package:win
```

`electron-builder` is configured to produce NSIS and zip artifacts. Before
packaging, `npm run desktop:prepare:python:win` downloads the Windows embeddable
Python runtime and unpacks the Python dependencies into `runtime/python-win`.
The packaged app then starts `resources/corelm_service/python/python.exe` instead
of relying on global Python.

The Python service source is copied to `resources/corelm_service` outside
`app.asar` so the sidecar can import `services.core_service.corelm_studio` in
packaged builds. Sample workflows, connector configs, prompt templates,
`examples/demo_session.json`, and example outbound packets are copied into the
same resource tree for offline demos.

The packaged app includes the Python sidecar runtime, not third-party model
servers or model weights. Real Ollama runs require Ollama to be installed on the
machine. When available, the sidecar can start `ollama serve` on demand and stop
the process it owns when the app exits. LM Studio remains an externally managed
desktop application.

Packaged service state uses the Electron user-data directory through
`CORELM_STUDIO_DATA_DIR`. Source-mode development can still override that
location explicitly.

Final installer signing and Windows Defender reputation checks are release
operations outside this local development environment.
