"""Block 4A M6 — branch comparison + revision snapshot via workbench (thin UI)."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlencode

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.workbench.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    monkeypatch.setenv("STRUCTURAL_TREE_WORKSPACE", str(ws))
    return TestClient(create_app())


def _first_project_id(ws: Path) -> str:
    dirs = sorted(d for d in ws.iterdir() if d.is_dir() and d.name.startswith("proj_"))
    assert dirs, f"no project dir under {ws}"
    return dirs[0].name


def _latest_revision_id(ws: Path, project_id: str) -> str:
    """Use project version order, not lexicographic directory names."""
    ps = ProjectService(ws)
    revs = ps.list_revisions(project_id)
    assert revs, "expected at least one revision"
    return revs[-1].id


def _setup_project_and_workflow(client: TestClient) -> None:
    client.post(
        "/workbench/project/create",
        data={
            "name": "M6",
            "description": "",
            "language": "es",
            "unit_system": "SI",
            "primary_standard_family": "AISC",
        },
        follow_redirects=True,
    )
    client.post(
        "/workbench/project/workflow",
        data={
            "span_m": "10",
            "support_condition": "simple_span",
            "member_role": "primary_steel_member",
            "include_optional_rolled_beam": "on",
        },
        follow_redirects=True,
    )


def _main_branch_id(page_text: str) -> str:
    m = re.search(r"main_branch_id</code>:\s*<code>(branch_[a-f0-9]{12})</code>", page_text)
    assert m, "main_branch_id not found"
    return m.group(1)


def _working_branch_from_materialize_redirect(location: str) -> str:
    m = re.search(r"(branch_[a-f0-9]{12})", unquote(location))
    assert m, location
    return m.group(1)


def test_m6_page_shows_live_vs_revision_copy_and_legends(client: TestClient) -> None:
    _setup_project_and_workflow(client)
    page = client.get("/workbench/project/workflow")
    assert page.status_code == 200
    t = page.text
    assert "M6" in t
    assert "Live workspace" in t
    assert "internal_trace_only" in t or "citation_trace_authority" in t
    assert "m5_deterministic_preliminary" in t
    assert "comparison_field_sources" in t


def test_compare_branches_ui_live_shows_result_and_provenance(client: TestClient) -> None:
    _setup_project_and_workflow(client)
    page = client.get("/workbench/project/workflow")
    main_b = _main_branch_id(page.text)
    aid = re.search(r"alt_[a-f0-9]{12}", page.text)
    assert aid
    r0 = client.post(
        "/workbench/project/workflow/materialize",
        data={"alternative_id": aid.group(0)},
        follow_redirects=False,
    )
    wb = _working_branch_from_materialize_redirect(r0.headers["location"])
    body = urlencode([("branch_ids", main_b), ("branch_ids", wb), ("context_revision_id", "")])
    r = client.post(
        "/workbench/project/workflow/compare",
        content=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    loc = r.headers.get("location", "")
    assert "msg=" in loc
    page2 = client.get("/workbench/project/workflow")
    assert page2.status_code == 200
    body = page2.text
    assert "Last comparison result" in body
    assert "internal_trace_only" in body
    assert "m5_deterministic_preliminary" in body
    assert "live tree context" in body.lower()


def test_compare_read_only_branch_file_unchanged(client: TestClient, tmp_path, monkeypatch) -> None:
    ws = tmp_path / "ws"
    monkeypatch.setenv("STRUCTURAL_TREE_WORKSPACE", str(ws))
    client = TestClient(create_app())
    _setup_project_and_workflow(client)
    page = client.get("/workbench/project/workflow")
    main_b = _main_branch_id(page.text)
    aid = re.search(r"alt_[a-f0-9]{12}", page.text)
    assert aid
    r0 = client.post(
        "/workbench/project/workflow/materialize",
        data={"alternative_id": aid.group(0)},
        follow_redirects=False,
    )
    wb = _working_branch_from_materialize_redirect(r0.headers["location"])
    # resolve project id from session via hub
    hub = client.get("/workbench")
    mproj = re.search(r"project[^\n]*<code>(proj_[a-f0-9]+)</code>", hub.text) or re.search(
        r"(proj_[a-f0-9]{12})", hub.text
    )
    assert mproj, hub.text[:500]
    pid = mproj.group(1)
    branch_path = ws / pid / "tree" / "branches" / f"{wb}.json"
    assert branch_path.is_file()
    before = branch_path.read_bytes()
    body = urlencode([("branch_ids", main_b), ("branch_ids", wb), ("context_revision_id", "")])
    client.post(
        "/workbench/project/workflow/compare",
        content=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        follow_redirects=True,
    )
    assert branch_path.read_bytes() == before


def test_revision_create_then_compare_replay_snapshot(client: TestClient, tmp_path, monkeypatch) -> None:
    ws = tmp_path / "ws"
    monkeypatch.setenv("STRUCTURAL_TREE_WORKSPACE", str(ws))
    client = TestClient(create_app())
    _setup_project_and_workflow(client)
    pid = _first_project_id(ws)
    page = client.get("/workbench/project/workflow")
    main_b = _main_branch_id(page.text)
    aid = re.search(r"alt_[a-f0-9]{12}", page.text)
    r0 = client.post(
        "/workbench/project/workflow/materialize",
        data={"alternative_id": aid.group(0)},
        follow_redirects=False,
    )
    wb = _working_branch_from_materialize_redirect(r0.headers["location"])
    client.post(
        "/workbench/project/workflow/revision-create",
        data={"rationale": "M6 test snapshot"},
        follow_redirects=True,
    )
    rev_id = _latest_revision_id(ws, pid)
    rev_page = client.get(f"/workbench/project/workflow?rev={rev_id}")
    assert rev_page.status_code == 200
    assert "Revision-backed view" in rev_page.text
    assert rev_id in rev_page.text
    body2 = urlencode([("branch_ids", main_b), ("branch_ids", wb), ("context_revision_id", rev_id)])
    r = client.post(
        "/workbench/project/workflow/compare",
        content=body2,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        follow_redirects=True,
    )
    assert r.status_code == 200
    page3 = client.get(f"/workbench/project/workflow?rev={rev_id}")
    assert "computed in revision context" in page3.text
    assert "internal_trace_only" in page3.text


def test_compare_too_few_branches_surfaces_error(client: TestClient) -> None:
    _setup_project_and_workflow(client)
    page = client.get("/workbench/project/workflow")
    main_b = _main_branch_id(page.text)
    body = urlencode([("branch_ids", main_b), ("context_revision_id", "")])
    r = client.post(
        "/workbench/project/workflow/compare",
        content=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert "err=" in r.headers.get("location", "")


def test_compare_no_session(client: TestClient) -> None:
    c2 = TestClient(client.app)
    body = urlencode([("branch_ids", "branch_a"), ("branch_ids", "branch_b"), ("context_revision_id", "")])
    r = c2.post(
        "/workbench/project/workflow/compare",
        content=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert "/workbench" in r.headers.get("location", "")


def test_unknown_revision_query_redirects_with_error(client: TestClient) -> None:
    _setup_project_and_workflow(client)
    r = client.get("/workbench/project/workflow?rev=rev_doesnotexist0", follow_redirects=False)
    assert r.status_code == 303
    assert "err=" in r.headers.get("location", "")
