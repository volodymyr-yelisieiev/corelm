# Windows Build

## Development Run

```powershell
scripts\start_corelm_studio.ps1
```

The desktop shell starts the sidecar automatically. Windows must have Python
3.11+ available, or `PYTHON`/`CORELM_STUDIO_SERVICE_CMD` must point to a bundled
or managed sidecar launcher.

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

`electron-builder` is configured to produce NSIS and zip artifacts. The Python
service source is copied to `resources/corelm_service` outside `app.asar` so the
sidecar can import `services.core_service.corelm_studio` in packaged builds.
Final installer signing and Windows Defender reputation checks are release
operations outside this local development environment.
