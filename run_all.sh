#!/usr/bin/env bash
set -euo pipefail

PYTHONPATH=. python -m pytest -q
PYTHONPATH=. python -m benches.runner --out reports/benchmark_latest.json --readiness-out reports/publication_readiness.json
PYTHONPATH=. python -m corelm.cli demo --session examples/demo_session.json
PYTHONPATH=. python -m pytest -q tests/core_service
python tools/generate_checksums.py
if command -v npm >/dev/null 2>&1 && [ -d node_modules ]; then
  npm run desktop:test
fi
python tools/build_full_spectrum_readiness.py
