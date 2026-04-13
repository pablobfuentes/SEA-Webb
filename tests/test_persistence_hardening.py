from __future__ import annotations

from pathlib import Path

import pytest

from structural_tree_app.domain.tree_integrity import validate_tree_integrity
from structural_tree_app.services.project_service import ProjectPersistenceError, ProjectService
from structural_tree_app.services.tree_workspace import TreeWorkspace


def test_revision_write_once(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    rid = p.version_ids[0]
    with pytest.raises(ProjectPersistenceError, match="write-once"):
        ps._write_revision_snapshot(p.id, rid, p, rationale="duplicate", parent_revision_id=None)


def test_revision_bundle_isolated_from_live_project(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("Original", "D", "es", "SI", "AISC")
    first_rev = p.version_ids[0]
    p.name = "Mutated live name"
    ps.save_project(p)
    bundle = ps.load_revision_bundle(p.id, first_rev)
    assert bundle.project.name == "Original"
    assert bundle.project.id == p.id
    # Tree store points at revision snapshot path, not live tree/
    assert "revisions" in bundle.tree_store.rel_root
    assert bundle.tree_store.rel_root.endswith(f"/revisions/{first_rev}/tree")


def test_tree_integrity_after_root_problem(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    tw = TreeWorkspace(ps, p)
    tw.create_root_problem("T", "D")
    p2 = ps.load_project(p.id)
    rep = validate_tree_integrity(tw.store, p2)
    assert rep.ok, rep.errors
