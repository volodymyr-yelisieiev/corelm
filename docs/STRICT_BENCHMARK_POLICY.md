# Strict Benchmark Policy

## Strict Direct Mode

Strict direct mode is the only mode allowed to produce strict benchmark
verdicts. A strict profile must use a direct adapter and must include:

- `mode = strict_direct`
- `strict = true`
- direct adapter id
- explicit `model_ref`
- explicit seed in `generation_config`
- persisted generation and adapter config hashes
- token trace
- Core LM replay and state metrics
- compression metrics
- profile-specific pass/fail thresholds

If any requirement is missing, the run is persisted as blocked and excluded from
strict summaries.

## Bridge Mode

Bridge/API paths remain product features but are never equivalent to strict
direct runtime benchmarking. Bridge paths include Ollama HTTP, LM Studio
OpenAI-compatible HTTP, OpenAI-compatible cloud APIs, REST inputs, shell
captures, files, clipboard, and outbound targets.

Bridge runs:

- are labeled non-strict;
- may have reduced metric sets;
- store unavailable metrics as `null`;
- cannot satisfy strict determinism claims;
- may still pass product smoke profiles.

## Generation Modes

- Strict deterministic: greedy or effectively deterministic settings, explicit
  seed, fixed sampler config, repeated exact-token comparison.
- Seeded stochastic: explicit seed and full sampler persistence; repeatability
  is measured, not assumed.
- Free exploratory: profiling only; excluded from strict pass/fail.

## No Fabricated Metrics

Metrics must come from direct runtime output, Core LM state, compression output,
local instrumentation, or a clearly labeled derived calculation. If a backend
does not expose a metric, the value is `null` with source `unavailable`.
