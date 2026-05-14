# Benchmark Profiles

Core LM Studio stores benchmark profiles in SQLite and exposes them through
`GET /api/benchmarks/profiles`. Built-in profiles cover runtime conformance,
determinism, compression, Core LM state dynamics, structured output, long
context retention, workflow/product integration, and stress/resource stability.

## Profile Fields

- `id`, `name`, `description`
- `mode`: `strict_direct`, `seeded_stochastic`, or `free_exploratory`
- `strict`: whether the run may produce a strict verdict
- `adapter_id`, `model_ref`
- `repetitions`
- `cases`: prompts, system text, annotations, evaluator config
- `generation_config`: seed and sampler settings
- `trace_config`: token/logprob/top-k capture preferences
- `compression`: Core LM preprocessing options
- `thresholds`: profile-specific pass/fail checks

## Built-In Profiles

The default smoke profiles use `deterministic_direct_smoke` so the UI, API, CLI,
SQLite persistence, and report exports can be verified from a clean checkout.
They are non-strict and are not production LLM benchmark results.

Strict templates for `transformers_direct` and `llamacpp_direct` are included
but remain blocked until the user supplies local models and optional runtime
dependencies.
