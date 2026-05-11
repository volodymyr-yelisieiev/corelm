# Reproducibility Guide

This bundle supports three local execution modes.

## 1. Source mode

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
PYTHONPATH=. python -m pytest -q
PYTHONPATH=. python -m benches.runner --out reports/benchmark_latest.json --readiness-out reports/publication_readiness.json
```

## 2. Editable install

```bash
python -m venv .venv-edit
source .venv-edit/bin/activate
pip install -r requirements-dev.txt
pip install -e .
python -m pytest -q
corelm demo --session examples/demo_session.json
```

## 3. Wheel install

```bash
python -m venv .venv-wheel
source .venv-wheel/bin/activate
pip install -r requirements-dev.txt
python -m pip wheel . -w dist --no-deps
pip install dist/*.whl
corelm demo --session examples/demo_session.json
```

## Integrity checks

- `reports/archive_checksums.txt` gives SHA256 digests
- `CoreLMProduct.replay_verify()` confirms digest stability
- `tools/validate_local_variants.sh` automates local mode validation

## Clean build rule

Before packaging a release, run:

```bash
python tools/clean_release_tree.py
python tools/generate_checksums.py
```
