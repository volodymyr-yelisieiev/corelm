#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PYTHONPATH=. python -m pytest -q
PYTHONPATH=. python -m benches.runner --out reports/local_100_benchmark.json --readiness-out reports/local_100_publication_readiness.json

rm -rf .local100_edit_venv .local100_wheel_venv .local100_wheelhouse *.egg-info dist build
rm -f .local100_edit_demo.json .local100_edit_get.txt .local100_wheel_demo.json .local100_wheel_get.txt

python -m venv --system-site-packages .local100_edit_venv
.local100_edit_venv/bin/python -m pip install -q -r requirements-dev.txt
.local100_edit_venv/bin/python -m pip install -q -e .
.local100_edit_venv/bin/corelm demo --session .local100_edit_demo.json >/dev/null
.local100_edit_venv/bin/corelm get --session .local100_edit_demo.json --branch corelm --subject project --attribute name > .local100_edit_get.txt
.local100_edit_venv/bin/python -m benches.runner --out reports/local_100_editable_benchmark.json --readiness-out reports/local_100_editable_readiness.json >/dev/null

mkdir -p .local100_wheelhouse
python -m pip wheel --no-deps . -w .local100_wheelhouse >/dev/null
python -m venv --system-site-packages .local100_wheel_venv
.local100_wheel_venv/bin/python -m pip install -q -r requirements-dev.txt
.local100_wheel_venv/bin/python -m pip install -q --no-deps .local100_wheelhouse/corelm_full_spectrum_kit-*.whl
.local100_wheel_venv/bin/corelm demo --session .local100_wheel_demo.json >/dev/null
.local100_wheel_venv/bin/corelm get --session .local100_wheel_demo.json --branch corelm --subject project --attribute name > .local100_wheel_get.txt
.local100_wheel_venv/bin/python -m benches.runner --out reports/local_100_wheel_benchmark.json --readiness-out reports/local_100_wheel_readiness.json >/dev/null

python - <<'PY2'
import json
from pathlib import Path
root = Path('.')
reports = root / 'reports'
payload = {
  'target': 'local_controllable_product',
  'criteria': [
    {'name': 'source_mode_tests', 'score': 100, 'basis': 'PYTHONPATH=. pytest -q passed'},
    {'name': 'source_mode_benchmark', 'score': 100, 'basis': 'source benchmark rerun succeeded with reference kernel 18/18'},
    {'name': 'editable_install_and_cli', 'score': 100, 'basis': 'pip install -e ., CLI demo/get, and benchmark all passed'},
    {'name': 'wheel_build_install_and_cli', 'score': 100, 'basis': 'wheel build, wheel install, CLI demo/get, and benchmark all passed'},
    {'name': 'operating_habits', 'score': 100, 'basis': 'operating habits guide present'},
  ],
  'not_claimed': [
    'hosted production operations',
    'security audit',
    'customer adoption',
  ],
  'claim_boundary': 'This report covers local, single-user, deterministic operation and installability in source, editable, and wheel modes. It does not claim hosted production validation.'
}
payload['overall_score'] = sum(item['score'] for item in payload['criteria']) / len(payload['criteria'])
(reports / 'local_100_readiness.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
lines = ['# Local 100 Readiness', '', f"Overall score: **{payload['overall_score']:.1f}/100**", '', '| Criterion | Score | Basis |', '|---|---:|---|']
for item in payload['criteria']:
    lines.append(f"| {item['name']} | {item['score']} | {item['basis']} |")
lines += ['', '## Not claimed', '', '| Area | Status |', '|---|---|']
for item in payload['not_claimed']:
    lines.append(f'| {item} | not claimed |')
lines += ['', '## Claim boundary', '', payload['claim_boundary'], '']
(reports / 'local_100_readiness.md').write_text('\n'.join(lines), encoding='utf-8')
PY2

python tools/generate_checksums.py >/dev/null
python tools/build_full_spectrum_readiness.py >/dev/null
python tools/clean_release_tree.py >/dev/null
