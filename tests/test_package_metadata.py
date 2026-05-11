from __future__ import annotations

import tomllib
from pathlib import Path


def test_pyproject_declares_package_discovery_and_scenario_data() -> None:
    payload = tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))
    setuptools = payload['tool']['setuptools']
    find_cfg = setuptools['packages']['find']
    assert 'corelm*' in find_cfg['include']
    assert 'benches*' in find_cfg['include']
    assert 'reports*' in find_cfg['exclude']
    package_data = setuptools['package-data']
    assert 'scenarios/*.json' in package_data['benches']
