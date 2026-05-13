# Quality Eval

Quality evaluation is separate from Core LM stability, replay, and invariant
metrics. It does not claim semantic truth unless a reference is configured.

Evaluation packets are versioned as `quality_eval.v1` and stored through
`GET /api/quality?session_id=default`. Ingested runs also include the packet in
chat metadata, ledger metadata, and metrics history.

Supported checks include:

- general text: nonempty output, output length, repetition ratio,
  contradiction marker count, optional format compliance, keyword coverage,
  exact match, normalized match, fuzzy match, and an unsafe-output hook;
- structured output: JSON/XML/simple YAML parse validity, simple schema
  validity, required key coverage, and field completeness;
- compression-aware: compression ratio, duplicate line reduction,
  canonicalization applied, contradiction candidates, and raw/canonical diff
  size;
- workflow: node success/failure counts, final output availability, outbound
  delivery failures, and pipeline completeness.

`summary_score` is the fraction of applicable checks that passed. When no
reference answer, expected terms, expected keys, or schema is provided, the
score is structural/process quality only.
