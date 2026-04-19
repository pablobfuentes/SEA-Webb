"""Phase U6 — secondary tree/workflow integration from primary surfaces (thin links + framing)."""

from __future__ import annotations

import re

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from structural_tree_app.workbench.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    monkeypatch.setenv("STRUCTURAL_TREE_WORKSPACE", str(ws))
    return TestClient(create_app())


def _session_project(client: TestClient) -> None:
    client.post(
        "/workbench/project/create",
        data={"name": "U6", "description": "", "language": "es", "unit_system": "SI", "primary_standard_family": "AISC"},
        follow_redirects=False,
    )


def test_u6_chat_links_to_workflow_secondary_strip(client: TestClient) -> None:
    _session_project(client)
    r = client.get("/workbench/project/chat")
    assert r.status_code == 200
    assert "/workbench/project/workflow" in r.text
    assert "u6-secondary-strip" in r.text
    assert "Secondary" in r.text and "tree" in r.text.lower()


def test_u6_evidence_links_to_workflow_secondary_strip(client: TestClient) -> None:
    _session_project(client)
    r = client.get("/workbench/project/evidence")
    assert r.status_code == 200
    assert "/workbench/project/workflow" in r.text
    assert "u6-secondary-strip" in r.text


def test_u6_canvas_links_to_workflow_secondary_strip(client: TestClient) -> None:
    _session_project(client)
    r = client.get("/workbench/project/canvas")
    assert r.status_code == 200
    assert "/workbench/project/workflow" in r.text
    assert "u6-secondary-strip" in r.text


def test_u6_workflow_links_back_to_primary_surfaces(client: TestClient) -> None:
    _session_project(client)
    r = client.get("/workbench/project/workflow")
    assert r.status_code == 200
    assert "case-flow-primary-nav" in r.text
    assert "/workbench/project/chat" in r.text
    assert "/workbench/project/evidence" in r.text
    assert "/workbench/project/canvas" in r.text
    assert "Secondary surface" in r.text or "secondary trace" in r.text.lower()


def test_u6_hub_lists_primary_before_secondary_sections(client: TestClient) -> None:
    _session_project(client)
    r = client.get("/workbench")
    assert r.status_code == 200
    assert "Primary surfaces" in r.text
    assert "Secondary" in r.text and "trace" in r.text.lower()
    pos_primary = r.text.find("Primary surfaces")
    pos_secondary = r.text.find("Secondary")
    assert pos_primary != -1 and pos_secondary != -1
    assert pos_primary < pos_secondary


def test_u6_session_project_preserved_chat_to_workflow(client: TestClient) -> None:
    """Same session: project_id available on both surfaces (HTML shows consistent project context on workflow)."""
    _session_project(client)
    hub = client.get("/workbench")
    m = re.search(r"<code>(proj_[a-z0-9]+)</code>", hub.text)
    assert m
    pid = m.group(1)
    wf = client.get("/workbench/project/workflow")
    assert wf.status_code == 200
    assert pid in wf.text


def test_u6_corpus_includes_primary_nav(client: TestClient) -> None:
    _session_project(client)
    r = client.get("/workbench/project/corpus")
    assert r.status_code == 200
    assert "case-flow-primary-nav" in r.text
    assert "/workbench/project/chat" in r.text
