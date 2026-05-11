# Core LM: A Publication-Ready Executable Specification with Deterministic Benchmarking

## Abstract

Core LM is framed as a discrete-time dynamical system with controlled excitation, bounded state evolution, and append-only knowledge commits.
This release packages the formal specification, a deterministic reference kernel, an oracle ceiling, and a frozen benchmark suite into a reproducible research artifact.

## 1. Problem

Long-horizon reasoning systems often collapse memory, truth maintenance, and generation into one opaque interface.
Core LM instead separates:
- external excitation,
- internal state transition,
- verification,
- durable commit.

## 2. Formal model

The formal source documents define:
- state dynamics `S_{t+1} = F(S_t, U_t)`;
- observation `y_t = H(S_t)`;
- perturbation classes for deterministic, stochastic, and chaotic excitation;
- orchestrator dynamics with convex mixing and bounded input.

## 3. Implementation in this release

The package vendors the uploaded v1.5 core as the numeric state engine and adds:
- deterministic extraction adapter;
- canonical truth state;
- append-only ledger;
- provenance tracking;
- supersession handling;
- deterministic replay digest.

## 4. Benchmark

The benchmark suite includes:
- direct spec recall;
- delayed recall under long noise walls;
- contradiction handling;
- branch isolation;
- paraphrase suppression;
- provenance queries;
- long-horizon publication traces;
- adversarial mixed-branch scenarios.

Baselines:
- sliding window;
- larger window;
- periodic summary;
- retrieval-only.

## 5. Results

On the frozen suite, both the oracle kernel and the reference kernel pass all scenarios with perfect query accuracy, deterministic replay, and full provenance coverage.
The baselines fail on long retention, provenance, and contradiction control.

## 6. Interpretation

The release demonstrates that the Core LM doctrine is not merely conceptual.
It exists as a deterministic executable specification with measurable behavior and reproducible reports.

## 7. Limitations

The extraction layer is deterministic and benchmark-backed.
This release does not claim product completeness or unconstrained NLP capability.

## 8. Release position

Therefore the project is publication-ready as a research artifact.
It is not presented as a finished product.
