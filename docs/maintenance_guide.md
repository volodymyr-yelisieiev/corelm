# Maintenance Guide

## When changing code

1. update the affected documentation
2. run `make release-check`
3. regenerate checksums
4. confirm `CHANGELOG.md` and `docs/release_notes.md`
5. cut a clean zip from a cleaned tree only

## When changing scenarios

- treat scenario files as versioned benchmark fixtures
- justify why the change is not benchmark laundering
- refresh benchmark and readiness reports
- record the change in the changelog

## Versioning rule

- patch: docs/report/packaging fixes
- minor: new docs, tests, validation paths, or non-breaking local UX
- major: semantic changes to kernels, benchmark meaning, or claim boundary

## Release routine

```bash
python tools/clean_release_tree.py
pip install -r requirements-dev.txt
make release-check
python -m pip wheel . -w dist --no-deps
```
