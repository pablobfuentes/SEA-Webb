from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from structural_tree_app.domain.tree_codec import canonicalize_json

# M3: only support model implemented; extend in later milestones.
SUPPORT_SIMPLE_SPAN = "simple_span"

WORKFLOW_ID = "simple_span_steel_m3"


@dataclass(frozen=True)
class SimpleSpanWorkflowInput:
    """Structured inputs for the Block 3 simple-span primary steel member workflow (SI)."""

    span_m: float
    support_condition: str = SUPPORT_SIMPLE_SPAN
    member_role: str = "primary_steel_member"
    max_depth_m: float | None = None
    architectural_restriction: str | None = None
    lightweight_preference: str | None = None
    fabrication_simplicity_preference: str | None = None
    include_optional_rolled_beam: bool = False

    def __post_init__(self) -> None:
        if self.span_m <= 0:
            raise ValueError("span_m must be positive (SI metres)")
        if self.support_condition != SUPPORT_SIMPLE_SPAN:
            raise ValueError(f"support_condition must be {SUPPORT_SIMPLE_SPAN!r} in M3")
        if self.max_depth_m is not None and self.max_depth_m <= 0:
            raise ValueError("max_depth_m must be positive when set")


def format_problem_description(inp: SimpleSpanWorkflowInput) -> str:
    """Deterministic problem text for the root PROBLEM node (workflow scope only)."""
    lines = [
        f"Workflow: {WORKFLOW_ID}",
        f"Member role: {inp.member_role}",
        f"Span: {inp.span_m:g} m (SI)",
        f"Support: {inp.support_condition}",
    ]
    if inp.max_depth_m is not None:
        lines.append(f"Max depth (optional constraint): {inp.max_depth_m:g} m")
    if inp.architectural_restriction:
        lines.append(f"Architectural restriction: {inp.architectural_restriction}")
    if inp.lightweight_preference:
        lines.append(f"Lightweight preference: {inp.lightweight_preference}")
    if inp.fabrication_simplicity_preference:
        lines.append(f"Fabrication simplicity preference: {inp.fabrication_simplicity_preference}")
    lines.append("Normative context: use project ActiveCodeContext and corpus (no claims in this milestone).")
    return "\n".join(lines)


def format_problem_title(inp: SimpleSpanWorkflowInput) -> str:
    return f"Primary steel member — simple span ({inp.span_m:g} m)"


DECISION_PROMPT = "Select primary structural solution"
SUGGESTED_TOP_K = 3


@dataclass
class SimpleSpanWorkflowResult:
    """Handles returned after persisting the M3 simple-span workflow."""

    workflow_id: str
    main_branch_id: str
    root_problem_node_id: str
    decision_node_id: str
    decision_id: str
    alternative_ids: list[str]
    alternative_titles: list[str]

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return canonicalize_json(d)


@dataclass
class SimpleSpanWorkflowPaths:
    """Stable identifiers for tests and docs (not persisted)."""

    decision_prompt: str = DECISION_PROMPT
    suggested_top_k: int = SUGGESTED_TOP_K


__all__ = [
    "DECISION_PROMPT",
    "SIMPLE_SPAN_WORKFLOW_PATHS",
    "SUGGESTED_TOP_K",
    "SUPPORT_SIMPLE_SPAN",
    "SimpleSpanWorkflowInput",
    "SimpleSpanWorkflowPaths",
    "SimpleSpanWorkflowResult",
    "WORKFLOW_ID",
    "format_problem_description",
    "format_problem_title",
]

SIMPLE_SPAN_WORKFLOW_PATHS = SimpleSpanWorkflowPaths()
