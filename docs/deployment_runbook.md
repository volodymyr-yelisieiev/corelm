# Deployment Runbook

## Local install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Smoke test

```bash
PYTHONPATH=. python -m pytest -q
PYTHONPATH=. python -m corelm.cli demo --session examples/demo_session.json
PYTHONPATH=. python -m corelm.cli get --session examples/demo_session.json --branch corelm --subject project --attribute name
```

## Container

```bash
docker build -t corelm-full-spectrum .
docker run --rm corelm-full-spectrum
```

## Backup / restore
Session state is stored as JSON; back up the session file and restore by re-loading it through the CLI or Python API.
