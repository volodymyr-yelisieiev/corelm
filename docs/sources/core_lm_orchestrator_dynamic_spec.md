# Core LM — Orchestrator as a Dynamic System (Formal Specification)

## 1. Problem Setting

State dynamics:

S_{t+1} = F(S_t, U_t)
S_t ∈ R^n

Multiple perturbation sources:

U_t^{(i)} ∈ R^m,  i = 1,...,k

We define a convex mixture:

w_t ∈ Δ^{k-1}
w_i ≥ 0
Σ w_i = 1

U_t = Σ w_{t,i} U_t^{(i)}

---

## 2. Orchestrator Internal State

O_t ∈ R^p

Update rule:

O_{t+1} = G(O_t, S_t, r_t)

Where r_t is metric vector:

r_t = [
  ||S_t||,
  ||S_{t+1}-S_t||,
  invariant_violation_rate,
  ||U_t||,
  quality_score
]

Weights via softmax:

w_t = softmax(W O_t + b)

---

## 3. Safety Layer

Mixed impulse:

Ũ_t = Σ w_{t,i} U_t^{(i)}

Energy constraint:

U_t = clip_norm(Ũ_t, M)

Guarantee:

||U_t|| ≤ M

---

## 4. Stability Condition

If F_stable is contraction:

||F_stable(S1) - F_stable(S2)|| ≤ c ||S1 - S2||,  c < 1

And ||U_t|| ≤ M,

Then system is bounded (ISS-style behavior).

---

## 5. Mandatory Invariants

1. w_i ≥ 0
2. Σ w_i = 1
3. ||U_t|| ≤ M
4. S_t ∈ X

---

## 6. Required Tests

Unit tests:
- weight normalization
- clipping correctness
- dimension consistency

Property-based tests:
- convexity preservation
- bounded-input bounded-state
- stability under random mixtures

Regression tests:
- compare violation rate across orchestrator versions
- compare max norm growth
- ensure no degradation in safety metrics

---

## 7. Core Architecture

PerturbationSource_i → Orchestrator → Mixer → Core F → Metrics → Orchestrator

Sequential, measurable, verifiable.

---

End of specification.
