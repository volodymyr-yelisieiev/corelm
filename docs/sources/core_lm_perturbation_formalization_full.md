# Core LM — Formalization of External Perturbation Source (U_t)

## 1. Definition

We define the external perturbation (cognitive excitation source):

U_t ∈ R^m

Where:

- U_t — external impulse at time t
- m — dimensionality of excitation space
- U ⊆ R^m — admissible input domain

The system evolves as:

S_{t+1} = F(S_t, U_t)

with S_t ∈ X ⊆ R^n.

---

# 2. Classes of Perturbation

We define three formal classes of excitation:

## 2.1 Deterministic Structured Input (LLM-Vectorized)

U_t = E(z_t)

Where:
- z_t — structured symbolic output (text, plan, tokens)
- E : Z → R^m — embedding operator

Properties to formalize:

1. Boundedness:
   ||U_t|| ≤ M

2. Lipschitz continuity of embedding:
   ||E(z1) − E(z2)|| ≤ L ||z1 − z2||

3. Dimensional consistency:
   dim(U_t) = m (fixed)

---

## 2.2 Stochastic Perturbation

U_t ~ D(μ, Σ)

Where:
- μ — mean vector
- Σ — covariance matrix

Common cases:

- Gaussian noise: U_t ~ N(μ, Σ)
- Uniform bounded noise

Required properties:

1. E[U_t] = μ
2. Cov(U_t) = Σ
3. E[||U_t||^2] < ∞

---

## 2.3 Chaotic Generator (Deterministic Nonlinear)

U_{t+1} = G(U_t)

Where G is nonlinear map with:

- Sensitive dependence on initial conditions
- Positive Lyapunov exponent (optional)

Example structure:

U_{t+1} = A U_t + φ(U_t)

Where φ is nonlinear bounded function.

---

# 3. Stability Under Perturbation

We define Input-to-State Stability (ISS):

There exist functions β and γ such that:

||S_t|| ≤ β(||S_0||, t) + γ( sup_{k < t} ||U_k|| )

If satisfied → system is stable under bounded input.

---

# 4. Linear Case

S_{t+1} = A S_t + B U_t

Stability condition:

Spectral radius ρ(A) < 1

Bounded response:

If ||U_t|| ≤ M,
then

sup ||S_t|| ≤ C * M

Where C depends on A and B.

---

# 5. Nonlinear Case

S_{t+1} = F(S_t, U_t)

Assume F Lipschitz:

||F(S1,U1) − F(S2,U2)|| ≤ Ls ||S1 − S2|| + Lu ||U1 − U2||

If Ls < 1 → contraction in state space.

---

# 6. Required Mathematical Tests

Each perturbation module must pass:

## 6.1 Dimension Test

assert dim(U_t) == m

## 6.2 Boundedness Test

Simulate random U_t
Verify sup ||U_t|| < threshold

## 6.3 Spectral Stability Test (Linear Case)

Compute eigenvalues of A
assert max(|λ|) < 1

## 6.4 Lipschitz Estimation

Numerically estimate:

||F(S+ε, U) − F(S, U)|| / ||ε||

Ensure < threshold

## 6.5 ISS Empirical Test

Simulate:

Bounded U_t
Check:

max ||S_t|| remains bounded

---

# 7. Property-Based Tests (Hypothesis Template)

1. For all bounded U_t:
   S_t ∈ X

2. If U_t = 0:
   S_t converges (if A stable)

3. If ||U_t|| ≤ M:
   ||S_t|| ≤ K*M

4. Determinism test:
   Same seed → identical S trajectory

---

# 8. Metric Definitions

Log per simulation:

- ||U_t||
- ||S_t||
- Drift ||S_{t+1} − S_t||
- Spectral radius (if linear)
- Empirical Lyapunov trend

---

# 9. Acceptance Criteria

A perturbation source may be committed only if:

1. Domain U explicitly defined
2. Boundedness or distribution specified
3. Lipschitz/linear stability analyzed
4. ISS empirically validated
5. Property tests pass
6. No invariant violation in S-space

---

# 10. Core Principle

Perturbation must inject excitation
without violating invariant structure
or causing uncontrolled divergence.

Controlled excitation.
Measured amplification.
Verified stability.
