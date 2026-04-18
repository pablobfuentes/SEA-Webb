"""Block 4A M3 — project hub, simple-span workflow form, persisted state display."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from structural_tree_app.domain.simple_span_workflow import WORKFLOW_ID
from structural_tree_app.workbench.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    monkeypatch.setenv("STRUCTURAL_TREE_WORKSPACE", str(ws))
    return TestClient(create_app())


def test_create_project_then_workflow_form(client: TestClient) -> None:
    r = client.post("/workbench/project/create", data={"name": "Bench M3"}, follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/workbench")

    w = client.get("/workbench/project/workflow")
    assert w.status_code == 200
    assert "Setup inputs" in w.text
    assert "span_m" in w.text


def test_workflow_post_shows_persisted_snapshot(client: TestClient) -> None:
    client.post(
        "/workbench/project/create",
        data={"name": "WF", "description": "", "language": "es", "unit_system": "SI", "primary_standard_family": "AISC"},
        follow_redirects=True,
    )
    r = client.post(
        "/workbench/project/workflow",
        data={
            "span_m": "10",
            "support_condition": "simple_span",
            "member_role": "primary_steel_member",
            "include_optional_rolled_beam": "on",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    assert "workflow" in r.headers["location"]

    page = client.get("/workbench/project/workflow")
    assert page.status_code == 200
    assert WORKFLOW_ID in page.text
    assert "Persisted workflow" in page.text
    assert "Alternatives" in page.text


def test_workflow_without_project_redirects(client: TestClient) -> None:
    r = client.get("/workbench/project/workflow", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/workbench")
