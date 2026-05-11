# Acceptance Criteria

A local release is treated as complete only if all of the following hold.

## Source tree

- clean tree with no build cache, venv, or stray runtime artifacts
- root metadata files present
- benchmark scenarios present and unchanged unless versioned

## Validation

- `pytest` passes
- benchmark runner completes
- demo session builds
- archive checksums regenerate
- source, editable, and wheel variants all work

## Documentation

- README and quickstart present
- user guide present
- reproducibility guide present
- scope/limitations documented
- release notes and changelog updated

## Claims

- no unsupported production or security claims
- archive and sales docs consistent with benchmark reports
- local product claims restricted to deterministic single-user use
