# Archive Manifest

This bundle is the frozen archive form of the Core LM full-spectrum kit.

## Archive contents

- source package under `corelm/`
- frozen benchmark traces under `benches/scenarios/`
- tests under `tests/`
- formal source specs under `docs/sources/`
- operational and handoff docs under `docs/`
- reports under `reports/`
- demo assets under `examples/`
- reproducibility helpers under `tools/`
- checksums in `reports/archive_checksums.txt`

## Rebuild commands

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
make release-check
```

## Archive claim

This package is complete enough to be frozen, copied, verified by checksum,
and replayed locally without hidden external services.
