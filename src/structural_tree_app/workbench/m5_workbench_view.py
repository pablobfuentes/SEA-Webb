"""
Read-only M5 / materialized-branch projection for workbench templates (no domain rules).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from structural_tree_app.domain.models import Assumption, Calculation, Check
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.services.simple_span_m5_service import METHOD_LABEL as M5_METHOD_LABEL
from structural_tree_app.storage.tree_store import TreeStore


@dataclass(frozen=True)
class MaterializedBranchWorkbenchRow:
    branch_id: str
    title: str
    origin_alternative_id: str
    alternative_title: str
    catalog_key: str | None
    path_root_node_id: str


@dataclass(frozen=True)
class M5RunWorkbenchView:
    """Persisted preliminary deterministic M5 slice for one path root (if present)."""

    calculation: Calculation
    checks: tuple[Check, ...]
    assumptions: tuple[Assumption, ...]


def list_materialized_working_branches(
    store: TreeStore, main_trunk_branch_id: str
) -> tuple[MaterializedBranchWorkbenchRow, ...]:
    """Branches created via ``materialize_working_branch_for_alternative`` (child of trunk)."""
    rows: list[MaterializedBranchWorkbenchRow] = []
    for bid in store.list_branch_ids():
        b = store.load_branch(bid)
        if not b.origin_alternative_id:
            continue
        if b.parent_branch_id != main_trunk_branch_id:
            continue
        alt = store.load_alternative(b.origin_alternative_id)
        ck = alt.catalog_key.strip() if alt.catalog_key else None
        pr = b.root_node_id or ""
        rows.append(
            MaterializedBranchWorkbenchRow(
                branch_id=b.id,
                title=b.title,
                origin_alternative_id=alt.id,
                alternative_title=alt.title,
                catalog_key=ck,
                path_root_node_id=pr,
            )
        )
    rows.sort(key=lambda r: (r.alternative_title.lower(), r.branch_id))
    return tuple(rows)


def load_m5_view_for_branch(
    ps: ProjectService, store: TreeStore, project_id: str, working_branch_id: str
) -> M5RunWorkbenchView | None:
    """Return persisted M5 calc + checks + M5-labeled assumptions for the branch path root, if any."""
    branch = store.load_branch(working_branch_id)
    if not branch.root_node_id:
        return None
    path_root_id = branch.root_node_id
    calc_id: str | None = None
    for cid in store.list_calculation_ids():
        c = store.load_calculation(cid)
        if c.node_id == path_root_id and c.method_label == M5_METHOD_LABEL:
            calc_id = c.id
            break
    if not calc_id:
        return None
    calc = store.load_calculation(calc_id)
    checks: list[Check] = []
    for ckid in store.list_check_ids():
        ch = store.load_check(ckid)
        if ch.calculation_id == calc_id:
            checks.append(ch)
    checks.sort(key=lambda x: x.check_type)
    assumptions_all = ps.load_assumptions(project_id)
    m5_asm = tuple(
        sorted(
            (a for a in assumptions_all if a.node_id == path_root_id and a.label.startswith("m5_")),
            key=lambda a: a.label,
        )
    )
    return M5RunWorkbenchView(
        calculation=calc,
        checks=tuple(checks),
        assumptions=m5_asm,
    )


def calculation_to_display_dict(c: Calculation) -> dict[str, Any]:
    return {
        "id": c.id,
        "objective": c.objective,
        "method_label": c.method_label,
        "formula_text": c.formula_text,
        "inputs": dict(c.inputs),
        "substitutions": dict(c.substitutions),
        "result": dict(c.result) if isinstance(c.result, dict) else c.result,
        "status": c.status,
    }


def check_to_display_dict(ch: Check) -> dict[str, Any]:
    return {
        "id": ch.id,
        "check_type": ch.check_type,
        "demand": ch.demand,
        "capacity": ch.capacity,
        "utilization_ratio": ch.utilization_ratio,
        "status": ch.status,
        "message": ch.message,
    }


def assumption_to_display_dict(a: Assumption) -> dict[str, Any]:
    return {
        "label": a.label,
        "value": a.value,
        "unit": a.unit,
        "source_type": getattr(a.source_type, "value", str(a.source_type)),
        "rationale": a.rationale,
    }
