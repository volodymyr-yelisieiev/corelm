#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

python -m pytest -q
PYTHONPATH=. python -m benches.runner --out reports/benchmark_latest.json --readiness-out reports/publication_readiness.json
PYTHONPATH=. python -m corelm.cli demo --session examples/demo_session.json > /dev/null

python -m venv .variant_edit
source .variant_edit/bin/activate
pip install -q -r requirements-dev.txt
pip install -q -e .
python -m pytest -q
corelm demo --session examples/demo_session.json > /dev/null
deactivate
rm -rf .variant_edit

python -m venv .variant_wheel
source .variant_wheel/bin/activate
pip install -q -r requirements-dev.txt
python -m pip wheel . -w dist --no-deps > /dev/null
pip install -q dist/*.whl
corelm demo --session examples/demo_session.json > /dev/null
deactivate
rm -rf .variant_wheel dist build *.egg-info
