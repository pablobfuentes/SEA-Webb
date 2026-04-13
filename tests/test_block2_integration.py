from __future__ import annotations

import json
from pathlib import Path

from structural_tree_app.domain.enums import NormativeClassification, NodeType
from structural_tree_app.services.branch_comparison import BranchComparisonService
from structural_tree_app.services.document_service import DocumentIngestionService
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.services.retrieval_service import DocumentRetrievalService
from structural_tree_app.services.tree_workspace import TreeWorkspace


def test_end_to_end_project_tree_ingest_retrieve_compare(tmp_path: Path) -> None:
    """
    Block 2 integrated flow: create project → tree (two branches) → ingest doc →
    approve/activate → normative retrieval → branch comparison (live + revision snapshot).
    """
    ws = tmp_path / "workspace"
    ps = ProjectService(ws)
    p = ps.create_project("Integration", "E2E", "es", "SI", "AISC")
    tw = TreeWorkspace(ps, p)
    b1, r1 = tw.create_root_problem("Beam path A", "option a")
    tw.add_child_node(b1.id, r1.id, NodeType.CRITERION, "Deflection", "L/360")
    b2, r2 = tw.create_root_problem("Beam path B", "option b")
    tw.add_child_node(b2.id, r2.id, NodeType.CRITERION, "Deflection", "L/400")

    src = tmp_path / "norm.txt"
    src.write_text(
        "Steel beam flexure design limit state and resistance factor provisions for bending.",
        encoding="utf-8",
    )
    ing = DocumentIngestionService(ps, p.id)
    ir = ing.ingest_local_file(
        src,
        title="Steel ref",
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="AISC",
    )
    assert ir.document
    ing.approve_document(ir.document.id)
    ing.activate_for_normative_corpus(ir.document.id)

    ret = DocumentRetrievalService(ps, p.id)
    rr = ret.search("flexure bending", citation_authority="normative_active_primary")
    assert rr.status == "ok"
    assert rr.hits
    assert rr.hits[0].content_hash

    ps.create_revision(p.id, "pre-compare")
    p_live = ps.load_project(p.id)
    rev_id = p_live.version_ids[-1]

    cmp_live = BranchComparisonService.for_live(ps, p.id)
    res_live = cmp_live.compare_branches([b1.id, b2.id])
    assert len(res_live.rows) == 2
    assert res_live.citation_trace_authority == "internal_trace_only"
    for row in res_live.rows:
        assert row.metric_provenance.get("citation_traces") == "document_trace_pending"
        assert row.metric_provenance.get("assumptions_count") == "computed"

    cmp_snap = BranchComparisonService.for_revision_snapshot(ps, p.id, rev_id)
    res_snap = cmp_snap.compare_branches([b1.id, b2.id])
    assert res_snap.compared_branch_ids == res_live.compared_branch_ids
    assert len(res_snap.rows) == len(res_live.rows)

    json.dumps(res_live.to_dict(), sort_keys=True)
    json.dumps(res_snap.to_dict(), sort_keys=True)


def test_comparison_json_deterministic_ordering(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("N", "D", "es", "SI", "AISC")
    tw = TreeWorkspace(ps, p)
    b1, _ = tw.create_root_problem("A", "")
    b2, _ = tw.create_root_problem("B", "")
    svc = BranchComparisonService.for_live(ps, p.id)
    r1 = svc.compare_branches([b2.id, b1.id])
    r2 = svc.compare_branches([b1.id, b2.id])
    assert r1.compared_branch_ids == r2.compared_branch_ids
    assert [x.branch_id for x in r1.rows] == [x.branch_id for x in r2.rows]
