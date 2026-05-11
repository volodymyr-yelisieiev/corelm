"""Vendored from uploaded /mnt/data/lucid_mind_v15_core.py with a stable-hash fix for cross-process determinism.


Lucid Mind v1.5 — Clean Core (reference implementation)

Design goals (v1.5):
- Self state S_t in R^n with explicit decomposition (Z, M, C) via slicing.
- Strict CognitiveFlow interface: external sources produce perturbations U_t; they never touch internal state.
- VoidInstabilityEngine is the ONLY component allowed to update the core state.
- Flow history stores state trajectory and supports compression (PCA-based) for persistence / downstream use.
- Built-in metrics: Energy, CSI, ED, etc.

Dependencies:
- Python 3.10+
- numpy

Note:
This is a *reference* implementation intended for experimentation and benchmarking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, Optional, Dict, Any, Tuple, List, Callable, Iterable
import time
import hashlib

import numpy as np


# ---------------------------
# Utilities
# ---------------------------

def _tanh(x: np.ndarray) -> np.ndarray:
    return np.tanh(x)


def _safe_float(x: float) -> float:
    # Guard against numpy scalar weirdness
    try:
        return float(x)
    except Exception:
        return float(np.asarray(x).item())


# ---------------------------
# CognitiveFlow (strict interface)
# ---------------------------

class CognitiveSource(Protocol):
    """
    External source that produces a perturbation vector U_t in R^n.
    The source must NOT be able to read/write internal core state.

    Implementations can wrap:
    - LLM outputs (via embedding adapter)
    - stochastic generators
    - external environment signals
    """
    def produce(self, x: Any) -> np.ndarray:
        ...


@dataclass(frozen=True)
class CognitiveFlow:
    """
    Enforces the "LLM -> Core" (or general source -> Core) boundary:
    - The Core never exposes internal state to the source.
    - Only accepts a perturbation vector U_t with the correct dimensionality.
    """
    n: int

    def ingest(self, source: CognitiveSource, x: Any) -> np.ndarray:
        u = source.produce(x)
        u = np.asarray(u, dtype=np.float32).reshape(-1)
        if u.shape[0] != self.n:
            raise ValueError(f"CognitiveFlow: perturbation dim mismatch: expected {self.n}, got {u.shape[0]}")
        return u


# ---------------------------
# Adapters / Sources
# ---------------------------

@dataclass
class RandomPerturbationSource:
    """
    Simple stochastic source for testing autonomous dynamics without LLM.

    mode:
        - "gaussian": N(0, sigma^2)
        - "uniform": U(-scale, scale)
    """
    n: int
    mode: str = "gaussian"
    sigma: float = 0.05
    scale: float = 0.05
    seed: Optional[int] = None

    def __post_init__(self) -> None:
        self._rng = np.random.default_rng(self.seed)

    def produce(self, x: Any = None) -> np.ndarray:
        if self.mode == "gaussian":
            return self._rng.normal(0.0, self.sigma, size=(self.n,)).astype(np.float32)
        if self.mode == "uniform":
            return self._rng.uniform(-self.scale, self.scale, size=(self.n,)).astype(np.float32)
        raise ValueError(f"Unknown mode: {self.mode}")


@dataclass
class TextHashEmbeddingSource:
    """
    Stand-in for "LLM(output) -> embedding -> U_t".

    This does NOT call an LLM. It deterministically hashes text into a vector.
    Use only for pipeline testing and benchmarking where you need reproducibility.

    For real systems replace with:
        - embedding model output
        - or your own adapter mapping
    """
    n: int
    seed: int = 1337

    def produce(self, x: Any) -> np.ndarray:
        txt = str(x)
        # stable deterministic pseudo-embedding via SHA256 keyed on text
        digest = hashlib.sha256(f"{self.seed}::{txt}".encode("utf-8")).digest()
        h = int.from_bytes(digest[:8], "big", signed=False)
        rng = np.random.default_rng(h)
        v = rng.normal(0.0, 1.0, size=(self.n,)).astype(np.float32)
        # normalize to unit length to keep scale stable
        norm = np.linalg.norm(v) + 1e-8
        return (v / norm).astype(np.float32)


# ---------------------------
# History + Compression
# ---------------------------

@dataclass
class FlowHistory:
    """
    Stores the recent trajectory of states S_t. Designed for sequential dynamics.

    window_k:
        number of states kept (sliding window).
    """
    n: int
    window_k: int = 256
    states: List[np.ndarray] = field(default_factory=list)

    def push(self, s: np.ndarray) -> None:
        s = np.asarray(s, dtype=np.float32).reshape(-1)
        if s.shape[0] != self.n:
            raise ValueError(f"FlowHistory: state dim mismatch: expected {self.n}, got {s.shape[0]}")
        self.states.append(s.copy())
        if len(self.states) > self.window_k:
            self.states = self.states[-self.window_k :]

    def tail(self, k: int) -> np.ndarray:
        k = max(1, min(k, len(self.states)))
        return np.stack(self.states[-k:], axis=0)  # (k, n)

    def variance(self, k: int) -> float:
        if len(self.states) < 2:
            return 0.0
        X = self.tail(k)
        return _safe_float(np.mean(np.var(X, axis=0)))

    def as_matrix(self) -> np.ndarray:
        if not self.states:
            return np.zeros((0, self.n), dtype=np.float32)
        return np.stack(self.states, axis=0)


@dataclass
class PCACompressor:
    """
    Simple PCA compressor for trajectory history H_t.

    Returns:
        compressed representation: (components, mean, explained_var_ratio)
    """
    n_components: int = 8

    def compress(self, X: np.ndarray) -> Dict[str, Any]:
        X = np.asarray(X, dtype=np.float32)
        if X.ndim != 2:
            raise ValueError("PCACompressor: X must be 2D [T, n]")
        T, n = X.shape
        if T < 2:
            return {"mean": X.mean(axis=0) if T else np.zeros((n,), np.float32),
                    "components": np.zeros((0, n), np.float32),
                    "explained_var_ratio": np.zeros((0,), np.float32)}

        mean = X.mean(axis=0)
        Xc = X - mean
        # SVD for PCA
        U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
        comps = Vt[: min(self.n_components, Vt.shape[0]), :]
        # explained variance ratio
        var = (S**2) / (T - 1)
        total = np.sum(var) + 1e-12
        evr = (var / total)[: comps.shape[0]]
        return {"mean": mean.astype(np.float32),
                "components": comps.astype(np.float32),
                "explained_var_ratio": evr.astype(np.float32)}


# ---------------------------
# Metrics
# ---------------------------

@dataclass
class Metrics:
    """
    Built-in measurable signals (v1.5)
    """
    energy: float = 0.0
    csi: float = 0.0
    compression_ratio_proxy: float = 0.0
    response_variance_index: float = 0.0  # placeholder for LLM-level eval
    energy_drift: float = 0.0


# ---------------------------
# Void Instability Engine
# ---------------------------

@dataclass
class VoidInstabilityEngine:
    """
    The ONLY state-update operator.

    Dynamics:
        S_{t+1} = S_t + alpha * D(S_t) + beta * U_t - gamma * grad(E(S_t))

    with:
        D(S) = W S + sigma(S)
        E(S) = ||S||^2 + lambda * Var(H)

    We approximate grad(E) as:
        grad(||S||^2) = 2S
        grad(Var(H)) ~ 0  (history term handled via gamma scheduling)
    """
    n: int
    alpha: float = 0.10
    beta: float = 0.20
    gamma: float = 0.05
    lam: float = 0.50
    nonlin: Callable[[np.ndarray], np.ndarray] = _tanh
    seed: Optional[int] = 42
    W: np.ndarray = field(init=False)

    def __post_init__(self) -> None:
        rng = np.random.default_rng(self.seed)
        # small random weights, stabilized by spectral scaling
        W = rng.normal(0.0, 0.02, size=(self.n, self.n)).astype(np.float32)
        # spectral normalization (approx)
        try:
            # power iteration for largest singular value
            v = rng.normal(0.0, 1.0, size=(self.n,)).astype(np.float32)
            for _ in range(10):
                v = W.T @ (W @ v)
                v = v / (np.linalg.norm(v) + 1e-8)
            smax = np.linalg.norm(W @ v) + 1e-8
            W = W / smax
        except Exception:
            pass
        self.W = W

    def D(self, s: np.ndarray) -> np.ndarray:
        s = np.asarray(s, dtype=np.float32).reshape(-1)
        return (self.W @ s) + self.nonlin(s)

    def energy(self, s: np.ndarray, hist_var: float) -> float:
        s = np.asarray(s, dtype=np.float32).reshape(-1)
        e = float(np.dot(s, s)) + float(self.lam * hist_var)
        return e

    def step(self, s: np.ndarray, u: np.ndarray, hist_var: float) -> np.ndarray:
        s = np.asarray(s, dtype=np.float32).reshape(-1)
        u = np.asarray(u, dtype=np.float32).reshape(-1)
        if s.shape[0] != self.n or u.shape[0] != self.n:
            raise ValueError("VoidInstabilityEngine.step: dimension mismatch")

        # grad of ||S||^2 term
        grad = 2.0 * s

        # adaptive gamma: increase stabilization when energy rises (simple schedule)
        e = self.energy(s, hist_var)
        gamma_eff = self.gamma * (1.0 + 0.25 * np.tanh(e / max(1.0, self.n)))
        gamma_eff = float(np.clip(gamma_eff, 0.0, 1.0))

        s_next = s + (self.alpha * self.D(s)) + (self.beta * u) - (gamma_eff * grad)
        return s_next.astype(np.float32)


# ---------------------------
# Core
# ---------------------------

@dataclass
class LucidMindCoreV15:
    """
    Clean-core v1.5.

    Contract:
    - Only `update()` changes internal state.
    - update() uses VoidInstabilityEngine exclusively.
    """
    n: int = 96
    k: int = 32   # Z slice
    m: int = 32   # M slice
    p: int = 32   # C slice
    window_k: int = 256

    engine: VoidInstabilityEngine = field(init=False)
    flow: CognitiveFlow = field(init=False)
    history: FlowHistory = field(init=False)
    compressor: PCACompressor = field(init=False)

    # internal state
    S: np.ndarray = field(init=False)
    t: int = field(default=0, init=False)
    metrics: Metrics = field(default_factory=Metrics, init=False)

    def __post_init__(self) -> None:
        if self.k + self.m + self.p != self.n:
            raise ValueError("LucidMindCoreV15: k+m+p must equal n")
        self.engine = VoidInstabilityEngine(n=self.n)
        self.flow = CognitiveFlow(n=self.n)
        self.history = FlowHistory(n=self.n, window_k=self.window_k)
        self.compressor = PCACompressor(n_components=min(8, self.n))
        self.S = np.zeros((self.n,), dtype=np.float32)
        self.history.push(self.S)

    # --- Self decomposition views ---
    @property
    def Z(self) -> np.ndarray:
        return self.S[: self.k]

    @property
    def M(self) -> np.ndarray:
        return self.S[self.k : self.k + self.m]

    @property
    def C(self) -> np.ndarray:
        return self.S[self.k + self.m :]

    # --- update loop ---
    def update(self, source: CognitiveSource, x: Any, hist_k_for_var: int = 32) -> Metrics:
        """
        One step:
        - get U_t via CognitiveFlow
        - compute hist variance
        - step state using VoidInstabilityEngine
        - push into history
        - update metrics
        """
        u = self.flow.ingest(source, x)
        var = self.history.variance(hist_k_for_var)

        e_prev = self.metrics.energy
        s_next = self.engine.step(self.S, u, var)

        # commit
        self.S = s_next
        self.t += 1
        self.history.push(self.S)

        # metrics
        e = self.engine.energy(self.S, var)
        csi = 1.0 / (var + 1e-8)
        ed = abs(e - e_prev) if self.t > 1 else 0.0

        self.metrics = Metrics(
            energy=float(e),
            csi=float(csi),
            compression_ratio_proxy=float(self.n / max(1.0, self.window_k)),  # proxy only
            response_variance_index=0.0,
            energy_drift=float(ed),
        )
        return self.metrics

    def get_compressed_history(self) -> Dict[str, Any]:
        X = self.history.as_matrix()
        return self.compressor.compress(X)

    def snapshot(self) -> Dict[str, Any]:
        """
        Export a safe snapshot (no executable objects).
        """
        ch = self.get_compressed_history()
        return {
            "version": "1.5",
            "t": int(self.t),
            "n": int(self.n),
            "k": int(self.k),
            "m": int(self.m),
            "p": int(self.p),
            "state": self.S.astype(np.float32).tolist(),
            "metrics": {
                "energy": self.metrics.energy,
                "csi": self.metrics.csi,
                "compression_ratio_proxy": self.metrics.compression_ratio_proxy,
                "response_variance_index": self.metrics.response_variance_index,
                "energy_drift": self.metrics.energy_drift,
            },
            "compressed_history": {
                "mean": ch["mean"].tolist(),
                "components": ch["components"].tolist(),
                "explained_var_ratio": ch["explained_var_ratio"].tolist(),
            },
        }


# ---------------------------
# Minimal experiment (v1.5)
# ---------------------------

def run_minimal_experiment(steps: int = 200, mode: str = "stochastic") -> List[Metrics]:
    """
    Minimal benchmark loop (no LLM):
    - stochastic source OR hash-text source
    Returns per-step metrics list.
    """
    core = LucidMindCoreV15(n=96, k=32, m=32, p=32, window_k=256)

    if mode == "stochastic":
        source: CognitiveSource = RandomPerturbationSource(n=core.n, sigma=0.05, seed=7)
        inputs = [None] * steps
    elif mode == "text":
        source = TextHashEmbeddingSource(n=core.n, seed=1337)
        inputs = [f"prompt-{i}" for i in range(steps)]
    else:
        raise ValueError("mode must be 'stochastic' or 'text'")

    metrics = []
    for i in range(steps):
        m = core.update(source, inputs[i])
        metrics.append(m)

    return metrics


if __name__ == "__main__":
    # quick sanity run
    ms = run_minimal_experiment(steps=300, mode="stochastic")
    print("Last metrics:", ms[-1])
    core = LucidMindCoreV15()
    src = RandomPerturbationSource(n=core.n, sigma=0.05, seed=1)
    for i in range(50):
        core.update(src, None)
    snap = core.snapshot()
    print("Snapshot keys:", list(snap.keys()))
