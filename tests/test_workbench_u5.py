"""Phase U5 — visual case canvas over ReasoningBridgeResult (thin UI; no logic duplication)."""

from __future__ import annotations

import re
from urllib.parse import quote

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from structural_tree_app.domain.enums import NormativeClassification
from structural_tree_app.services.derived_knowledge_service import DerivedKnowledgeService
from structural_tree_app.services.document_service import DocumentIngestionService
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.workbench.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    monkeypatch.setenv("STRUCTURAL_TREE_WORKSPACE", str(ws))
    return TestClient(create_app())


def _session_project(client: TestClient) -> None:
    r = client.post(
        "/workbench/project/create",
        data={"name": "U5", "description": "", "language": "es", "unit_system": "SI", "primary_standard_family": "AISC"},
        follow_redirects=False,
    )
    assert r.status_code == 303


def test_u5_canvas_requires_project(client: TestClient) -> None:
    r = client.get("/workbench/project/canvas", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/workbench")


def test_u5_canvas_empty_query_shows_empty_state(client: TestClient) -> None:
    _session_project(client)
    r = client.get("/workbench/project/canvas")
    assert r.status_code == 200
    assert "No case query loaded" in r.text
    assert 'action="/workbench/project/canvas"' in r.text
    assert "name=\"q\"" in r.text
    assert "Visual case board" in r.text or "visual case board" in r.text.lower()


def test_u5_canvas_with_query_renders_bridge_sections(client: TestClient, tmp_path) -> None:
    _session_project(client)
    hub = client.get("/workbench")
    m = re.search(r"<code>(proj_[a-z0-9]+)</code>", hub.text)
    assert m
    pid = m.group(1)
    ps = ProjectService(tmp_path / "ws")
    src = tmp_path / "u5norm.txt"
    src.write_text(
        "Steel simple span beam flexure equation capacity check limit state phi Mn unique_u5_token.",
        encoding="utf-8",
    )
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(
        src,
        title="U5 ref",
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="AISC",
    )
    assert ir.document
    ing.approve_document(ir.document.id)
    ing.activate_for_normative_corpus(ir.document.id)
    DerivedKnowledgeService(ps).regenerate(pid)

    q = "simple span steel beam flexure capacity unique_u5_token"
    r = client.get(f"/workbench/project/canvas?q={quote(q)}")
    assert r.status_code == 200
    assert "Interpreted problem" in r.text
    assert "flexure" in r.text.lower() or "span" in r.text.lower()
    assert "Candidate formulas" in r.text or "formulas" in r.text.lower()
    assert "Reasoning bridge output is interpretive" in r.text or "interpretive" in r.text.lower()
    assert "/workbench/project/evidence/fragment/" in r.text
    assert "u5-formula-supported" in r.text or "u5-formula-recognized" in r.text or "u5-formula-gap" in r.text


def test_u5_supported_vs_recognized_tier_css_classes(client: TestClient, tmp_path) -> None:
    """Tier classes distinguish supported vs recognition-only vs gap (HTML contract)."""
    _session_project(client)
    hub = client.get("/workbench")
    m = re.search(r"<code>(proj_[a-z0-9]+)</code>", hub.text)
    pid = m.group(1)
    ps = ProjectService(tmp_path / "ws")
    src = tmp_path / "u5tier.txt"
    src.write_text("Steel beam flexure phi Mn equation check.", encoding="utf-8")
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(
        src,
        title="Tier",
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="AISC",
    )
    ing.approve_document(ir.document.id)
    ing.activate_for_normative_corpus(ir.document.id)
    DerivedKnowledgeService(ps).regenerate(pid)

    r = client.get("/workbench/project/canvas?q=" + quote("steel span beam flexure equation"))
    assert r.status_code == 200
    assert "u5-formula-supported" in r.text or "u5-formula-recognized" in r.text or "u5-formula-gap" in r.text


def test_u5_execution_steps_not_labeled_as_normative_evidence(client: TestClient, tmp_path) -> None:
    _session_project(client)
    hub = client.get("/workbench")
    pid = re.search(r"<code>(proj_[a-z0-9]+)</code>", hub.text).group(1)
    ps = ProjectService(tmp_path / "ws")
    src = tmp_path / "u5exec.txt"
    src.write_text("Steel simple span flexure check phi.", encoding="utf-8")
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(
        src,
        title="Exec",
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="AISC",
    )
    ing.approve_document(ir.document.id)
    ing.activate_for_normative_corpus(ir.document.id)
    DerivedKnowledgeService(ps).regenerate(pid)

    r = client.get("/workbench/project/canvas?q=" + quote("steel simple span flexure"))
    assert r.status_code == 200
    assert "not normative evidence" in r.text
    assert "deterministic" in r.text.lower()


def test_u5_chat_includes_canvas_nav_link(client: TestClient) -> None:
    _session_project(client)
    r = client.get("/workbench/project/chat")
    assert r.status_code == 200
    assert "/workbench/project/canvas" in r.text
    assert "Case canvas" in r.text or "visual case board" in r.text.lower()


def test_u5_view_model_helpers_stable_import() -> None:
    from structural_tree_app.workbench.u5_canvas_view import u5_canvas_board_from_result
    from structural_tree_app.domain.reasoning_bridge_contract import ReasoningBridgeResult

    empty = ReasoningBridgeResult(project_id="proj_x", query_text="")
    d = u5_canvas_board_from_result(empty)
    assert d["analysis_status"] == "ok"
    assert d["process_steps"] == []

