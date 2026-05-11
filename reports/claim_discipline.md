# Claim Discipline Report

## Supported claims

### Core LM has a formal mathematical specification.

Support:
- `docs/sources/core_lm_state_space_formalization_and_verification.md`
- `docs/sources/core_lm_perturbation_formalization_full.md`
- `docs/sources/core_lm_orchestrator_dynamic_spec.md`

### Core LM has an executable reference implementation.

Support:
- `corelm/reference_kernel.py`
- `corelm/vendor/lucid_mind_v15_core_ref.py`

### Reference and oracle kernels pass the frozen benchmark suite with deterministic replay.

Support:
- `reports/benchmark_latest.json`
- `tests/test_reference_matches_oracle.py`
- `tests/test_replay_and_invariants.py`

### The artifact is publication-ready and locally reproducible.

Support:
- `README.md`
- `run_all.sh`
- `.github/workflows/ci.yml`
- `reports/publication_readiness.json`

## Unsupported claims

- The package is a complete commercial product.
- The package solves general-purpose open-domain NLP memory.
- The package dominates every external memory architecture outside this benchmark.