"""Phase U2 — chat-first shell: primary LocalAssist surface, same orchestrator as U1 evidence."""

from __future__ import annotations

import re

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from structural_tree_app.domain.enums import NormativeClassification
from structural_tree_app.domain.governance_enums import GovernanceRetrievalBinding
from structural_tree_app.domain.governance_models import ActiveKnowledgeProjection
from structural_tree_app.domain.models import utc_now
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
        data={"name": "U2", "description": "", "language": "es", "unit_system": "SI", "primary_standard_family": "AISC"},
        follow_redirects=False,
    )
    assert r.status_code == 303


def _project_id_from_hub(client: TestClient) -> str:
    hub = client.get("/workbench")
    assert hub.status_code == 200
    m = re.search(r"<code>(proj_[a-z0-9]+)</code>", hub.text)
    assert m, hub.text[:500]
    return m.group(1)


def test_u2_chat_requires_project(client: TestClient) -> None:
    r = client.get("/workbench/project/chat", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/workbench")


def test_u2_chat_get_empty_no_response_block(client: TestClient) -> None:
    """Primary chat page with session: form only; no assist article until POST."""
    _session_project(client)
    r = client.get("/workbench/project/chat")
    assert r.status_code == 200
    assert "chat-first shell" in r.text.lower() or "Primary assistant" in r.text
    assert 'action="/workbench/project/chat/query"' in r.text
    assert "LocalAssistOrchestrator" in r.text
    assert 'name="retrieval_query_text"' in r.text
    assert 'aria-label="Assist response"' not in r.text


def test_u2_hub_lists_chat_first(client: TestClient) -> None:
    _session_project(client)
    hub = client.get("/workbench")
    assert hub.status_code == 200
    assert "/workbench/project/chat" in hub.text
    pos_chat = hub.text.find("/workbench/project/chat")
    pos_wf = hub.text.find("/workbench/project/workflow")
    assert pos_chat != -1 and pos_wf != -1
    assert pos_chat < pos_wf


def test_u2_post_chat_success_citations_and_fragment_link(client: TestClient, tmp_path) -> None:
    _session_project(client)
    pid = _project_id_from_hub(client)
    ps = ProjectService(tmp_path / "ws")
    src = tmp_path / "u2chat.txt"
    src.write_text("Steel beam flexure design provisions AISC unique_u2_chat_token.", encoding="utf-8")
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(
        src,
        title="Steel ref",
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="AISC",
    )
    assert ir.document
    ing.approve_document(ir.document.id)
    ing.activate_for_normative_corpus(ir.document.id)

    r = client.post(
        "/workbench/project/chat/query",
        data={
            "retrieval_query_text": "flexure unique_u2_chat_token",
            "citation_authority": "normative_active_primary",
            "retrieval_limit": "5",
            "include_project_assumptions": "1",
            "match_project_primary_standard_family": "1",
        },
    )
    assert r.status_code == 200
    assert "evidence_passages_assembled" in r.text or "Normative retrieval" in r.text
    assert 'aria-label="Assist response"' in r.text
    assert "response_authority_summary" in r.text
    assert "/workbench/project/evidence/fragment/" in r.text
    assert "Open source fragment" in r.text


def test_u2_post_shows_answer_authority_warnings_structure(client: TestClient, tmp_path) -> None:
    _session_project(client)
    pid = _project_id_from_hub(client)
    ps = ProjectService(tmp_path / "ws")
    src = tmp_path / "u2struct.txt"
    src.write_text("Lateral torsional buckling check token_u2_struct.", encoding="utf-8")
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(
        src,
        title="LTB",
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="AISC",
    )
    assert ir.document
    ing.approve_document(ir.document.id)
    ing.activate_for_normative_corpus(ir.document.id)

    r = client.post(
        "/workbench/project/chat/query",
        data={
            "retrieval_query_text": "token_u2_struct",
            "citation_authority": "normative_active_primary",
            "retrieval_limit": "3",
        },
    )
    assert r.status_code == 200
    assert "<strong>answer_status:</strong>" in r.text
    assert "<h4" in r.text and "answer_text" in r.text
    assert "Retrieval provenance" in r.text


def test_u2_governance_refusal_rendered_on_chat(client: TestClient, tmp_path) -> None:
    _session_project(client)
    pid = _project_id_from_hub(client)
    from structural_tree_app.domain.governance_enums import DocumentGovernanceDisposition
    from structural_tree_app.domain.governance_models import DocumentGovernanceIndex, DocumentGovernanceRecord

    ps = ProjectService(tmp_path / "ws")
    src = tmp_path / "gov_u2.txt"
    src.write_text("Conflict doc text u2.", encoding="utf-8")
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(
        src,
        title="G",
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="AISC",
    )
    did = ir.document.id
    ing.approve_document(did)
    ing.activate_for_normative_corpus(did)
    gs = ps.governance_store()
    idx = gs.try_load_document_governance_index(pid)
    assert idx
    rec = idx.by_document_id[did]
    bumped = DocumentGovernanceRecord(
        document_id=did,
        pipeline_stage=rec.pipeline_stage,
        disposition=DocumentGovernanceDisposition.CONFLICTING_UNRESOLVED,
        updated_at=utc_now(),
        notes=rec.notes,
        analysis=rec.analysis,
        classification=rec.classification,
    )
    gs.save_document_governance_index(
        DocumentGovernanceIndex(
            project_id=pid,
            schema_version=idx.schema_version,
            updated_at=utc_now(),
            by_document_id={**idx.by_document_id, did: bumped},
        )
    )
    cur = gs.try_load_active_knowledge_projection(pid)
    assert cur
    gs.save_active_knowledge_projection(
        ActiveKnowledgeProjection(
            project_id=pid,
            schema_version=cur.schema_version,
            updated_at=utc_now(),
            retrieval_binding=GovernanceRetrievalBinding.EXPLICIT_PROJECTION,
            authoritative_document_ids=(did,),
            supporting_document_ids=cur.supporting_document_ids,
            excluded_from_authoritative_document_ids=cur.excluded_from_authoritative_document_ids,
            notes=cur.notes,
        )
    )

    r = client.post(
        "/workbench/project/chat/query",
        data={"retrieval_query_text": "Conflict u2", "citation_authority": "normative_active_primary"},
    )
    assert r.status_code == 200
    assert "GOVERNANCE_CONFLICT_BLOCKS_NORMATIVE" in r.text
    assert 'class="refusal' in r.text or "Refusal" in r.text


def test_u2_authoritative_vs_supporting_badge_classes(client: TestClient, tmp_path) -> None:
    _session_project(client)
    pid = _project_id_from_hub(client)
    ps = ProjectService(tmp_path / "ws")
    src = tmp_path / "badge_u2.txt"
    src.write_text("Badge test unique_u2_badge normative supporting.", encoding="utf-8")
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(
        src,
        title="B",
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="AISC",
    )
    assert ir.document
    ing.approve_document(ir.document.id)
    ing.activate_for_normative_corpus(ir.document.id)

    rn = client.post(
        "/workbench/project/chat/query",
        data={
            "retrieval_query_text": "unique_u2_badge",
            "citation_authority": "normative_active_primary",
            "retrieval_limit": "5",
        },
    )
    assert rn.status_code == 200
    assert 'class="badge auth"' in rn.text

    rs = client.post(
        "/workbench/project/chat/query",
        data={
            "retrieval_query_text": "unique_u2_badge",
            "citation_authority": "approved_ingested",
            "retrieval_limit": "5",
        },
    )
    assert rs.status_code == 200
    assert 'class="badge sup"' in rs.text


def test_u2_fragment_navigation_from_chat_result(client: TestClient, tmp_path) -> None:
    _session_project(client)
    pid = _project_id_from_hub(client)
    ps = ProjectService(tmp_path / "ws")
    src = tmp_path / "frag_u2.txt"
    src.write_text("Fragment body for u2 chat link test.", encoding="utf-8")
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(src, title="Frag", normative_classification=NormativeClassification.PRIMARY_STANDARD)
    assert ir.document
    doc_id = ir.document.id
    ing.approve_document(doc_id)
    ing.activate_for_normative_corpus(doc_id)

    chat = client.post(
        "/workbench/project/chat/query",
        data={
            "retrieval_query_text": "Fragment body u2 chat",
            "citation_authority": "normative_active_primary",
        },
    )
    assert chat.status_code == 200
    m = re.search(r'href="/workbench/project/evidence/fragment/([^/]+)/([^"]+)"', chat.text)
    assert m, chat.text[:1200]
    fid = m.group(2)
    page = client.get(f"/workbench/project/evidence/fragment/{doc_id}/{fid}")
    assert page.status_code == 200
    assert "Fragment body for u2 chat link test." in page.text


def test_u2_bad_project_session_redirects(client: TestClient, tmp_path) -> None:
    _session_project(client)
    pid = _project_id_from_hub(client)
    proj_file = tmp_path / "ws" / pid / "project.json"
    assert proj_file.is_file()
    proj_file.unlink()

    r = client.get("/workbench/project/chat", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/workbench")

    hub = client.get("/workbench")
    assert "proj_" not in hub.text or "No project selected" in hub.text or "Current" not in hub.text


def test_u2_empty_chat_stable_strings(client: TestClient) -> None:
    _session_project(client)
    a = client.get("/workbench/project/chat").text
    b = client.get("/workbench/project/chat").text
    assert a == b
    assert "Primary assistant" in a


def test_u2_deterministic_hooks_not_citations_chat(client: TestClient, tmp_path) -> None:
    _session_project(client)
    pid = _project_id_from_hub(client)
    from structural_tree_app.domain.models import Calculation
    from structural_tree_app.services.simple_span_m5_service import METHOD_LABEL as M5_METHOD_LABEL
    from structural_tree_app.storage.tree_store import TreeStore

    ps = ProjectService(tmp_path / "ws")
    store = TreeStore.for_live_project(ps.repository, pid)
    store.ensure_layout()
    store.save_calculation(
        Calculation(
            project_id=pid,
            node_id="n-u2",
            objective="x",
            method_label=M5_METHOD_LABEL,
            formula_text="n/a",
            inputs={},
            substitutions={},
            result={},
        )
    )

    r = client.post(
        "/workbench/project/chat/query",
        data={
            "retrieval_query_text": "nomatchzzz_u2_999",
            "include_deterministic_hooks": "1",
        },
    )
    assert r.status_code == 200
    assert "Deterministic hooks" in r.text
    assert "not document evidence" in r.text.lower()
