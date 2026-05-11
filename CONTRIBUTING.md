# Contributing

This repository is a frozen reference bundle first, and a development target
second. Changes are acceptable only when they preserve benchmark integrity and
claim discipline.

## Ground rules

- Do not rewrite benchmark scenarios to rescue a weaker implementation.
- Do not widen claims beyond what reports actually validate.
- Do not remove provenance, replay, or contradiction semantics.
- Keep deterministic behavior under fixed seeds.
- Update docs and reports when a change affects user-visible behavior.

## Local workflow

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
make release-check
```

## Required checks before proposing a change

1. `make test`
2. `make bench`
3. `make demo`
4. `make checksums`
5. `tools/validate_local_variants.sh`

## Change categories

- **Documentation-only**: docs, reports, packaging metadata.
- **Reference-kernel changes**: must keep benchmark semantics and replay.
- **Scenario changes**: require explicit justification and report refresh.
- **Sales/archive changes**: must not alter technical claims.

## Commit hygiene

- Prefer small, reviewable changes.
- Mention affected claims in the commit message.
- Regenerate checksums whenever archive contents change.
