"""G1.5 / U0 — corpus bootstrap workbench: upload, list, detail, manual disposition, projection."""

from __future__ import annotations

import re

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from structural_tree_app.domain.enums import DocumentApprovalStatus, NormativeClassification
from structural_tree_app.domain.governance_enums import GovernanceRetrievalBinding
from structural_tree_app.domain.governance_models import ActiveKnowledgeProjection
from structural_tree_app.services.corpus_bootstrap_service import apply_manual_corpus_bootstrap
from structural_tree_app.services.document_service import DocumentIngestionService
from structural_tree_app.services.local_assist_orchestrator import LocalAssistOrchestrator
from structural_tree_app.domain.local_assist_contract import LocalAssistQuery
from structural_tree_app.workbench.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    monkeypatch.setenv("STRUCTURAL_TREE_WORKSPACE", str(ws))
    return TestClient(create_app())


def _session_project(client: TestClient) -> str:
    r = client.post(
        "/workbench/project/create",
        data={
            "name": "Corpus",
            "description": "",
            "language": "es",
            "unit_system": "SI",
            "primary_standard_family": "AISC",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    hub = client.get("/workbench")
    assert hub.status_code == 200
    m = re.search(r"<code>(proj_[a-z0-9]+)</code>", hub.text)
    assert m, hub.text[:500]
    return m.group(1)


def test_corpus_requires_session(client: TestClient) -> None:
    r = client.get("/workbench/project/corpus", follow_redirects=False)
    assert r.status_code == 303
    assert "/workbench" in r.headers["location"]


def test_corpus_list_renders_with_session(client: TestClient) -> None:
    _session_project(client)
    r = client.get("/workbench/project/corpus")
    assert r.status_code == 200
    assert "Corpus bootstrap" in r.text
    assert "Upload" in r.text


def test_upload_ingest_success(client: TestClient, tmp_path) -> None:
    pid = _session_project(client)
    ws = tmp_path / "ws"
    fpath = tmp_path / "up.txt"
    fpath.write_text("Bootstrap unique token alpha βγδ for corpus test.\n", encoding="utf-8")

    with open(fpath, "rb") as fh:
        r = client.post(
            "/workbench/project/corpus/upload",
            files={"files": ("up.txt", fh, "text/plain")},
            follow_redirects=False,
        )
    assert r.status_code == 303
    assert "ingested" in (client.get(r.headers["location"]).text or "").lower() or "ingested" in r.headers.get("location", "")

    follow = client.get(r.headers["location"])
    assert follow.status_code == 200
    assert "ingested" in follow.text.lower()
    assert pid in follow.text

    from structural_tree_app.services.project_service import ProjectService

    ps = ProjectService(ws)
    assert ps.load_project(pid).ingested_document_ids


def test_upload_duplicate_skipped(client: TestClient, tmp_path) -> None:
    _session_project(client)
    fpath = tmp_path / "dup.txt"
    fpath.write_text("Same duplicate bytes for skip test.", encoding="utf-8")
    for _ in range(2):
        with open(fpath, "rb") as fh:
            r = client.post(
                "/workbench/project/corpus/upload",
                files={"files": ("dup.txt", fh, "text/plain")},
                follow_redirects=False,
            )
        assert r.status_code == 303
    page = client.get(r.headers["location"])
    assert page.status_code == 200
    assert "duplicate_skipped" in page.text.lower()


def test_upload_ocr_deferred_blank_pdf(client: TestClient, tmp_path) -> None:
    pytest.importorskip("pypdf")
    from pypdf import PdfWriter

    _session_project(client)
    blank = tmp_path / "blank.pdf"
    w = PdfWriter()
    w.add_blank_page(width=72, height=72)
    with open(blank, "wb") as fh:
        w.write(fh)
    with open(blank, "rb") as fh:
        r = client.post(
            "/workbench/project/corpus/upload",
            files={"files": ("blank.pdf", fh, "application/pdf")},
            follow_redirects=False,
        )
    assert r.status_code == 303
    page = client.get(r.headers["location"])
    assert page.status_code == 200
    assert "ocr_deferred" in page.text.lower()


def test_upload_unsupported_extension(client: TestClient, tmp_path) -> None:
    _session_project(client)
    fpath = tmp_path / "x.xyz"
    fpath.write_text("nope", encoding="utf-8")
    with open(fpath, "rb") as fh:
        r = client.post(
            "/workbench/project/corpus/upload",
            files={"files": ("bad.xyz", fh, "application/octet-stream")},
            follow_redirects=False,
        )
    assert r.status_code == 303
    page = client.get(r.headers["location"])
    assert "unsupported_document_for_ingestion" in page.text.lower()


def test_document_detail_and_bootstrap_actions(client: TestClient, tmp_path) -> None:
    pid = _session_project(client)
    ws = tmp_path / "ws"
    fpath = tmp_path / "det.txt"
    fpath.write_text("Detail view document content.", encoding="utf-8")
    with open(fpath, "rb") as fh:
        client.post(
            "/workbench/project/corpus/upload",
            files={"files": ("det.txt", fh, "text/plain")},
        )
    from structural_tree_app.services.project_service import ProjectService

    ps = ProjectService(ws)
    doc_id = ps.load_project(pid).ingested_document_ids[0]

    r = client.get(f"/workbench/project/corpus/document/{doc_id}")
    assert r.status_code == 200
    assert doc_id in r.text
    assert "pipeline_stage" in r.text.lower() or "ingested" in r.text.lower()

    r2 = client.post(
        f"/workbench/project/corpus/document/{doc_id}/bootstrap",
        data={"bootstrap_role": "authoritative_active"},
        follow_redirects=False,
    )
    assert r2.status_code == 303
    detail = client.get(r2.headers["location"])
    assert detail.status_code == 200
    assert "active" in detail.text.lower()

    client.post(
        f"/workbench/project/corpus/document/{doc_id}/bootstrap",
        data={"bootstrap_role": "supporting"},
    )
    d2 = client.get(f"/workbench/project/corpus/document/{doc_id}")
    assert "supporting" in d2.text.lower()

    client.post(
        f"/workbench/project/corpus/document/{doc_id}/bootstrap",
        data={"bootstrap_role": "pending_review"},
    )
    d3 = client.get(f"/workbench/project/corpus/document/{doc_id}")
    assert "pending_review" in d3.text.lower()


def test_projection_binding_and_sync_legacy(client: TestClient, tmp_path) -> None:
    pid = _session_project(client)
    ws = tmp_path / "ws"
    fpath = tmp_path / "pr.txt"
    fpath.write_text("Projection sync test text.", encoding="utf-8")
    with open(fpath, "rb") as fh:
        client.post("/workbench/project/corpus/upload", files={"files": ("pr.txt", fh, "text/plain")})

    from structural_tree_app.services.project_service import ProjectService

    ps = ProjectService(ws)
    doc_id = ps.load_project(pid).ingested_document_ids[0]
    apply_manual_corpus_bootstrap(
        ps.governance_store(), pid, doc_id, "authoritative_active", actor="test", rationale="t"
    )

    r = client.post(
        "/workbench/project/corpus/projection/binding",
        data={"retrieval_binding": "explicit_projection"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    page = client.get("/workbench/project/corpus")
    assert "explicit_projection" in page.text

    client.post("/workbench/project/corpus/projection/sync-legacy-allowed", follow_redirects=False)
    proj = ps.load_project(pid)
    assert doc_id in proj.active_code_context.allowed_document_ids


def test_orchestrator_after_bootstrap_explicit(client: TestClient, tmp_path) -> None:
    pid = _session_project(client)
    ws = tmp_path / "ws"
    fpath = tmp_path / "orch.txt"
    fpath.write_text(
        "Steel design provisions unique_orch_token_z9 for flexure.\n",
        encoding="utf-8",
    )
    with open(fpath, "rb") as fh:
        client.post("/workbench/project/corpus/upload", files={"files": ("orch.txt", fh, "text/plain")})

    from structural_tree_app.services.project_service import ProjectService

    ps = ProjectService(ws)
    doc_id = ps.load_project(pid).ingested_document_ids[0]
    ing = DocumentIngestionService(ps, pid)
    doc = ing.load_document(doc_id)
    doc.approval_status = DocumentApprovalStatus.APPROVED
    doc.normative_classification = NormativeClassification.PRIMARY_STANDARD
    doc.standard_family = "AISC"
    ing.save_document(doc)

    apply_manual_corpus_bootstrap(
        ps.governance_store(), pid, doc_id, "authoritative_active", actor="test", rationale="t"
    )
    gstore = ps.governance_store()
    proj = gstore.try_load_active_knowledge_projection(pid)
    assert proj is not None
    gstore.save_active_knowledge_projection(
        ActiveKnowledgeProjection(
            project_id=pid,
            schema_version="g3.1",
            updated_at=proj.updated_at,
            retrieval_binding=GovernanceRetrievalBinding.EXPLICIT_PROJECTION,
            authoritative_document_ids=(doc_id,),
            supporting_document_ids=proj.supporting_document_ids,
            excluded_from_authoritative_document_ids=proj.excluded_from_authoritative_document_ids,
            notes=proj.notes or "",
        )
    )

    q = LocalAssistQuery(
        project_id=pid,
        retrieval_query_text="unique_orch_token_z9 flexure",
        citation_authority="normative_active_primary",
        retrieval_limit=10,
    )
    out = LocalAssistOrchestrator(ps).run(q)
    assert not out.refusal_reasons
    assert out.citations
    assert any(
        "unique_orch_token_z9" in (c.snippet or "").lower()
        for c in out.citations
    )


def test_bad_project_session_cleared_on_corpus(monkeypatch, tmp_path) -> None:
    ws = tmp_path / "ws"
    monkeypatch.setenv("STRUCTURAL_TREE_WORKSPACE", str(ws))
    client = TestClient(create_app())
    client.post(
        "/workbench/project/create",
        data={"name": "X", "description": "", "language": "es", "unit_system": "SI", "primary_standard_family": "AISC"},
    )
    hub = client.get("/workbench")
    import re

    m = re.search(r"<code>(proj_[a-z0-9]+)</code>", hub.text)
    assert m
    pid = m.group(1)
    import shutil

    shutil.rmtree(ws / pid, ignore_errors=True)

    r = client.get("/workbench/project/corpus", follow_redirects=False)
    assert r.status_code == 303


def test_corpus_bootstrap_service_errors_without_governance_record(client: TestClient, tmp_path) -> None:
    from structural_tree_app.services.corpus_bootstrap_service import CorpusBootstrapError

    pid = _session_project(client)
    from structural_tree_app.services.project_service import ProjectService

    ps = ProjectService(tmp_path / "ws")
    with pytest.raises(CorpusBootstrapError):
        apply_manual_corpus_bootstrap(
            ps.governance_store(), pid, "doc_nonexistent", "pending_review", actor="t"
        )
