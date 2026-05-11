# Release Notes

## Version 1.3.0

This release completes the repository-grade surface of the local 100 bundle.

Added and fixed:
- clean release-tree discipline via `.gitignore`, `.dockerignore`, and `MANIFEST.in`
- proprietary `LICENSE` file aligned with evaluation/archive use
- `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, and `CODE_OF_CONDUCT.md`
- split runtime and development requirements
- quickstart, user guide, reproducibility guide, limitations, acceptance, and maintenance docs
- cleanup and multi-variant validation tooling
- repository completeness tests and CLI help test
- removal of stray local runtime artifacts from the release source tree

Operational result:
- source mode validated
- editable install validated
- wheel build/install path documented and validated
- release archive now has the standard repository files expected for handoff and review

## Version 1.2.0

Version 1.2.0 hardened the local reference product path and validated all local execution variants.
