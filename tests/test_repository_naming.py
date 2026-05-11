import re
from pathlib import Path


ALLOWED_CASED_FILES = {
    'AGENTS.md',
    'CHANGELOG.md',
    'CITATION.cff',
    'CODE_OF_CONDUCT.md',
    'CONTRIBUTING.md',
    'Dockerfile',
    'LICENSE',
    'MANIFEST.in',
    'Makefile',
    'README.md',
    'SECURITY.md',
    'apps/desktop/src/App.tsx',
    'docs/handoff/README.md',
}

IGNORED_PARTS = {
    '.git',
    '.pytest_cache',
    '.venv',
    '__pycache__',
    'build',
    'dist',
    'dist-electron',
    'dist_windows',
    'node_modules',
    'venv',
}

CONVENTIONAL_NAME = re.compile(r'^\.?[a-z0-9][a-z0-9._-]*$')
PYTHON_DUNDER_FILE = re.compile(r'^__[a-z0-9_]+__\.py$')


def has_uppercase(value: str) -> bool:
    return any(char.isupper() for char in value)


def test_repository_paths_use_conventional_casing() -> None:
    bad_dirs = []
    bad_files = []
    for path in Path('.').rglob('*'):
        parts = path.parts
        if any(part in IGNORED_PARTS for part in parts):
            continue
        if path.is_dir() and not CONVENTIONAL_NAME.fullmatch(path.name):
            bad_dirs.append(path.as_posix())
        if path.is_file():
            rel = path.as_posix()
            if rel in ALLOWED_CASED_FILES:
                continue
            if PYTHON_DUNDER_FILE.fullmatch(path.name):
                continue
            if has_uppercase(rel) or not CONVENTIONAL_NAME.fullmatch(path.name):
                bad_files.append(rel)

    assert bad_dirs == []
    assert bad_files == []
