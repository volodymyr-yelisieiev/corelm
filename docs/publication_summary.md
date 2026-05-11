# Publication Summary

## Position

This release takes Core LM to **100% publication readiness as a research artifact**.

That means:
- formal specification is frozen;
- the reference implementation is included;
- the benchmark suite is frozen and reproducible;
- tests and reports are included;
- claim discipline is explicit.

It does **not** mean 100% product readiness.

## Benchmark headline

- Reference kernel: **18/18** scenarios passed
- Oracle core: **18/18** scenarios passed
- Sliding window: **10/18**
- Large context window: **13/18**
- Periodic summary: **14/18**
- Retrieval only: **13/18**

## Publication readiness score

Overall score: **100.0/100**

## Release statement

A precise publication statement is:

> Core LM is a formally specified, benchmarked, and reproducible executable memory architecture with deterministic replay on the frozen publication suite.

## Reproducibility

```bash
PYTHONPATH=. python -m pytest -q
PYTHONPATH=. python -m benches.runner --out reports/benchmark_latest.json --readiness-out reports/publication_readiness.json
```
