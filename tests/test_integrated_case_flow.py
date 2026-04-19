"""Integrated case flow — session + URL query handoff across primary surfaces (thin; no retrieval change)."""

from __future__ import annotations

import re
from urllib.parse import quote, unquote

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from structural_tree_app.workbench.app import create_app
from structural_tree_app.workbench.case_flow_handoff import (
    build_case_nav,
    surface_href,
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    monkeypatch.setenv("STRUCTURAL_TREE_WORKSPACE", str(ws))
    return TestClient(create_app())


def _create_session(client: TestClient) -> None:
    client.post(
        "/workbench/project/create",
        data={
            "name": "ICF",
            "description": "",
            "language": "es",
            "unit_system": "SI",
            "primary_standard_family": "AISC",
        },
        follow_redirects=False,
    )


def test_chat_post_then_evidence_prefills_query(client: TestClient) -> None:
    """Assist query persists in session for the next GET on evidence."""
    _create_session(client)
    q = "unique_integrated_flow_token_beam_shear"
    r = client.post(
        "/workbench/project/chat/query",
        data={
            "retrieval_query_text": q,
            "citation_authority": "normative_active_primary",
            "retrieval_limit": "5",
            "include_project_assumptions": "1",
        },
    )
    assert r.status_code == 200
    ev = client.get("/workbench/project/evidence")
    assert ev.status_code == 200
    assert q in ev.text


def test_explicit_q_overrides_session_on_get(client: TestClient) -> None:
    _create_session(client)
    client.post(
        "/workbench/project/chat/query",
        data={
            "retrieval_query_text": "first_query_token_icf",
            "citation_authority": "normative_active_primary",
            "retrieval_limit": "5",
        },
    )
    second = "second_query_token_icf_override"
    r = client.get("/workbench/project/chat?q=" + quote(second))
    assert r.status_code == 200
    assert second in r.text
    assert "first_query_token_icf" not in r.text


def test_workflow_includes_chat_link_with_q_when_session_has_query(client: TestClient) -> None:
    _create_session(client)
    q = "workflow_return_path_query_icf"
    client.post(
        "/workbench/project/evidence/query",
        data={
            "retrieval_query_text": q,
            "citation_authority": "normative_active_primary",
            "retrieval_limit": "5",
        },
    )
    wf = client.get("/workbench/project/workflow")
    assert wf.status_code == 200
    m = re.search(r'href="([^"]*workbench/project/chat[^"]*)"', wf.text)
    assert m
    href = unquote(m.group(1))
    assert q in href


def test_new_project_clears_assist_query_handoff(client: TestClient) -> None:
    _create_session(client)
    client.post(
        "/workbench/project/chat/query",
        data={
            "retrieval_query_text": "stale_after_switch_icf",
            "citation_authority": "normative_active_primary",
            "retrieval_limit": "5",
        },
    )
    client.post(
        "/workbench/project/create",
        data={
            "name": "ICF2",
            "description": "",
            "language": "es",
            "unit_system": "SI",
            "primary_standard_family": "AISC",
        },
        follow_redirects=False,
    )
    ev = client.get("/workbench/project/evidence")
    assert ev.status_code == 200
    assert "stale_after_switch_icf" not in ev.text


def test_integrated_flow_no_session_redirects(client: TestClient) -> None:
    for path in (
        "/workbench/project/chat",
        "/workbench/project/evidence",
        "/workbench/project/canvas",
        "/workbench/project/workflow",
    ):
        r = client.get(path, follow_redirects=False)
        assert r.status_code == 303
        assert r.headers["location"].startswith("/workbench")


def test_surface_href_appends_q() -> None:
    assert surface_href("/workbench/project/chat", "") == "/workbench/project/chat"
    assert surface_href("/workbench/project/chat", "hello world") == "/workbench/project/chat?q=hello%20world"


def test_build_case_nav_keys() -> None:
    nav = build_case_nav("x")
    assert nav["query_nonempty"] is True
    assert "q=x" in nav["chat"]
    nav_empty = build_case_nav("")
    assert nav_empty["query_nonempty"] is False
    assert nav_empty["evidence"] == "/workbench/project/evidence"
