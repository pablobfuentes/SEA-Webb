"""Workbench U3 — synthesis control visibility, states, form passthrough (chat + evidence)."""

from __future__ import annotations

import re

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from structural_tree_app.domain.enums import NormativeClassification
from structural_tree_app.services.document_service import DocumentIngestionService
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.workbench.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STRUCTURAL_TREE_WORKSPACE", str(tmp_path / "ws"))
    return TestClient(create_app())


def _session(client: TestClient) -> None:
    r = client.post(
        "/workbench/project/create",
        data={
            "name": "U3WB",
            "description": "",
            "language": "es",
            "unit_system": "SI",
            "primary_standard_family": "AISC",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303


def _project_id_from_hub(client: TestClient) -> str:
    hub = client.get("/workbench")
    assert hub.status_code == 200
    m = re.search(r"<code>(proj_[a-z0-9]+)</code>", hub.text)
    assert m, hub.text[:500]
    return m.group(1)


def test_chat_u3_control_visible_and_disabled_when_server_off(client: TestClient) -> None:
    _session(client)
    r = client.get("/workbench/project/chat")
    assert r.status_code == 200
    assert "Local answer synthesis (U3)" in r.text
    assert 'id="u3-req-synth-chat"' in r.text
    assert "STRUCTURAL_LOCAL_MODEL_ENABLED=1" in r.text
    assert "bounded synthesis is" in r.text.lower() or "unavailable" in r.text.lower()
    assert 'name="request_local_model_synthesis"' not in r.text
    m = re.search(r'<input[^>]*id="u3-req-synth-chat"[^>]*>', r.text)
    assert m and "disabled" in m.group(0)


def test_evidence_u3_control_visible_and_disabled_when_server_off(client: TestClient) -> None:
    _session(client)
    r = client.get("/workbench/project/evidence")
    assert r.status_code == 200
    assert "Local answer synthesis (U3)" in r.text
    assert 'id="u3-req-synth-evidence"' in r.text
    assert 'name="request_local_model_synthesis"' not in r.text
    m = re.search(r'<input[^>]*id="u3-req-synth-evidence"[^>]*>', r.text)
    assert m and "disabled" in m.group(0)


def test_chat_u3_checkbox_visible_and_enabled_when_server_on(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRUCTURAL_LOCAL_MODEL_ENABLED", "1")
    monkeypatch.setenv("STRUCTURAL_LOCAL_MODEL_PROVIDER", "stub")
    _session(client)
    r = client.get("/workbench/project/chat")
    assert r.status_code == 200
    assert 'name="request_local_model_synthesis"' in r.text
    assert 'id="u3-req-synth-chat"' in r.text
    m = re.search(r'<input[^>]*id="u3-req-synth-chat"[^>]*>', r.text)
    assert m and "disabled" not in m.group(0)
    assert "stub" in r.text
    assert "answer_text" in r.text and "orchestration" in r.text.lower()


def test_evidence_u3_checkbox_visible_and_enabled_when_server_on(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRUCTURAL_LOCAL_MODEL_ENABLED", "1")
    monkeypatch.setenv("STRUCTURAL_LOCAL_MODEL_PROVIDER", "stub")
    _session(client)
    r = client.get("/workbench/project/evidence")
    assert r.status_code == 200
    assert 'name="request_local_model_synthesis"' in r.text
    m = re.search(r'<input[^>]*id="u3-req-synth-evidence"[^>]*>', r.text)
    assert m and "disabled" not in m.group(0)


def test_post_chat_passes_request_local_model_synthesis_when_checked(client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setenv("STRUCTURAL_LOCAL_MODEL_ENABLED", "1")
    monkeypatch.setenv("STRUCTURAL_LOCAL_MODEL_PROVIDER", "stub")
    _session(client)
    pid = _project_id_from_hub(client)
    ps = ProjectService(tmp_path / "ws")
    src = tmp_path / "u3synth.txt"
    src.write_text("Steel beam flexure u3_post_unique_token.", encoding="utf-8")
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(
        src,
        title="U3 post",
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="AISC",
    )
    assert ir.document
    ing.approve_document(ir.document.id)
    ing.activate_for_normative_corpus(ir.document.id)

    r = client.post(
        "/workbench/project/chat/query",
        data={
            "retrieval_query_text": "u3_post_unique_token",
            "citation_authority": "normative_active_primary",
            "retrieval_limit": "5",
            "request_local_model_synthesis": "1",
        },
    )
    assert r.status_code == 200
    assert "local_model_synthesis_bounded" in r.text or "Bounded local model restatement" in r.text


def test_u3_ux_patch_does_not_strip_assist_provenance_citations(client: TestClient, monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    """Assist partial still renders authority, provenance, citations (unchanged by U3 control UX)."""
    monkeypatch.setenv("STRUCTURAL_LOCAL_MODEL_ENABLED", "1")
    monkeypatch.setenv("STRUCTURAL_LOCAL_MODEL_PROVIDER", "stub")
    _session(client)
    pid = _project_id_from_hub(client)
    ps = ProjectService(tmp_path / "ws")
    src = tmp_path / "u3prov.txt"
    src.write_text("Lateral stability token_u3_prov_only.", encoding="utf-8")
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(
        src,
        title="Prov",
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="AISC",
    )
    assert ir.document
    ing.approve_document(ir.document.id)
    ing.activate_for_normative_corpus(ir.document.id)

    r = client.post(
        "/workbench/project/chat/query",
        data={
            "retrieval_query_text": "token_u3_prov_only",
            "citation_authority": "normative_active_primary",
            "retrieval_limit": "3",
            "request_local_model_synthesis": "1",
        },
    )
    assert r.status_code == 200
    assert 'aria-label="Assist response"' in r.text
    assert "Retrieval provenance" in r.text
    assert "response_authority_summary" in r.text
    assert "/workbench/project/evidence/fragment/" in r.text
    assert "Citations" in r.text or "citation_id=" in r.text

    r2 = client.post(
        "/workbench/project/chat/query",
        data={
            "retrieval_query_text": "token_u3_prov_only",
            "citation_authority": "normative_active_primary",
            "retrieval_limit": "3",
        },
    )
    assert r2.status_code == 200
    assert "Retrieval provenance" in r2.text
    assert "/workbench/project/evidence/fragment/" in r2.text
