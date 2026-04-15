from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from jsonschema.exceptions import ValidationError

from structural_tree_app.domain.models import Calculation, Check, Reference
from structural_tree_app.domain.tree_codec import calculation_to_dict
from structural_tree_app.domain.tree_integrity import validate_tree_integrity
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.services.tree_workspace import TreeWorkspace
from structural_tree_app.storage.tree_store import TreeStore
from structural_tree_app.validation.json_schema import validate_calculation_payload


def _sample_calc(project_id: str, node_id: str, calc_id: str, ref_id: str) -> Calculation:
    return Calculation(
        id=calc_id,
        project_id=project_id,
        node_id=node_id,
        objective="M2 placeholder",
        method_label="block3_m2_stub",
        formula_text="(not executed in M2)",
        inputs={"w_N_per_m": 10.0, "L_m": 6.0},
        substitutions={"w_N_per_m": "10", "L_m": "6"},
        result={"note": "no numerical engine in M2"},
        formula_id=None,
        dimensional_validation=None,
        reference_ids=[ref_id],
        status="draft",
        created_at="2026-04-12T00:00:00+00:00",
        updated_at="2026-04-12T00:00:00+00:00",
    )


def _sample_check(project_id: str, node_id: str, calculation_id: str, check_id: str) -> Check:
    return Check(
        id=check_id,
        project_id=project_id,
        node_id=node_id,
        calculation_id=calculation_id,
        check_type="placeholder_utilization",
        demand={"value": 1.0},
        capacity={"value": 1.0},
        utilization_ratio=1.0,
        status="pending_inputs",
        message="M2 persistence only",
        reference_ids=[],
    )


def _sample_ref(project_id: str, doc_id: str, frag_id: str, ref_id: str) -> Reference:
    return Reference(
        id=ref_id,
        project_id=project_id,
        document_id=doc_id,
        fragment_id=frag_id,
        usage_type="evidence_link",
        citation_short="[stub]",
        citation_long="",
        quoted_context="",
    )


def test_calculation_round_trip_and_deterministic_dict(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    tw = TreeWorkspace(ps, p)
    b, root = tw.create_root_problem("P", "D")
    ref = _sample_ref(p.id, "doc_x", "frag_y", "ref_aabbccddeeff")
    calc_a = _sample_calc(p.id, root.id, "calc_aabbccddeeff", ref.id)
    calc_b = replace(
        calc_a,
        inputs={"L_m": 6.0, "w_N_per_m": 10.0},
        substitutions={"L_m": "6", "w_N_per_m": "10"},
    )
    assert calculation_to_dict(calc_a) == calculation_to_dict(calc_b)

    tw.store.save_reference(ref)
    tw.store.save_calculation(calc_a)
    loaded = tw.store.load_calculation(calc_a.id)
    assert loaded == calc_a

    text = json.dumps(calculation_to_dict(loaded), sort_keys=True)
    again = json.dumps(calculation_to_dict(loaded), sort_keys=True)
    assert text == again


def test_schema_rejects_invalid_calculation_payload() -> None:
    with pytest.raises(ValidationError):
        validate_calculation_payload({})


def test_check_and_reference_round_trip(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    tw = TreeWorkspace(ps, p)
    _, root = tw.create_root_problem("P", "D")
    ref = _sample_ref(p.id, "doc_x", "frag_y", "ref_bbccddeeff00")
    calc = replace(_sample_calc(p.id, root.id, "calc_bbccddeeff00", ref.id), reference_ids=[ref.id])
    chk = _sample_check(p.id, root.id, calc.id, "chk_ccddeeff0011")
    tw.store.save_reference(ref)
    tw.store.save_calculation(calc)
    tw.store.save_check(chk)
    assert tw.store.load_check(chk.id) == chk
    assert tw.store.load_reference(ref.id) == ref


def test_revision_snapshot_contains_calculation_and_check(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    tw = TreeWorkspace(ps, p)
    _, root = tw.create_root_problem("P", "D")
    ref = _sample_ref(p.id, "doc_x", "frag_y", "ref_ccddeeff0011")
    calc = _sample_calc(p.id, root.id, "calc_ccddeeff0011", ref.id)
    chk = _sample_check(p.id, root.id, calc.id, "chk_ddeeff001122")
    tw.store.save_reference(ref)
    tw.store.save_calculation(calc)
    tw.store.save_check(chk)

    ps.create_revision(p.id, "with calc/check")
    p2 = ps.load_project(p.id)
    rev_id = p2.version_ids[-1]

    bundle = ps.load_revision_bundle(p.id, rev_id)
    assert bundle.tree_store.load_calculation(calc.id) == calc
    assert bundle.tree_store.load_check(chk.id) == chk
    assert bundle.tree_store.load_reference(ref.id) == ref


def test_tree_integrity_linked_ids_and_cross_refs(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    tw = TreeWorkspace(ps, p)
    _, root = tw.create_root_problem("P", "D")
    ref = _sample_ref(p.id, "doc_x", "frag_y", "ref_ddeeff001122")
    calc = _sample_calc(p.id, root.id, "calc_ddeeff001122", ref.id)
    chk = _sample_check(p.id, root.id, calc.id, "chk_eeff00112233")
    tw.store.save_reference(ref)
    tw.store.save_calculation(calc)
    tw.store.save_check(chk)

    node = tw.load_node(root.id)
    tw.store.save_node(
        replace(
            node,
            linked_calculation_ids=[calc.id],
            linked_reference_ids=[ref.id],
        )
    )

    p2 = ps.load_project(p.id)
    rep = validate_tree_integrity(tw.store, p2)
    assert rep.ok, rep.errors

    # Broken link: reference file removed from ids but still listed on node (simulate stale id)
    bad = tw.load_node(root.id)
    tw.store.save_node(replace(bad, linked_reference_ids=["ref_deadbeef0000"]))
    p3 = ps.load_project(p.id)
    rep_bad = validate_tree_integrity(tw.store, p3)
    assert not rep_bad.ok
    assert any("missing reference file" in e for e in rep_bad.errors)


def test_check_node_mismatch_errors(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    tw = TreeWorkspace(ps, p)
    _, root = tw.create_root_problem("P", "D")
    _, root2 = tw.create_root_problem("P2", "D2")
    ref = _sample_ref(p.id, "doc_x", "frag_y", "ref_eeff00112233")
    calc = _sample_calc(p.id, root.id, "calc_eeff00112233", ref.id)
    chk = _sample_check(p.id, root2.id, calc.id, "chk_ff0011223344")
    tw.store.save_reference(ref)
    tw.store.save_calculation(calc)
    tw.store.save_check(chk)
    p2 = ps.load_project(p.id)
    rep = validate_tree_integrity(tw.store, p2)
    assert not rep.ok
    assert any("does not match calculation" in e for e in rep.errors)
