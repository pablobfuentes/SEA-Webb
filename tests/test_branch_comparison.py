from __future__ import annotations

import json
from pathlib import Path

import pytest

from structural_tree_app.domain.enums import NodeType
from structural_tree_app.domain.models import Assumption, SourceType
from structural_tree_app.services.branch_comparison import (
    BranchComparisonError,
    BranchComparisonService,
)
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.services.tree_workspace import TreeWorkspace


def _two_branch_project(tmp_path: Path) -> tuple[ProjectService, str, str, str]:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("N", "D", "es", "SI", "AISC")
    tw = TreeWorkspace(ps, p)
    b1, root1 = tw.create_root_problem("Option A", "first")
    tw.add_decision_with_options(
        b1.id,
        root1.id,
        "Choose",
        [
            ("Alt1", "d", ["fast"], ["costly"]),
            ("Alt2", "d2", ["cheap"], ["slow"]),
        ],
    )
    b2 = tw.clone_branch(b1.id, title="Option B")
    tw.store.load_branch(b2.id)
    p2 = ps.load_project(p.id)
    return ps, p2.id, b1.id, b2.id


def test_compare_two_branches_stable_json(tmp_path: Path) -> None:
    ps, pid, b1, b2 = _two_branch_project(tmp_path)
    svc = BranchComparisonService.for_live(ps, pid)
    res = svc.compare_branches([b2, b1])
    assert res.compared_branch_ids == sorted([b1, b2])
    assert len(res.rows) == 2
    by_id = {r.branch_id: r for r in res.rows}
    assert by_id[b1].node_count >= 2
    assert by_id[b2].node_count >= 2
    assert by_id[b1].qualitative_advantages
    assert by_id[b1].qualitative_disadvantages
    d = res.to_dict()
    json.dumps(d)
    assert d["project_id"] == pid


def test_discarded_branch_still_comparable(tmp_path: Path) -> None:
    ps, pid, b1, b2 = _two_branch_project(tmp_path)
    tw = TreeWorkspace(ps, ps.load_project(pid))
    tw.discard_branch(b1)
    assert tw.load_branch(b1).state.value == "discarded"
    svc = BranchComparisonService.for_live(ps, pid)
    res = svc.compare_branches([b1, b2])
    assert len(res.rows) == 2
    states = {r.branch_id: r.state for r in res.rows}
    assert states[b1] == "discarded"


def test_assumption_count_scoped_to_branch_nodes(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("N", "D", "es", "SI", "AISC")
    tw = TreeWorkspace(ps, p)
    b1, r1 = tw.create_root_problem("A", "")
    b2, r2 = tw.create_root_problem("B", "")
    asm = Assumption(
        project_id=p.id,
        node_id=r1.id,
        label="L",
        value=1.0,
        unit="m",
        source_type=SourceType.USER_CONFIRMED,
    )
    ps.save_assumptions(p.id, [asm])
    svc = BranchComparisonService.for_live(ps, p.id)
    res = svc.compare_branches([b1.id, b2.id])
    by_id = {row.branch_id: row for row in res.rows}
    assert by_id[b1.id].assumptions_count == 1
    assert by_id[b2.id].assumptions_count == 0


def test_placeholder_tags_optional(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("N", "D", "es", "SI", "AISC")
    tw = TreeWorkspace(ps, p)
    b1, _ = tw.create_root_problem("A", "")
    br = tw.store.load_branch(b1.id)
    from dataclasses import replace

    br2 = replace(
        br,
        comparison_tags=["depth:12m", "weight:heavy", "fab:high", "erect:low"],
    )
    tw.store.save_branch(br2)
    svc = BranchComparisonService.for_live(ps, p.id)
    row = svc._row_for_branch(ps.load_project(p.id), b1.id)
    assert row.estimated_depth_or_height == "12m"
    assert row.estimated_weight_category == "heavy"
    assert row.fabrication_complexity_category == "high"
    assert row.erection_complexity_category == "low"


def test_compare_requires_two_branches(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("N", "D", "es", "SI", "AISC")
    tw = TreeWorkspace(ps, p)
    b1, _ = tw.create_root_problem("A", "")
    svc = BranchComparisonService.for_live(ps, p.id)
    with pytest.raises(BranchComparisonError):
        svc.compare_branches([b1.id])


def test_missing_metrics_safe_empty_branch(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("N", "D", "es", "SI", "AISC")
    tw = TreeWorkspace(ps, p)
    b1, _ = tw.create_root_problem("A", "")
    b2, _ = tw.create_root_problem("B", "")
    svc = BranchComparisonService.for_live(ps, p.id)
    res = svc.compare_branches([b1.id, b2.id])
    for row in res.rows:
        assert row.calculations_count >= 0
        assert row.pending_checks_count >= 0
        assert row.max_subtree_depth >= 0
