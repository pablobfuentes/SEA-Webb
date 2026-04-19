"""
U4 — Read-only project logic / audit snapshot for workbench (no solver logic).

Exposes persisted assumptions, calculations, and checks from project + tree store
for transparency; document retrieval evidence stays in LocalAssistResponse only.
"""

from __future__ import annotations

import json
from typing import Any

from structural_tree_app.services.project_service import ProjectPersistenceError, ProjectService
from structural_tree_app.services.simple_span_m5_service import METHOD_LABEL as M5_METHOD_LABEL
from structural_tree_app.storage.tree_store import TreeStore
from structural_tree_app.workbench.m5_workbench_view import calculation_to_display_dict, check_to_display_dict

U4_PRELIMINARY_DISCLAIMER = (
    "Preliminary deterministic outputs (including M5) are workflow signals only: "
    "not code-compliant design, not final structural adequacy, not normative document citations."
)


def load_project_logic_audit_snapshot(ps: ProjectService, project_id: str) -> dict[str, Any]:
    """
    Load assumptions (project log), calculations, and checks (tree store) for audit UI.

    Classification mirrors ``LocalAssistOrchestrator._load_deterministic_hooks`` boundaries
    for ``method_label`` (M5 vs other) without duplicating computation.
    """
    assumptions: list[dict[str, Any]] = []
    try:
        for a in ps.load_assumptions(project_id):
            assumptions.append(
                {
                    "id": a.id,
                    "label": a.label,
                    "value": str(a.value),
                    "unit": a.unit,
                    "source_type": getattr(a.source_type, "value", str(a.source_type)),
                    "node_id": a.node_id,
                    "rationale": a.rationale or "",
                }
            )
    except ProjectPersistenceError:
        pass

    store = TreeStore.for_live_project(ps.repository, project_id)
    calculations: list[dict[str, Any]] = []
    for cid in sorted(store.list_calculation_ids()):
        c = store.load_calculation(cid)
        is_m5 = c.method_label == M5_METHOD_LABEL
        boundary = "preliminary_deterministic_m5" if is_m5 else "deterministic_computation_other"
        row = dict(calculation_to_display_dict(c))
        row["node_id"] = c.node_id
        row["authority_boundary"] = boundary
        row["is_m5_preliminary"] = is_m5
        row["inputs_json"] = json.dumps(c.inputs, indent=2, sort_keys=True)
        row["result_json"] = json.dumps(c.result, indent=2, sort_keys=True)
        calculations.append(row)

    checks: list[dict[str, Any]] = []
    for ckid in sorted(store.list_check_ids()):
        ch = store.load_check(ckid)
        row = dict(check_to_display_dict(ch))
        row["node_id"] = ch.node_id
        row["calculation_id"] = ch.calculation_id
        row["demand_json"] = json.dumps(ch.demand, indent=2, sort_keys=True)
        row["capacity_json"] = json.dumps(ch.capacity, indent=2, sort_keys=True)
        checks.append(row)

    has_any = bool(assumptions or calculations or checks)

    return {
        "assumptions": assumptions,
        "calculations": calculations,
        "checks": checks,
        "has_any": has_any,
        "workflow_href": "/workbench/project/workflow",
        "m5_method_label": M5_METHOD_LABEL,
        "preliminary_disclaimer": U4_PRELIMINARY_DISCLAIMER,
    }
