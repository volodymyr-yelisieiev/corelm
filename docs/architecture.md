# Core LM Architecture Note

## Formal decomposition

The package implements the Core LM doctrine as:

1. **E — Excitation / extraction**
   - a deterministic benchmark adapter converts natural-language trace events into structured claims;
   - the raw event text is also converted into a numeric perturbation using the vendored v1.5 core text embedding source.

2. **N — Normalize**
   - claim slots are canonicalized as `branch::subject::attribute`;
   - near-duplicate values are suppressed with deterministic similarity rules.

3. **T — Transition**
   - the numeric state is advanced by the vendored `LucidMindCoreV15` operator;
   - symbolic truth candidates are prepared against canonical slots.

4. **Q — Verify**
   - state norm finiteness;
   - state norm boundedness;
   - one current fact per slot;
   - mandatory provenance on all durable facts.

5. **K — Commit**
   - append-only ledger entry;
   - durable fact insertion or supersession;
   - frozen snapshot and digest support.

## Why this closes the earlier gap

Earlier project status had a gap between:
- strong formal specification, and
- absence of an integrated benchmarked implementation.

This package closes that gap for the **publication target** by shipping:
- a real reference implementation,
- an oracle ceiling,
- frozen scenarios,
- deterministic replay,
- regression tests,
- reproducible reports.

## Boundaries

This remains a **reference implementation**.
It is benchmark-conformant and publication-ready, but it is not asserted to be a production application stack.
