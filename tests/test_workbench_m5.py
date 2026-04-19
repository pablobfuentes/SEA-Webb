"""Block 4A M5 — materialize branch + M5 preliminary via workbench routes."""

from __future__ import annotations

import re
from urllib.parse import unquote

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from structural_tree_app.services.simple_span_m5_service import METHOD_LABEL as M5_METHOD_LABEL
from structural_tree_app.workbench.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    monkeypatch.setenv("STRUCTURAL_TREE_WORKSPACE", str(ws))
    return TestClient(create_app())


def _create_project_and_workflow(client: TestClient) -> None:
    client.post(
        "/workbench/project/create",
        data={
            "name": "M5",
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


def _first_alternative_id(page_text: str) -> str:
    m = re.search(r"alt_[a-f0-9]{12}", page_text)
    assert m, "expected alternative id in page"
    return m.group(0)


def _working_branch_id_from_materialize_redirect(location: str) -> str:
    m = re.search(r"(branch_[a-f0-9]{12})", unquote(location))
    assert m, location
    return m.group(1)


def test_m5_page_shows_preliminary_banner_and_method_label(client: TestClient) -> None:
    _create_project_and_workflow(client)
    page = client.get("/workbench/project/workflow")
    assert page.status_code == 200
    t = page.text
    assert "preliminary" in t.lower()
    assert M5_METHOD_LABEL in t
    assert "materialize" in t.lower()
    assert "Block 3 services" in t


def test_materialize_then_m5_persists_calc_and_checks(client: TestClient) -> None:
    _create_project_and_workflow(client)
    page = client.get("/workbench/project/workflow")
    aid = _first_alternative_id(page.text)
    r = client.post(
        "/workbench/project/workflow/materialize",
        data={"alternative_id": aid},
        follow_redirects=False,
    )
    assert r.status_code == 303
    wb = _working_branch_id_from_materialize_redirect(r.headers["location"])
    page2 = client.get("/workbench/project/workflow")
    assert page2.status_code == 200
    assert wb in page2.text
    r3 = client.post(
        "/workbench/project/workflow/m5-run",
        data={"working_branch_id": wb},
        follow_redirects=False,
    )
    assert r3.status_code == 303
    page3 = client.get("/workbench/project/workflow")
    assert page3.status_code == 200
    body = page3.text
    assert "Persisted Calculation" in body
    assert "preliminary_max_depth_fit" in body or "Checks" in body
    assert M5_METHOD_LABEL in body


def test_m5_duplicate_run_surfaces_error(client: TestClient) -> None:
    _create_project_and_workflow(client)
    page = client.get("/workbench/project/workflow")
    aid = _first_alternative_id(page.text)
    r0 = client.post(
        "/workbench/project/workflow/materialize", data={"alternative_id": aid}, follow_redirects=False
    )
    wid = _working_branch_id_from_materialize_redirect(r0.headers["location"])
    client.post("/workbench/project/workflow/m5-run", data={"working_branch_id": wid}, follow_redirects=True)
    r = client.post("/workbench/project/workflow/m5-run", data={"working_branch_id": wid}, follow_redirects=False)
    assert r.status_code == 303
    loc = r.headers.get("location", "")
    assert "err=" in loc
    err_page = client.get("/workbench/project/workflow" + ("?" + loc.split("?", 1)[1] if "?" in loc else ""))
    assert err_page.status_code == 200
    assert "already exists" in err_page.text.lower() or "duplicate" in err_page.text.lower() or "refuse" in err_page.text.lower()


def test_m5_no_session_redirects(client: TestClient) -> None:
    r = client.post(
        "/workbench/project/workflow/m5-run",
        data={"working_branch_id": "branch_deadbeef0001"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert "/workbench" in r.headers.get("location", "")


def test_materialize_bad_project_session(client: TestClient) -> None:
    _create_project_and_workflow(client)
    # clear session by opening client without cookie — new request without project
    c2 = TestClient(client.app)
    r = c2.post(
        "/workbench/project/workflow/materialize",
        data={"alternative_id": "alt_dummy0000001"},
        follow_redirects=False,
    )
    assert r.status_code == 303


def test_m5_bad_branch_id(client: TestClient) -> None:
    _create_project_and_workflow(client)
    r = client.post(
        "/workbench/project/workflow/m5-run",
        data={"working_branch_id": "branch_doesnotexist0"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    follow = client.get(r.headers["location"], follow_redirects=True)
    assert follow.status_code == 200
    assert "Error" in follow.text or "err" in follow.text.lower()


def test_workflow_reload_shows_persisted_m5(client: TestClient) -> None:
    _create_project_and_workflow(client)
    page = client.get("/workbench/project/workflow")
    aid = _first_alternative_id(page.text)
    r0 = client.post(
        "/workbench/project/workflow/materialize", data={"alternative_id": aid}, follow_redirects=False
    )
    wb = _working_branch_id_from_materialize_redirect(r0.headers["location"])
    client.post("/workbench/project/workflow/m5-run", data={"working_branch_id": wb}, follow_redirects=True)
    page3 = client.get("/workbench/project/workflow")
    assert M5_METHOD_LABEL in page3.text
    page4 = client.get("/workbench/project/workflow")
    assert M5_METHOD_LABEL in page4.text
    assert "Persisted Calculation" in page4.text
