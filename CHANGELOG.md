# Changelog

## 1.3.0

This release completes the local reference bundle as a clean repository-grade
artifact and fills the operational files that were still missing at the root
of the project.

Added:
- proprietary `LICENSE`
- `CONTRIBUTING.md`, `SECURITY.md`, and `CODE_OF_CONDUCT.md`
- `.gitignore`, `.dockerignore`, and `MANIFEST.in`
- `requirements-dev.txt`
- `docs/quickstart.md`
- `docs/user_guide.md`
- `docs/reproducibility_guide.md`
- `docs/limitations_and_scope.md`
- `docs/acceptance_criteria.md`
- `docs/maintenance_guide.md`
- `examples/demo_commands.sh`
- `tools/clean_release_tree.py`
- `tools/validate_local_variants.sh`
- `tests/test_repository_completeness.py`
- `tests/test_cli_help.py`

Changed:
- cleaned the source tree for release packaging
- upgraded metadata in `pyproject.toml`
- split runtime and development requirements
- expanded `README.md`, `Makefile`, and `run_all.sh`
- strengthened checksum generation filters and readiness checks
- refreshed archive, release, and license documentation

Retained:
- deterministic reference kernel and oracle kernel
- frozen benchmark scenarios and baseline comparisons
- local CLI product workflow and replay verification
- publication, archive, sales, and product documentation

## 1.2.0

Version 1.2.0 hardened the local reference product path and validated source,
editable-install, and wheel-install execution modes.
