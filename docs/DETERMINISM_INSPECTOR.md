# Determinism Inspector

The Benchmark Studio surface shows determinism summaries for the active run:

- exact output repeat rate
- exact token sequence repeat rate
- token trace hash repeat rate
- replay consistency score

Strict deterministic profiles should target exact output and exact token
sequence repeat rates of `1.0`. Seeded stochastic profiles still measure the
same values, but pass/fail policy is profile-specific because some backends are
not exactly repeatable even with a seed.

Unavailable low-level traces, such as logits or entropy, stay `null` unless the
adapter directly exposes them.
