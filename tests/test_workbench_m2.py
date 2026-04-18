"""Block 4A M2 — workbench shell routes and workspace config."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from structural_tree_app.workbench.app import create_app
from structural_tree_app.workbench.config import get_workspace_path


@pytest.fixture
def client(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    monkeypatch.setenv("STRUCTURAL_TREE_WORKSPACE", str(ws))
    return TestClient(create_app())


def test_health_returns_ok(client: TestClient, tmp_path) -> None:
    ws = (tmp_path / "ws").resolve()
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"
    assert data["service"] == "structural_tree_app.workbench"
    assert data["workspace_path"] == str(ws)
    assert data["workspace_env"] == "STRUCTURAL_TREE_WORKSPACE"


def test_root_redirects_to_workbench(client: TestClient) -> None:
    r = client.get("/", follow_redirects=False)
    assert r.status_code == 307
    assert r.headers["location"] == "/workbench"


def test_workbench_page_renders(client: TestClient) -> None:
    r = client.get("/workbench")
    assert r.status_code == 200
    assert "Validation workbench" in r.text
    assert "pip install -e" in r.text
    assert "Create project" in r.text


def test_get_workspace_path_respects_env(tmp_path, monkeypatch) -> None:
    ws = tmp_path / "custom_ws"
    monkeypatch.setenv("STRUCTURAL_TREE_WORKSPACE", str(ws))
    assert get_workspace_path() == ws.resolve()
