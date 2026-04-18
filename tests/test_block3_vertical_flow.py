"""
Block 3 M7 — end-to-end vertical acceptance for the simple-span steel workflow slice.

Validates in one scenario:
  M3 simple-span workflow setup
  M4 alternative characterization (provenance-bearing items)
  materialized working branch for a selected catalog alternative
  M5 deterministic preliminary Calculation + Checks (method_label slice)
  M6 branch comparison enrichment (including check rows via calculation_id linkage)
  revision snapshot replay (comparison + tree artifacts reconstructible from snapshot)

Check discovery model: M6 discovers preliminary checks by scanning persisted Check rows and
filtering on calculation_id belonging to the M5 calculation(s) for that branch — not by
direct node→check listing. The full flow remains reconstructible because Calculation and Check
ids are stable in the tree store and revision copy.
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

from structural_tree_app.services.branch_comparison import BranchComparisonResult, BranchComparisonService
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.services.simple_span_m5_service import METHOD_LABEL as M5_METHOD_LABEL, run_simple_span_m5_preliminary
from structural_tree_app.services.simple_span_steel_workflow import SimpleSpanSteelWorkflowService
from structural_tree_app.services.tree_workspace import TreeWorkspace
from structural_tree_app.domain.simple_span_workflow import SUPPORT_SIMPLE_SPAN, SimpleSpanWorkflowInput


def _comparison_equivalent_except_generated_at(
    live: BranchComparisonResult, snap: BranchComparisonResult
) -> None:
    assert live.project_id == snap.project_id
    assert live.compared_branch_ids == snap.compared_branch_ids
    assert live.citation_trace_authority == snap.citation_trace_authority
    assert len(live.rows) == len(snap.rows)
    live_by = {r.branch_id: r for r in live.rows}
    snap_by = {r.branch_id: r for r in snap.rows}
    assert live_by.keys() == snap_by.keys()
    for bid in sorted(live_by.keys()):
        a, b = live_by[bid], snap_by[bid]
        assert a.title == b.title
        assert a.state == b.state
        assert a.calculations_count == b.calculations_count
        assert a.assumptions_count == b.assumptions_count
        assert a.pending_checks_count == b.pending_checks_count
        assert a.m5_preliminary == b.m5_preliminary
        assert len(a.m5_checks_via_calculation_id) == len(b.m5_checks_via_calculation_id)
        # Stable ordering: same check_type + status per position (ids may match across snapshot)
        for ca, cb in zip(
            sorted(a.m5_checks_via_calculation_id, key=lambda x: x["check_type"]),
            sorted(b.m5_checks_via_calculation_id, key=lambda x: x["check_type"]),
        ):
            assert ca["check_type"] == cb["check_type"]
            assert ca["status"] == cb["status"]
            assert ca["utilization_ratio"] == cb["utilization_ratio"]


def test_block3_m7_vertical_e2e_simple_span_castellated_m5_m6_revision_replay(tmp_path: Path) -> None:
    """
    Single coherent scenario: 15 m simple span, four alternatives (optional rolled enabled),
    select castellated / cellular path, preliminary M5 on materialized branch, compare trunk vs
    working branch, then replay comparison from latest revision snapshot.
    """
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("M7 E2E", "Block 3 vertical acceptance", "es", "SI", "AISC")
    inp = SimpleSpanWorkflowInput(
        span_m=15.0,
        support_condition=SUPPORT_SIMPLE_SPAN,
        max_depth_m=0.85,
        lightweight_preference="high",
        fabrication_simplicity_preference="medium",
        include_optional_rolled_beam=True,
    )
    res = SimpleSpanSteelWorkflowService.setup_initial_workflow(ps, p, inp)
    assert len(res.alternative_ids) == 4

    tw = TreeWorkspace(ps, ps.load_project(p.id))
    cast_alt_id = next(
        aid
        for aid in res.alternative_ids
        if tw.store.load_alternative(aid).catalog_key == "castellated"
    )
    alt0 = tw.store.load_alternative(cast_alt_id)
    assert alt0.characterization_items, "M4 must persist characterization_items"
    provenances = {
        (it.get("provenance") if isinstance(it, dict) else getattr(it, "provenance", None))
        for it in alt0.characterization_items
    }
    assert "workflow_heuristic" in provenances
    assert ("retrieval_backed" in provenances) or ("not_yet_evidenced" in provenances)

    wb, _path_root = tw.materialize_working_branch_for_alternative(res.main_branch_id, cast_alt_id)
    calc, checks, _asms = run_simple_span_m5_preliminary(tw, wb.id, inp)
    assert calc.method_label == M5_METHOD_LABEL
    assert len(checks) == 2
    assert {c.calculation_id for c in checks} == {calc.id}

    branch_ids = sorted([res.main_branch_id, wb.id])
    comp_live = BranchComparisonService.for_live(ps, p.id).compare_branches(branch_ids)
    assert comp_live.citation_trace_authority == "internal_trace_only"
    rows = {r.branch_id: r for r in comp_live.rows}
    assert rows[wb.id].m5_preliminary is not None
    assert rows[wb.id].m5_preliminary["classification"] == "preliminary_workflow_signal"
    assert rows[wb.id].m5_preliminary["method_label"] == M5_METHOD_LABEL
    assert len(rows[wb.id].m5_checks_via_calculation_id) == 2
    for src in ("m5_preliminary", "m5_checks_via_calculation_id"):
        assert rows[wb.id].comparison_field_sources[src] == "m5_deterministic_preliminary"
    assert rows[res.main_branch_id].m5_preliminary is None

    d_live = comp_live.to_dict()
    json.dumps(d_live, sort_keys=True)

    ps.create_revision(p.id, "Block 3 M7 E2E — post M5/M6")
    p_after = ps.load_project(p.id)
    rev_id = p_after.version_ids[-1]

    bundle = ps.load_revision_bundle(p.id, rev_id)
    assert bundle.tree_store.load_calculation(calc.id).method_label == M5_METHOD_LABEL
    snap_chk_ids = {bundle.tree_store.load_check(c.id).id for c in checks}
    assert snap_chk_ids == {c.id for c in checks}

    comp_snap = BranchComparisonService.for_revision_snapshot(ps, p.id, rev_id).compare_branches(branch_ids)
    _comparison_equivalent_except_generated_at(comp_live, comp_snap)

    d_snap = comp_snap.to_dict()
    d_snap.pop("generated_at", None)
    d_live2 = deepcopy(d_live)
    d_live2.pop("generated_at", None)
    assert d_snap["compared_branch_ids"] == d_live2["compared_branch_ids"]
    assert d_snap["citation_trace_authority"] == d_live2["citation_trace_authority"]
