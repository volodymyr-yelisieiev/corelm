from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_cli(repo: Path, *args: str) -> str:
    cmd = [sys.executable, '-m', 'corelm.cli', *args]
    out = subprocess.check_output(cmd, cwd=repo, env={'PYTHONPATH': str(repo)})
    return out.decode('utf-8').strip()


def test_cli_roundtrip(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    session = tmp_path / 'cli_session.json'
    run_cli(repo, 'ingest', '--session', str(session), '--branch', 'corelm', '--subject', 'project', '--attribute', 'name', '--value', 'Core LM')
    value = run_cli(repo, 'get', '--session', str(session), '--branch', 'corelm', '--subject', 'project', '--attribute', 'name')
    assert value == 'Core LM'
