"""
M5: persist preliminary deterministic Calculation + Check records on a materialized working branch.

Does not call retrieval, LLMs, or alternative characterization prose — only ``catalog_key`` + workflow input.
"""

from __future__ import annotations

from dataclasses import replace

from structural_tree_app.domain.enums import SourceType
from structural_tree_app.domain.models import Assumption, Calculation, Check, new_id, utc_now
from structural_tree_app.domain.simple_span_workflow import SimpleSpanWorkflowInput
from structural_tree_app.services.deterministic.simple_span_preliminary_m5 import (
    M5_PRELIMINARY_VERSION,
    compute_preliminary_m5,
)
from structural_tree_app.services.tree_workspace import TreeWorkspace, TreeWorkspaceError


class SimpleSpanM5Error(RuntimeError):
    """Invalid M5 evaluation request."""


METHOD_LABEL = M5_PRELIMINARY_VERSION


def _existing_m5_calc_ids(tw: TreeWorkspace, node_id: str) -> list[str]:
    out: list[str] = []
    for cid in tw.store.list_calculation_ids():
        c = tw.store.load_calculation(cid)
        if c.node_id != node_id:
            continue
        if c.method_label == METHOD_LABEL:
            out.append(cid)
    return out


def run_simple_span_m5_preliminary(
    tw: TreeWorkspace,
    working_branch_id: str,
    inp: SimpleSpanWorkflowInput,
) -> tuple[Calculation, list[Check], list[Assumption]]:
    """
    Run the narrow M5 preliminary slice on the path root of ``working_branch_id``.

    Preconditions: working branch from ``materialize_working_branch_for_alternative`` (``origin_alternative_id`` set).
    Refuses duplicate M5 runs on the same path root node.
    """
    branch = tw.store.load_branch(working_branch_id)
    if not branch.origin_alternative_id:
        raise SimpleSpanM5Error("M5 requires a working branch with origin_alternative_id (materialized path)")
    if not branch.root_node_id:
        raise SimpleSpanM5Error("Working branch has no root node")

    alt = tw.store.load_alternative(branch.origin_alternative_id)
    catalog_key = alt.catalog_key
    if not catalog_key:
        raise SimpleSpanM5Error("Selected alternative has no catalog_key")

    path_root = tw.store.load_node(branch.root_node_id)
    if path_root.branch_id != working_branch_id:
        raise TreeWorkspaceError("Path root branch mismatch")

    if _existing_m5_calc_ids(tw, path_root.id):
        raise SimpleSpanM5Error(
            "M5 preliminary evaluation already exists for this path root; refuse duplicate run"
        )

    try:
        comp = compute_preliminary_m5(inp, catalog_key)
    except ValueError as e:
        raise SimpleSpanM5Error(str(e)) from e

    calc = Calculation(
        project_id=tw.project.id,
        node_id=path_root.id,
        objective="Preliminary simple-span structural fit (M5 workflow; not design adequacy)",
        method_label=METHOD_LABEL,
        formula_text=(
            "Indicative depth demand = span_m * nominal_ratio(catalog_key); "
            "fabrication alignment = ordinal score vs stated preferences."
        ),
        inputs={
            "span_m": inp.span_m,
            "catalog_key": catalog_key,
            "max_depth_m": inp.max_depth_m,
            "lightweight_preference": inp.lightweight_preference,
            "fabrication_simplicity_preference": inp.fabrication_simplicity_preference,
        },
        substitutions={k: str(v) for k, v in {
            "span_m": inp.span_m,
            "catalog_key": catalog_key,
            "max_depth_m": inp.max_depth_m,
        }.items()},
        result=comp.result,
        reference_ids=[],
        status="completed",
    )

    chk_depth = Check(
        project_id=tw.project.id,
        node_id=path_root.id,
        calculation_id=calc.id,
        check_type="preliminary_max_depth_fit",
        demand=comp.depth_check_demand,
        capacity=comp.depth_check_capacity,
        utilization_ratio=comp.depth_utilization_ratio,
        status=comp.depth_check_status,
        message=comp.depth_check_message,
        reference_ids=[],
    )

    chk_fab = Check(
        project_id=tw.project.id,
        node_id=path_root.id,
        calculation_id=calc.id,
        check_type="preliminary_fabrication_alignment",
        demand=comp.fab_check_demand,
        capacity=comp.fab_check_capacity,
        utilization_ratio=comp.fab_utilization_ratio,
        status=comp.fab_check_status,
        message=comp.fab_check_message,
        reference_ids=[],
    )

    assumptions: list[Assumption] = [
        Assumption(
            project_id=tw.project.id,
            node_id=path_root.id,
            label="m5_echo_span_m",
            value=inp.span_m,
            unit="m",
            source_type=SourceType.ASSUMED,
            confidence=1.0,
            rationale="Echo of workflow span for M5 preliminary evaluation inputs.",
            id=new_id("asm"),
        ),
        Assumption(
            project_id=tw.project.id,
            node_id=path_root.id,
            label="m5_selected_catalog_key",
            value=catalog_key,
            unit=None,
            source_type=SourceType.ASSUMED,
            confidence=1.0,
            rationale="Structural alternative system key (from persisted Alternative; not upgraded from characterization prose).",
            id=new_id("asm"),
        ),
        Assumption(
            project_id=tw.project.id,
            node_id=path_root.id,
            label="m5_preliminary_method",
            value=METHOD_LABEL,
            unit=None,
            source_type=SourceType.CALCULATED,
            confidence=1.0,
            rationale="Deterministic M5 preliminary slice version tag.",
            id=new_id("asm"),
        ),
    ]

    existing = tw.ps.load_assumptions(tw.project.id)
    merged = [*existing, *assumptions]
    tw.ps.save_assumptions(tw.project.id, merged)

    tw.store.save_calculation(calc)
    tw.store.save_check(chk_depth)
    tw.store.save_check(chk_fab)

    path_root = replace(
        path_root,
        linked_calculation_ids=[*path_root.linked_calculation_ids, calc.id],
        linked_assumption_ids=[*path_root.linked_assumption_ids, *(a.id for a in assumptions)],
        updated_at=utc_now(),
    )
    tw.store.save_node(path_root)
    tw.ps.save_project(tw.project)

    return calc, [chk_depth, chk_fab], assumptions


__all__ = ["METHOD_LABEL", "SimpleSpanM5Error", "run_simple_span_m5_preliminary"]
