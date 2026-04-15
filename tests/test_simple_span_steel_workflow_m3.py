from __future__ import annotations

import json
from pathlib import Path

import pytest

from structural_tree_app.domain.enums import BranchState
from structural_tree_app.domain.models import Branch
from structural_tree_app.domain.simple_span_alternative_catalog import rank_eligible_alternatives
from structural_tree_app.domain.enums import NodeType
from structural_tree_app.domain.simple_span_workflow import (
    DECISION_PROMPT,
    SIMPLE_SPAN_WORKFLOW_PATHS,
    SUGGESTED_TOP_K,
    SUPPORT_SIMPLE_SPAN,
    SimpleSpanWorkflowInput,
    WORKFLOW_ID,
    format_problem_description,
)
from structural_tree_app.domain.tree_integrity import validate_tree_integrity
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.services.simple_span_steel_workflow import (
    SimpleSpanSteelWorkflowError,
    SimpleSpanSteelWorkflowService,
)
from structural_tree_app.services.tree_workspace import TreeWorkspace


def _base_input(**kwargs: object) -> SimpleSpanWorkflowInput:
    defaults: dict[str, object] = {
        "span_m": 12.0,
        "support_condition": SUPPORT_SIMPLE_SPAN,
    }
    defaults.update(kwargs)
    return SimpleSpanWorkflowInput(**defaults)  # type: ignore[arg-type]


def test_m3_valid_workflow_generates_decision_and_alternatives(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    inp = _base_input(span_m=10.0, architectural_restriction="headroom limited")
    res = SimpleSpanSteelWorkflowService.setup_initial_workflow(ps, p, inp)
    assert res.workflow_id == WORKFLOW_ID
    assert len(res.alternative_titles) >= 3

    p2 = ps.load_project(p.id)
    tw = TreeWorkspace(ps, p2)
    root = tw.load_node(res.root_problem_node_id)
    assert root.node_type == NodeType.PROBLEM
    assert "10 m" in root.title or "10" in root.title
    assert format_problem_description(inp) == root.description

    dec = tw.store.load_decision(res.decision_id)
    assert dec.prompt == DECISION_PROMPT
    assert len(dec.alternative_ids) == 3
    dnode = tw.load_node(res.decision_node_id)
    assert dnode.node_type == NodeType.DECISION
    assert dnode.title == DECISION_PROMPT


def test_m3_persistence_reload(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    inp = _base_input(span_m=8.0)
    res = SimpleSpanSteelWorkflowService.setup_initial_workflow(ps, p, inp)

    p3 = ps.load_project(p.id)
    tw = TreeWorkspace(ps, p3)
    for aid in res.alternative_ids:
        alt = tw.store.load_alternative(aid)
        assert alt.pros == [] and alt.cons == []
        assert alt.catalog_key != ""
        assert alt.suggestion_provenance == "workflow_heuristic"
        provs = {item["provenance"] for item in alt.characterization_items}
        assert "workflow_heuristic" in provs
        assert "manual_placeholder" in provs
        assert "not_yet_evidenced" in provs or "retrieval_backed" in provs


def test_m3_result_to_dict_deterministic(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    inp = _base_input(span_m=6.0)
    res = SimpleSpanSteelWorkflowService.setup_initial_workflow(ps, p, inp)
    a = json.dumps(res.to_dict(), sort_keys=True)
    b = json.dumps(res.to_dict(), sort_keys=True)
    assert a == b


def test_m3_optional_rolled_fourth_alternative(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    inp = _base_input(span_m=15.0, include_optional_rolled_beam=True)
    res = SimpleSpanSteelWorkflowService.setup_initial_workflow(ps, p, inp)
    assert len(res.alternative_titles) >= 4
    assert "Rolled or built-up beam (conventional)" in res.alternative_titles

    ps2 = ProjectService(tmp_path / "ws2")
    p2 = ps2.create_project("Q", "D", "es", "SI", "AISC")
    inp2 = _base_input(span_m=15.0, include_optional_rolled_beam=False)
    res2 = SimpleSpanSteelWorkflowService.setup_initial_workflow(ps2, p2, inp2)
    assert len(res2.alternative_titles) == 3


def test_m31_catalog_ranking_is_deterministic_and_top3_marked(tmp_path: Path) -> None:
    inp = _base_input(
        span_m=14.0,
        include_optional_rolled_beam=True,
        lightweight_preference="high",
        architectural_restriction="tight envelope",
    )
    first = rank_eligible_alternatives(inp)
    second = rank_eligible_alternatives(inp)
    assert [(r.entry.key, r.score, r.rank, r.suggested) for r in first] == [
        (r.entry.key, r.score, r.rank, r.suggested) for r in second
    ]
    assert len([r for r in first if r.suggested]) == SUGGESTED_TOP_K
    assert all(first[i].score >= first[i + 1].score for i in range(len(first) - 1))

    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    res = SimpleSpanSteelWorkflowService.setup_initial_workflow(ps, p, inp)
    tw = TreeWorkspace(ps, ps.load_project(p.id))
    alternatives = [tw.store.load_alternative(aid) for aid in res.alternative_ids]
    suggested = [a for a in alternatives if a.suggested]
    assert len(suggested) == SUGGESTED_TOP_K
    assert sorted(a.suggestion_rank for a in suggested) == [1, 2, 3]
    assert all(a.suggestion_score is not None for a in alternatives)
    assert all(a.suggestion_provenance == "workflow_heuristic" for a in alternatives)


def test_m3_invalid_input_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="span_m"):
        SimpleSpanWorkflowInput(span_m=-1.0)

    with pytest.raises(ValueError, match="support_condition"):
        SimpleSpanWorkflowInput(span_m=5.0, support_condition="fixed-fixed")

    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    tw = TreeWorkspace(ps, p)
    tw.create_root_problem("X", "Y")
    p4 = ps.load_project(p.id)
    with pytest.raises(SimpleSpanSteelWorkflowError, match="already has a root"):
        SimpleSpanSteelWorkflowService.setup_initial_workflow(
            ps, p4, _base_input(span_m=5.0)
        )


def test_m3_revision_snapshot_preserves_workflow(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    res = SimpleSpanSteelWorkflowService.setup_initial_workflow(ps, p, _base_input(span_m=9.0))
    ps.create_revision(p.id, "after m3")

    p2 = ps.load_project(p.id)
    rev_id = p2.version_ids[-1]
    bundle = ps.load_revision_bundle(p.id, rev_id)

    snap = bundle.tree_store
    assert len(snap.list_decision_ids()) == 1
    assert len(snap.list_alternative_ids()) >= 3
    d = snap.load_decision(res.decision_id)
    assert d.prompt == DECISION_PROMPT
    root = snap.load_node(res.root_problem_node_id)
    assert root.node_type == NodeType.PROBLEM


def test_m3_branch_discard_and_reopen(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    SimpleSpanSteelWorkflowService.setup_initial_workflow(ps, p, _base_input(span_m=7.0))
    p2 = ps.load_project(p.id)
    tw = TreeWorkspace(ps, p2)
    bid = tw.store.list_branch_ids()[0]
    tw.discard_branch(bid)
    b = tw.load_branch(bid)
    assert b.state.value == "discarded"
    tw.reopen_branch(bid)
    b2 = tw.load_branch(bid)
    assert b2.state.value == "active"
    dec_id = tw.store.list_decision_ids()[0]
    assert tw.store.load_decision(dec_id).prompt == DECISION_PROMPT


def test_m3_tree_integrity_ok(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    SimpleSpanSteelWorkflowService.setup_initial_workflow(ps, p, _base_input(span_m=11.0))
    p2 = ps.load_project(p.id)
    tw = TreeWorkspace(ps, p2)
    rep = validate_tree_integrity(tw.store, p2)
    assert rep.ok, rep.errors


def test_m31_backward_compat_old_alternative_payload_defaults(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    tw = TreeWorkspace(ps, p)
    branch, root = tw.create_root_problem("legacy", "legacy")
    _, decision, _ = tw.add_decision_with_options(branch.id, root.id, "legacy decision", [("A", "B", [], [])])
    alt_id = decision.alternative_ids[0]
    alt_path = (tmp_path / "ws" / p.id / "tree" / "alternatives" / f"{alt_id}.json")
    payload = json.loads(alt_path.read_text(encoding="utf-8"))
    payload.pop("catalog_key", None)
    payload.pop("suggested", None)
    payload.pop("suggestion_rank", None)
    payload.pop("suggestion_score", None)
    payload.pop("suggestion_provenance", None)
    alt_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    loaded = tw.store.load_alternative(alt_id)
    assert loaded.catalog_key == ""
    assert loaded.suggested is False
    assert loaded.suggestion_rank is None
    assert loaded.suggestion_score is None
    assert loaded.suggestion_provenance == "workflow_heuristic"


def test_m31_branch_origin_alternative_integrity(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    res = SimpleSpanSteelWorkflowService.setup_initial_workflow(ps, p, _base_input(span_m=12.0))
    p2 = ps.load_project(p.id)
    tw = TreeWorkspace(ps, p2)
    trunk = tw.load_branch(res.main_branch_id)
    origin_alt_id = res.alternative_ids[0]
    child = Branch(
        project_id=p2.id,
        title="Selected alternative branch",
        description="materialized from alternative",
        origin_decision_node_id=res.decision_node_id,
        origin_alternative_id=origin_alt_id,
        root_node_id=trunk.root_node_id,
        state=BranchState.PENDING,
    )
    tw.store.save_branch(child)
    p2.branch_ids.append(child.id)
    tw.ps.save_project(p2)
    rep = validate_tree_integrity(tw.store, p2)
    assert rep.ok, rep.errors
