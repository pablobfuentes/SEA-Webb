from __future__ import annotations

import json
from pathlib import Path

import pytest

from structural_tree_app.domain.models import Assumption, Project
from structural_tree_app.domain.enums import SourceType
from structural_tree_app.services.project_service import ProjectPersistenceError, ProjectService


def test_create_load_round_trip(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ps = ProjectService(ws)
    p = ps.create_project(
        name="Test",
        description="D",
        language="es",
        unit_system="SI",
        primary_standard_family="AISC",
    )
    loaded = ps.load_project(p.id)
    assert loaded.id == p.id
    assert loaded.name == "Test"
    assert loaded.active_code_context.primary_standard_family == "AISC"
    assert loaded.head_revision_id is not None
    assert len(loaded.version_ids) == 1


def test_save_preserves_core_fields(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("N", "D", "en", "SI", "EC3")
    p.description = "Updated"
    ps.save_project(p)
    again = ps.load_project(p.id)
    assert again.description == "Updated"
    assert again.unit_system == "SI"
    assert again.language == "en"


def test_create_revision_and_list(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("N", "D", "es", "SI", "AISC")
    first_head = p.head_revision_id
    meta = ps.create_revision(p.id, "checkpoint")
    revs = ps.list_revisions(p.id)
    assert len(revs) == 2
    assert revs[-1].id == meta.id
    assert revs[-1].rationale == "checkpoint"
    assert revs[-1].parent_revision_id == first_head
    latest = ps.load_project(p.id)
    assert latest.head_revision_id == meta.id
    assert len(latest.version_ids) == 2


def test_revision_snapshot_matches_project_json(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("N", "D", "es", "SI", "AISC")
    ps.create_revision(p.id, "second")
    loaded = ps.load_project(p.id)
    snap = ps.load_revision_snapshot_project(loaded.id, loaded.version_ids[-1])
    assert snap.id == loaded.id
    assert snap.head_revision_id == loaded.head_revision_id


def test_invalid_project_json_fails(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ps = ProjectService(ws)
    p = ps.create_project("N", "D", "es", "SI", "AISC")
    bad = ws / p.id / "project.json"
    bad.write_text('{"id": "x"}', encoding="utf-8")
    with pytest.raises(ProjectPersistenceError):
        ps.load_project(p.id)


def test_example_json_maps_to_create_project(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[1]
    example = json.loads((root / "examples" / "example_project.json").read_text(encoding="utf-8"))
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project(
        name=example["project_name"],
        description=example["problem"],
        language="es",
        unit_system="SI",
        primary_standard_family=example["active_standard_family"],
    )
    loaded = ps.load_project(p.id)
    assert loaded.name == example["project_name"]
    assert loaded.active_code_context.primary_standard_family == example["active_standard_family"]


def test_assumptions_round_trip(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("N", "D", "es", "SI", "AISC")
    asm = Assumption(
        project_id=p.id,
        node_id="node_1",
        label="L",
        value=15.0,
        unit="m",
        source_type=SourceType.USER_CONFIRMED,
    )
    ps.save_assumptions(p.id, [asm])
    items = ps.load_assumptions(p.id)
    assert len(items) == 1
    assert items[0].label == "L"
    assert items[0].value == 15.0


def test_assumptions_file_invalid_raises(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("N", "D", "es", "SI", "AISC")
    path = tmp_path / "ws" / p.id / "assumptions.json"
    path.write_text('{"not": "array"}', encoding="utf-8")
    with pytest.raises(ProjectPersistenceError):
        ps.load_assumptions(p.id)
