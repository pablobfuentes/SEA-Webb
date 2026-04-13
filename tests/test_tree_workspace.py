from __future__ import annotations

from pathlib import Path

import pytest

from structural_tree_app.domain.enums import BranchState, NodeType
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.services.tree_workspace import TreeWorkspace, TreeWorkspaceError


def test_root_problem_persists_branch_and_node(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("N", "D", "es", "SI", "AISC")
    tw = TreeWorkspace(ps, p)
    b, root = tw.create_root_problem("T", "D")
    loaded_b = tw.load_branch(b.id)
    loaded_n = tw.load_node(root.id)
    assert loaded_b.state == BranchState.ACTIVE
    assert loaded_n.node_type == NodeType.PROBLEM
    assert loaded_n.branch_id == b.id
    assert p.root_node_id == root.id


def test_discard_and_reopen_branch(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("N", "D", "es", "SI", "AISC")
    tw = TreeWorkspace(ps, p)
    b, _root = tw.create_root_problem("T", "D")
    tw.discard_branch(b.id)
    assert tw.load_branch(b.id).state == BranchState.DISCARDED
    tw.reopen_branch(b.id)
    assert tw.load_branch(b.id).state == BranchState.ACTIVE


def test_clone_branch_subtree_integrity(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("N", "D", "es", "SI", "AISC")
    tw = TreeWorkspace(ps, p)
    b, root = tw.create_root_problem("Root", "D")
    tw.add_child_node(b.id, root.id, NodeType.PROBLEM, "Child", "c")
    nb = tw.clone_branch(b.id, title="Clone")
    nodes = tw.store.load_all_nodes()
    by_branch: dict[str, list] = {}
    for n in nodes:
        by_branch.setdefault(n.branch_id, []).append(n)
    assert len(by_branch[b.id]) == 2
    assert len(by_branch[nb.id]) == 2
    paths = tw.list_branch_paths(nb.id)
    assert len(paths) == 1
    assert len(paths[0]) == 2


def test_invalid_branch_transition(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("N", "D", "es", "SI", "AISC")
    tw = TreeWorkspace(ps, p)
    b, _ = tw.create_root_problem("T", "D")
    tw.discard_branch(b.id)
    with pytest.raises(TreeWorkspaceError):
        tw.activate_branch(b.id)


def test_revision_includes_assumptions_and_tree(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("N", "D", "es", "SI", "AISC")
    tw = TreeWorkspace(ps, p)
    tw.create_root_problem("T", "D")
    ps.create_revision(p.id, "snap")
    rev_id = ps.load_project(p.id).version_ids[-1]
    base = tmp_path / "ws" / p.id / "revisions" / rev_id
    assert (base / "assumptions_snapshot.json").is_file()
    assert (base / "tree" / "branches").is_dir()
    snap_asm = ps.load_revision_snapshot_assumptions(p.id, rev_id)
    assert snap_asm == []


def test_get_subtree(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("N", "D", "es", "SI", "AISC")
    tw = TreeWorkspace(ps, p)
    b, root = tw.create_root_problem("T", "D")
    c = tw.add_child_node(b.id, root.id, NodeType.PROBLEM, "C", "")
    sub = tw.get_subtree(b.id, root.id)
    assert len(sub) == 2
    ids = {n.id for n in sub}
    assert root.id in ids and c.id in ids
