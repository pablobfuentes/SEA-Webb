"""Deterministic, testable engineering slices (no LLM; not normative authority)."""

from structural_tree_app.services.deterministic.simple_span_preliminary_m5 import (
    M5_PRELIMINARY_VERSION,
    PreliminaryM5Computation,
    compute_preliminary_m5,
)

__all__ = [
    "M5_PRELIMINARY_VERSION",
    "PreliminaryM5Computation",
    "compute_preliminary_m5",
]
