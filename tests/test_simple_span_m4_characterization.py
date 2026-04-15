from __future__ import annotations

from pathlib import Path

from structural_tree_app.domain.characterization_provenance import (
    PROVENANCE_MANUAL_PLACEHOLDER,
    PROVENANCE_NOT_YET_EVIDENCED,
    PROVENANCE_RETRIEVAL_BACKED,
    PROVENANCE_WORKFLOW_HEURISTIC,
)
from structural_tree_app.domain.enums import NormativeClassification
from structural_tree_app.domain.tree_integrity import validate_tree_integrity
from structural_tree_app.services.document_service import DocumentIngestionService
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.services.simple_span_steel_workflow import SimpleSpanSteelWorkflowService
from structural_tree_app.services.tree_workspace import TreeWorkspace
from structural_tree_app.domain.simple_span_workflow import SUPPORT_SIMPLE_SPAN, SimpleSpanWorkflowInput


def _ingest_normative_span_keywords(tmp_path: Path) -> tuple[ProjectService, str]:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    src = tmp_path / "steel.txt"
    src.write_text(
        "Steel truss triangulation systems for long steel span projects. "
        "Castellated cellular beam openings reduce weight. "
        "Tapered variable inertia beam profiles track demand. "
        "Rolled beam flexure and limit states per steel design provisions.",
        encoding="utf-8",
    )
    ing = DocumentIngestionService(ps, p.id)
    res = ing.ingest_local_file(
        src,
        title="Steel keywords",
        topics=["steel", "beams"],
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="AISC",
    )
    assert res.document
    ing.approve_document(res.document.id)
    ing.activate_for_normative_corpus(res.document.id)
    return ps, p.id


def test_m4_without_corpus_marks_not_yet_evidenced(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    inp = SimpleSpanWorkflowInput(span_m=10.0, support_condition=SUPPORT_SIMPLE_SPAN)
    res = SimpleSpanSteelWorkflowService.setup_initial_workflow(ps, p, inp)
    tw = TreeWorkspace(ps, ps.load_project(p.id))
    for aid in res.alternative_ids:
        alt = tw.store.load_alternative(aid)
        provs = [item["provenance"] for item in alt.characterization_items]
        assert PROVENANCE_WORKFLOW_HEURISTIC in provs
        assert PROVENANCE_MANUAL_PLACEHOLDER in provs
        assert PROVENANCE_NOT_YET_EVIDENCED in provs
        assert PROVENANCE_RETRIEVAL_BACKED not in provs
    rep = validate_tree_integrity(tw.store, tw.project)
    assert rep.ok, rep.errors


def test_m4_with_corpus_adds_retrieval_backed_and_references(tmp_path: Path) -> None:
    ps, pid = _ingest_normative_span_keywords(tmp_path)
    p = ps.load_project(pid)
    inp = SimpleSpanWorkflowInput(span_m=15.0, support_condition=SUPPORT_SIMPLE_SPAN, include_optional_rolled_beam=True)
    res = SimpleSpanSteelWorkflowService.setup_initial_workflow(ps, p, inp)
    tw = TreeWorkspace(ps, ps.load_project(p.id))
    assert tw.store.list_reference_ids()
    any_retrieval = False
    for aid in res.alternative_ids:
        alt = tw.store.load_alternative(aid)
        provs = [item["provenance"] for item in alt.characterization_items]
        if PROVENANCE_RETRIEVAL_BACKED in provs:
            any_retrieval = True
            for item in alt.characterization_items:
                if item["provenance"] == PROVENANCE_RETRIEVAL_BACKED:
                    assert item.get("reference_id")
                    tw.store.load_reference(item["reference_id"])
    assert any_retrieval
    rep = validate_tree_integrity(tw.store, tw.project)
    assert rep.ok, rep.errors


def test_m4_materialize_working_branch(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    inp = SimpleSpanWorkflowInput(span_m=8.0, support_condition=SUPPORT_SIMPLE_SPAN)
    res = SimpleSpanSteelWorkflowService.setup_initial_workflow(ps, p, inp)
    tw = TreeWorkspace(ps, ps.load_project(p.id))
    alt_id = res.alternative_ids[0]
    nb, root = tw.materialize_working_branch_for_alternative(res.main_branch_id, alt_id)
    assert nb.origin_alternative_id == alt_id
    assert nb.origin_decision_node_id == res.decision_node_id
    assert root.branch_id == nb.id
    dec = tw.store.load_decision(res.decision_id)
    assert dec.selected_alternative_id == alt_id
    rep = validate_tree_integrity(tw.store, tw.project)
    assert rep.ok, rep.errors


def test_m4_clone_branch_preserves_characterization(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    inp = SimpleSpanWorkflowInput(span_m=9.0, support_condition=SUPPORT_SIMPLE_SPAN)
    res = SimpleSpanSteelWorkflowService.setup_initial_workflow(ps, p, inp)
    tw = TreeWorkspace(ps, ps.load_project(p.id))
    src_alt = tw.store.load_alternative(res.alternative_ids[0])
    n = len(src_alt.characterization_items)
    clone = tw.clone_branch(res.main_branch_id, title="copy")
    tw2 = TreeWorkspace(ps, ps.load_project(p.id))
    dec_on_clone = None
    for did in tw2.store.list_decision_ids():
        d = tw2.store.load_decision(did)
        if tw2.load_node(d.decision_node_id).branch_id == clone.id:
            dec_on_clone = d
            break
    assert dec_on_clone is not None
    ca = tw2.store.load_alternative(dec_on_clone.alternative_ids[0])
    assert len(ca.characterization_items) == n
    assert {x["provenance"] for x in ca.characterization_items} == {
        x["provenance"] for x in src_alt.characterization_items
    }
