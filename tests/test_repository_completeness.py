from pathlib import Path


ROOT_FILES = [
    'LICENSE',
    'CHANGELOG.md',
    'CONTRIBUTING.md',
    'SECURITY.md',
    'CODE_OF_CONDUCT.md',
    '.gitignore',
    '.dockerignore',
    'MANIFEST.in',
    'requirements-dev.txt',
]

DOC_FILES = [
    'docs/corelm_studio/quickstart.md',
    'docs/corelm_studio/architecture.md',
    'docs/corelm_studio/connectors.md',
    'docs/corelm_studio/workflows.md',
    'docs/corelm_studio/security_notes.md',
    'docs/corelm_studio/replay_and_ledger.md',
    'docs/corelm_studio/windows_build.md',
    'docs/quickstart.md',
    'docs/user_guide.md',
    'docs/reproducibility_guide.md',
    'docs/limitations_and_scope.md',
    'docs/acceptance_criteria.md',
    'docs/maintenance_guide.md',
]


def test_required_repository_files_exist() -> None:
    for rel in ROOT_FILES + DOC_FILES + ['examples/demo_commands.sh']:
        assert Path(rel).exists(), rel
