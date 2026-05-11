from __future__ import annotations

import subprocess
import sys


def test_cli_help_lists_core_commands() -> None:
    out = subprocess.check_output([sys.executable, '-m', 'corelm.cli', '--help'])
    text = out.decode('utf-8')
    assert 'ingest' in text
    assert 'correct' in text
    assert 'get' in text
    assert 'provenance' in text
    assert 'list-branch' in text
    assert 'demo' in text
