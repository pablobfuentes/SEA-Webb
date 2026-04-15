"""
Narrow preliminary deterministic metrics for the simple-span steel workflow (M5).

These rules are workflow scaffolding only: not code-compliant design, not resistance checks,
not serviceability design. Do not treat outputs as authoritative adequacy evidence.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from structural_tree_app.domain.simple_span_workflow import SimpleSpanWorkflowInput

M5_PRELIMINARY_VERSION = "m5_simple_span_preliminary_v1"

# Indicative depth demand as a fraction of span (SI, metres). Tunable constants — not from design codes.
_NOMINAL_DEPTH_RATIO: dict[str, float] = {
    "truss": 0.10,
    "castellated": 0.07,
    "tapered": 0.06,
    "rolled": 0.045,
}

# Higher = more fabrication coordination (ordinal only).
_FABRICATION_RANK: dict[str, int] = {
    "truss": 4,
    "castellated": 3,
    "tapered": 2,
    "rolled": 1,
}

_FABRICATION_LABEL = ("low", "medium", "high", "very_high")


def _fab_label(rank: int) -> str:
    idx = max(0, min(len(_FABRICATION_LABEL) - 1, rank - 1))
    return _FABRICATION_LABEL[idx]


def _lightweight_fit(catalog_key: str, inp: SimpleSpanWorkflowInput) -> str:
    pref = (inp.lightweight_preference or "").strip().lower()
    wants = pref in ("high", "yes", "true", "1")
    if wants and catalog_key in {"truss", "castellated"}:
        return "favorable"
    if wants and catalog_key == "rolled":
        return "not_favorable"
    return "neutral"


def _simplicity_alignment_score(catalog_key: str, inp: SimpleSpanWorkflowInput) -> tuple[float, str]:
    pref = (inp.fabrication_simplicity_preference or "").strip().lower()
    wants = pref in ("high", "yes", "true", "1")
    if not wants:
        return 1.0, "no_fabrication_simplicity_preference"
    # Rolled easiest → highest score; truss most complex → lowest.
    scores = {"rolled": 1.0, "tapered": 0.7, "castellated": 0.45, "truss": 0.2}
    return scores.get(catalog_key, 0.5), "fabrication_simplicity_preference_active"


@dataclass(frozen=True)
class PreliminaryM5Computation:
    """Structured deterministic outputs before persistence."""

    result: dict[str, Any]
    depth_check_demand: dict[str, Any]
    depth_check_capacity: dict[str, Any]
    depth_utilization_ratio: float
    depth_check_status: str
    depth_check_message: str
    fab_check_demand: dict[str, Any]
    fab_check_capacity: dict[str, Any]
    fab_utilization_ratio: float
    fab_check_status: str
    fab_check_message: str


def compute_preliminary_m5(
    inp: SimpleSpanWorkflowInput,
    catalog_key: str,
) -> PreliminaryM5Computation:
    if catalog_key not in _NOMINAL_DEPTH_RATIO:
        raise ValueError(f"Unsupported catalog_key for M5 preliminary: {catalog_key!r}")

    ratio = _NOMINAL_DEPTH_RATIO[catalog_key]
    nominal_depth_m = inp.span_m * ratio
    fab_rank = _FABRICATION_RANK[catalog_key]
    fab_label = _fab_label(fab_rank)

    lw = _lightweight_fit(catalog_key, inp)
    align_score, align_reason = _simplicity_alignment_score(catalog_key, inp)

    result: dict[str, Any] = {
        "m5_version": M5_PRELIMINARY_VERSION,
        "disclaimer": (
            "Preliminary workflow metrics only (M5). Not code-compliant design adequacy; "
            "not a substitute for project-specific engineering."
        ),
        "authority": {
            "uses_retrieval_corpus": False,
            "uses_alternative_characterization_text": False,
            "characterization_provenance_unchanged": True,
        },
        "inputs_echo": {
            "span_m": inp.span_m,
            "catalog_key": catalog_key,
            "max_depth_m": inp.max_depth_m,
            "lightweight_preference": inp.lightweight_preference,
            "fabrication_simplicity_preference": inp.fabrication_simplicity_preference,
        },
        "nominal_depth_demand_m": round(nominal_depth_m, 6),
        "nominal_depth_ratio_of_span": ratio,
        "fabrication_complexity_rank": fab_rank,
        "fabrication_complexity_label": fab_label,
        "lightweight_fit": lw,
        "fabrication_simplicity_alignment_score": round(align_score, 6),
        "fabrication_simplicity_alignment_reason": align_reason,
    }

    # --- Check 1: max depth constraint (preliminary fit)
    if inp.max_depth_m is None:
        d_status = "not_applicable"
        d_msg = "No max_depth_m constraint; preliminary depth demand not compared."
        d_util = 0.0
        d_demand = {"nominal_depth_demand_m": round(nominal_depth_m, 6)}
        d_capacity = {"max_depth_m": None}
    else:
        d_demand = {"nominal_depth_demand_m": round(nominal_depth_m, 6)}
        d_capacity = {"max_depth_m": inp.max_depth_m}
        d_util = nominal_depth_m / inp.max_depth_m if inp.max_depth_m > 0 else 0.0
        if d_util <= 1.0:
            d_status = "pass"
            d_msg = "Nominal indicative depth fits within stated max depth (preliminary)."
        else:
            d_status = "fail"
            d_msg = (
                "Nominal indicative depth exceeds stated max depth under narrow M5 rules "
                "(preliminary; not a fabrication guarantee)."
            )

    # --- Check 2: fabrication simplicity alignment (ordinal score as pseudo-utilization)
    f_demand = {"fabrication_complexity_rank": fab_rank, "catalog_key": catalog_key}
    f_capacity = {"target": "simpler_fabrication_when_preference_active", "score_scale": 1.0}
    pref_fab = (inp.fabrication_simplicity_preference or "").strip().lower()
    wants_simple = pref_fab in ("high", "yes", "true", "1")
    if wants_simple:
        f_util = 1.0 - align_score
        if align_score >= 0.85:
            f_status = "pass"
            f_msg = "Fabrication choice aligns with stated simplicity preference (preliminary ordinal score)."
        elif align_score >= 0.4:
            f_status = "tensioned"
            f_msg = "Fabrication choice partially aligns with simplicity preference (review coordination)."
        else:
            f_status = "fail"
            f_msg = "Fabrication choice is tensioned against stated simplicity preference (preliminary)."
    else:
        f_status = "not_applicable"
        if not (inp.fabrication_simplicity_preference or "").strip():
            f_msg = "No fabrication simplicity preference; alignment check not applied."
        else:
            f_msg = (
                "Fabrication simplicity preference not set to active values (high/yes/true/1); "
                "alignment check not applied."
            )
        f_util = 0.0

    return PreliminaryM5Computation(
        result=result,
        depth_check_demand=d_demand,
        depth_check_capacity=d_capacity,
        depth_utilization_ratio=round(d_util, 6),
        depth_check_status=d_status,
        depth_check_message=d_msg,
        fab_check_demand=f_demand,
        fab_check_capacity=f_capacity,
        fab_utilization_ratio=round(f_util, 6),
        fab_check_status=f_status,
        fab_check_message=f_msg,
    )


__all__ = [
    "M5_PRELIMINARY_VERSION",
    "PreliminaryM5Computation",
    "compute_preliminary_m5",
]
