from __future__ import annotations

from .reference_kernel import ReferenceKernel


class OracleKernel(ReferenceKernel):
    """
    Oracle kernel. For this publication kit, the oracle shares the same
    deterministic symbolic logic as the reference kernel, but uses a looser
    numeric state bound to represent the idealized specification ceiling.
    """
    name = "oracle_core"

    def __init__(self) -> None:
        super().__init__(n=96, history_window=256, dedupe_threshold=0.90, state_norm_limit=75.0)
