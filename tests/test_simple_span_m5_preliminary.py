from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

from structural_tree_app.domain.tree_codec import calculation_to_dict, check_to_dict
from structural_tree_app.domain.tree_integrity import validate_tree_integrity
from structural_tree_app.services.deterministic.simple_span_preliminary_m5 import compute_preliminary_m5
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.services.simple_span_m5_service import (
    METHOD_LABEL,
    SimpleSpanM5Error,
    run_simple_span_m5_preliminary,
)
from structural_tree_app.services.simple_span_steel_workflow import SimpleSpanSteelWorkflowService
from structural_tree_app.services.tree_workspace import TreeWorkspace
from structural_tree_app.domain.simple_span_workflow import SUPPORT_SIMPLE_SPAN, SimpleSpanWorkflowInput


def _workflow_and_materialized(
    tmp_path: Path,
    *,
    inp: SimpleSpanWorkflowInput,
) -> tuple[TreeWorkspace, str, str]:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    res = SimpleSpanSteelWorkflowService.setup_initial_workflow(ps, p, inp)
    tw = TreeWorkspace(ps, ps.load_project(p.id))
    alt_id = res.alternative_ids[0]
    wb, root = tw.materialize_working_branch_for_alternative(res.main_branch_id, alt_id)
    return tw, wb.id, root.id


def test_m5_preliminary_persist_and_reload(tmp_path: Path) -> None:
    inp = SimpleSpanWorkflowInput(
        span_m=12.0,
        support_condition=SUPPORT_SIMPLE_SPAN,
        max_depth_m=2.0,
        lightweight_preference="high",
        fabrication_simplicity_preference="high",
    )
    tw, wb_id, root_id = _workflow_and_materialized(tmp_path, inp=inp)
    alt_id = tw.store.load_branch(wb_id).origin_alternative_id
    assert alt_id
    catalog_before = tw.store.load_alternative(alt_id).catalog_key

    calc, checks, asms = run_simple_span_m5_preliminary(tw, wb_id, inp)
    assert calc.method_label == METHOD_LABEL
    assert calc.reference_ids == []
    assert len(checks) == 2
    assert {c.check_type for c in checks} == {"preliminary_max_depth_fit", "preliminary_fabrication_alignment"}
    assert {a.label for a in asms} == {"m5_echo_span_m", "m5_selected_catalog_key", "m5_preliminary_method"}

    root = tw.store.load_node(root_id)
    assert calc.id in root.linked_calculation_ids
    for a in asms:
        assert a.id in root.linked_assumption_ids

    loaded_calc = tw.store.load_calculation(calc.id)
    assert loaded_calc.result["authority"]["uses_retrieval_corpus"] is False
    assert loaded_calc.result["authority"]["characterization_provenance_unchanged"] is True

    tw2 = TreeWorkspace(tw.ps, tw.ps.load_project(tw.project.id))
    assert tw2.store.load_calculation(calc.id).result == loaded_calc.result
    assert tw2.ps.load_assumptions(tw.project.id) == tw.ps.load_assumptions(tw.project.id)

    rep = validate_tree_integrity(tw.store, tw.project)
    assert rep.ok, rep.errors

    alt_after = tw.store.load_alternative(alt_id)
    assert alt_after.catalog_key == catalog_before


def test_m5_revision_snapshot_contains_calc_checks_assumptions(tmp_path: Path) -> None:
    inp = SimpleSpanWorkflowInput(span_m=10.0, support_condition=SUPPORT_SIMPLE_SPAN, max_depth_m=1.5)
    tw, wb_id, root_id = _workflow_and_materialized(tmp_path, inp=inp)
    calc, checks, _ = run_simple_span_m5_preliminary(tw, wb_id, inp)

    tw.ps.create_revision(tw.project.id, "post M5")
    p2 = tw.ps.load_project(tw.project.id)
    rev_id = p2.version_ids[-1]

    bundle = tw.ps.load_revision_bundle(tw.project.id, rev_id)
    assert bundle.tree_store.load_calculation(calc.id) == calc
    for c in checks:
        assert bundle.tree_store.load_check(c.id) == c
    labels = {a.label for a in bundle.assumptions}
    assert "m5_preliminary_method" in labels
    snap_root = bundle.tree_store.load_node(root_id)
    assert calc.id in snap_root.linked_calculation_ids


def test_m5_calculation_to_dict_stable_ordering(tmp_path: Path) -> None:
    inp = SimpleSpanWorkflowInput(span_m=8.0, support_condition=SUPPORT_SIMPLE_SPAN)
    tw, wb_id, _ = _workflow_and_materialized(tmp_path, inp=inp)
    calc, checks, _ = run_simple_span_m5_preliminary(tw, wb_id, inp)
    a = json.dumps(calculation_to_dict(calc), sort_keys=True)
    b = json.dumps(calculation_to_dict(calc), sort_keys=True)
    assert a == b
    for chk in checks:
        x = json.dumps(check_to_dict(chk), sort_keys=True)
        y = json.dumps(check_to_dict(chk), sort_keys=True)
        assert x == y


def test_m5_rejects_non_materialized_branch(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    inp = SimpleSpanWorkflowInput(span_m=6.0, support_condition=SUPPORT_SIMPLE_SPAN)
    res = SimpleSpanSteelWorkflowService.setup_initial_workflow(ps, p, inp)
    tw = TreeWorkspace(ps, ps.load_project(p.id))
    with pytest.raises(SimpleSpanM5Error, match="origin_alternative_id"):
        run_simple_span_m5_preliminary(tw, res.main_branch_id, inp)


def test_m5_duplicate_run_rejected(tmp_path: Path) -> None:
    inp = SimpleSpanWorkflowInput(span_m=7.0, support_condition=SUPPORT_SIMPLE_SPAN)
    tw, wb_id, _ = _workflow_and_materialized(tmp_path, inp=inp)
    run_simple_span_m5_preliminary(tw, wb_id, inp)
    with pytest.raises(SimpleSpanM5Error, match="already exists"):
        run_simple_span_m5_preliminary(tw, wb_id, inp)


def test_m5_unsupported_catalog_key(tmp_path: Path) -> None:
    inp = SimpleSpanWorkflowInput(span_m=9.0, support_condition=SUPPORT_SIMPLE_SPAN)
    tw, wb_id, _ = _workflow_and_materialized(tmp_path, inp=inp)
    b = tw.store.load_branch(wb_id)
    alt_id = b.origin_alternative_id
    assert alt_id
    alt = tw.store.load_alternative(alt_id)
    tw.store.save_alternative(replace(alt, catalog_key="not_a_catalog_key"))
    with pytest.raises(SimpleSpanM5Error, match="Unsupported catalog_key"):
        run_simple_span_m5_preliminary(tw, wb_id, inp)


def test_m5_characterization_items_unchanged(tmp_path: Path) -> None:
    inp = SimpleSpanWorkflowInput(span_m=11.0, support_condition=SUPPORT_SIMPLE_SPAN)
    tw, wb_id, _ = _workflow_and_materialized(tmp_path, inp=inp)
    alt_id = tw.store.load_branch(wb_id).origin_alternative_id
    assert alt_id
    before = deepcopy(tw.store.load_alternative(alt_id).characterization_items)
    run_simple_span_m5_preliminary(tw, wb_id, inp)
    after = tw.store.load_alternative(alt_id).characterization_items
    assert after == before


def test_m5_service_result_matches_deterministic_core(tmp_path: Path) -> None:
    inp = SimpleSpanWorkflowInput(
        span_m=14.0,
        support_condition=SUPPORT_SIMPLE_SPAN,
        max_depth_m=0.9,
        fabrication_simplicity_preference="high",
    )
    tw, wb_id, _ = _workflow_and_materialized(tmp_path, inp=inp)
    alt_id = tw.store.load_branch(wb_id).origin_alternative_id
    ck = tw.store.load_alternative(alt_id).catalog_key
    expected = compute_preliminary_m5(inp, ck)
    calc, _, _ = run_simple_span_m5_preliminary(tw, wb_id, inp)
    assert calc.result == expected.result
    assert calc.inputs["catalog_key"] == ck


def test_m5_no_retrieval_references(tmp_path: Path) -> None:
    inp = SimpleSpanWorkflowInput(span_m=5.0, support_condition=SUPPORT_SIMPLE_SPAN)
    tw, wb_id, _ = _workflow_and_materialized(tmp_path, inp=inp)
    calc, checks, _ = run_simple_span_m5_preliminary(tw, wb_id, inp)
    assert calc.reference_ids == []
    assert all(not c.reference_ids for c in checks)
    auth = calc.result.get("authority", {})
    assert auth.get("uses_retrieval_corpus") is False
    assert auth.get("uses_alternative_characterization_text") is False
