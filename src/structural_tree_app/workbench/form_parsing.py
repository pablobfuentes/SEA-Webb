"""HTTP form → ``SimpleSpanWorkflowInput`` coercion only (no domain rules)."""

from __future__ import annotations

from typing import Any, Mapping

from structural_tree_app.domain.simple_span_workflow import SUPPORT_SIMPLE_SPAN, SimpleSpanWorkflowInput


def simple_span_input_from_form(form: Mapping[str, Any]) -> SimpleSpanWorkflowInput:
    """
    Map validated form keys to dataclass. Domain validation remains in ``SimpleSpanWorkflowInput.__post_init__``.
    """
    span_m = float(form["span_m"])
    support_condition = str(form.get("support_condition") or SUPPORT_SIMPLE_SPAN)
    member_role = str(form.get("member_role") or "primary_steel_member").strip() or "primary_steel_member"

    max_raw = form.get("max_depth_m")
    max_depth_m: float | None
    if max_raw is None or (isinstance(max_raw, str) and not str(max_raw).strip()):
        max_depth_m = None
    else:
        max_depth_m = float(max_raw)

    def opt_str(key: str) -> str | None:
        v = form.get(key)
        if v is None:
            return None
        s = str(v).strip()
        return s if s else None

    include = form.get("include_optional_rolled_beam")
    if isinstance(include, bool):
        include_optional_rolled_beam = include
    else:
        include_optional_rolled_beam = str(include).lower() in ("true", "1", "on", "yes")

    return SimpleSpanWorkflowInput(
        span_m=span_m,
        support_condition=support_condition,
        member_role=member_role,
        max_depth_m=max_depth_m,
        architectural_restriction=opt_str("architectural_restriction"),
        lightweight_preference=opt_str("lightweight_preference"),
        fabrication_simplicity_preference=opt_str("fabrication_simplicity_preference"),
        include_optional_rolled_beam=include_optional_rolled_beam,
    )
