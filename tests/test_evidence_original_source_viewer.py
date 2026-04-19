"""Evidence UX — original source viewer: routes, PDF/text embedding, honest fallbacks, integrity checks."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from structural_tree_app.domain.enums import NormativeClassification
from structural_tree_app.services.document_service import DocumentIngestionService
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.workbench.app import create_app
from structural_tree_app.workbench.evidence_pdf_pages import pdf_url_fragment_page_open_params
from structural_tree_app.workbench.evidence_source_view import build_evidence_source_view_context


@pytest.fixture
def client(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    monkeypatch.setenv("STRUCTURAL_TREE_WORKSPACE", str(ws))
    return TestClient(create_app())


def _session_project(client: TestClient) -> str:
    r = client.post(
        "/workbench/project/create",
        data={"name": "EV", "description": "", "language": "es", "unit_system": "SI", "primary_standard_family": "AISC"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    hub = client.get("/workbench")
    m = re.search(r"<code>(proj_[a-z0-9]+)</code>", hub.text)
    assert m
    return m.group(1)


FIXTURE_PDF = Path(__file__).resolve().parent / "fixtures" / "sample_text.pdf"


def test_citation_route_is_source_oriented(client: TestClient, tmp_path) -> None:
    _session_project(client)
    hub = client.get("/workbench")
    pid = re.search(r"<code>(proj_[a-z0-9]+)</code>", hub.text).group(1)
    ps = ProjectService(tmp_path / "ws")
    src = tmp_path / "src.txt"
    src.write_text("Unique evidence body XYZ123 for source view.", encoding="utf-8")
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(src, title="T", normative_classification=NormativeClassification.PRIMARY_STANDARD)
    assert ir.document
    doc_id = ir.document.id
    frag_id = ing.load_fragments(doc_id)[0].id

    page = client.get(f"/workbench/project/evidence/fragment/{doc_id}/{frag_id}")
    assert page.status_code == 200
    assert "evidence-source-view" in page.text
    assert "Citation source view" in page.text
    assert "Unique evidence body XYZ123 for source view." in page.text
    assert doc_id in page.text
    assert frag_id in page.text
    assert "location_precision" in page.text.lower() or "Precision:" in page.text


def test_pdf_known_page_shows_pdf_context(client: TestClient, tmp_path) -> None:
    assert FIXTURE_PDF.is_file(), "tests/fixtures/sample_text.pdf required"
    _session_project(client)
    pid = re.search(r"<code>(proj_[a-z0-9]+)</code>", client.get("/workbench").text).group(1)
    ps = ProjectService(tmp_path / "ws")
    pdf_path = tmp_path / "ingest.pdf"
    pdf_path.write_bytes(FIXTURE_PDF.read_bytes())
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(pdf_path, title="PDF fixture", normative_classification=NormativeClassification.PRIMARY_STANDARD)
    assert ir.document
    assert ir.status == "ingested"
    doc_id = ir.document.id
    frags = ing.load_fragments(doc_id)
    assert frags
    frag = next(f for f in frags if "Page one" in f.text or "paragraph" in f.text)
    page = client.get(f"/workbench/project/evidence/fragment/{doc_id}/{frag.id}")
    assert page.status_code == 200
    assert "pdf_side_by_side" in page.text
    assert "Original PDF" in page.text
    # Primary embed: PDF.js viewer iframe
    assert f"/source/{doc_id}/viewer" in page.text
    assert "<iframe" in page.text
    # Fallback: direct file link still present
    assert f"/source/{doc_id}/file" in page.text
    assert "new tab" in page.text.lower() or "Open in new tab" in page.text
    assert "exact_page" in page.text or "page_range" in page.text or "unknown_page" in page.text


def test_source_file_route_serves_pdf(client: TestClient, tmp_path) -> None:
    assert FIXTURE_PDF.is_file()
    _session_project(client)
    pid = re.search(r"<code>(proj_[a-z0-9]+)</code>", client.get("/workbench").text).group(1)
    ps = ProjectService(tmp_path / "ws")
    pdf_path = tmp_path / "ingest.pdf"
    pdf_path.write_bytes(FIXTURE_PDF.read_bytes())
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(pdf_path, title="P", normative_classification=NormativeClassification.PRIMARY_STANDARD)
    assert ir.document
    doc_id = ir.document.id
    r = client.get(f"/workbench/project/evidence/source/{doc_id}/file")
    assert r.status_code == 200
    assert r.headers.get("content-type", "").startswith("application/pdf")
    assert r.content[:4] == b"%PDF"


def test_source_file_404_when_integrity_fails(client: TestClient, tmp_path) -> None:
    _session_project(client)
    pid = re.search(r"<code>(proj_[a-z0-9]+)</code>", client.get("/workbench").text).group(1)
    ps = ProjectService(tmp_path / "ws")
    src = tmp_path / "t.txt"
    src.write_text("Integrity test body.", encoding="utf-8")
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(src, title="I", normative_classification=NormativeClassification.PRIMARY_STANDARD)
    assert ir.document
    doc_id = ir.document.id
    p = Path(ir.document.file_path)
    assert p.is_file()
    p.write_bytes(b"tampered")

    r = client.get(f"/workbench/project/evidence/source/{doc_id}/file")
    assert r.status_code == 404


def test_fragment_fallback_when_original_missing(client: TestClient, tmp_path) -> None:
    _session_project(client)
    pid = re.search(r"<code>(proj_[a-z0-9]+)</code>", client.get("/workbench").text).group(1)
    ps = ProjectService(tmp_path / "ws")
    src = tmp_path / "gone.txt"
    src.write_text("Still have fragment text.", encoding="utf-8")
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(src, title="G", normative_classification=NormativeClassification.PRIMARY_STANDARD)
    assert ir.document
    doc_id = ir.document.id
    frag = ing.load_fragments(doc_id)[0]
    Path(ir.document.file_path).unlink()

    page = client.get(f"/workbench/project/evidence/fragment/{doc_id}/{frag.id}")
    assert page.status_code == 200
    assert "fragment_only" in page.text
    assert "Fallback:" in page.text
    assert "Still have fragment text." in page.text


def test_evidence_source_requires_session(client: TestClient, tmp_path) -> None:
    _session_project(client)
    pid = re.search(r"<code>(proj_[a-z0-9]+)</code>", client.get("/workbench").text).group(1)
    ps = ProjectService(tmp_path / "ws")
    src = tmp_path / "s.txt"
    src.write_text("Session gate.", encoding="utf-8")
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(src, title="S", normative_classification=NormativeClassification.PRIMARY_STANDARD)
    doc_id = ir.document.id

    c2 = TestClient(client.app)
    r = c2.get(f"/workbench/project/evidence/source/{doc_id}/file", follow_redirects=False)
    assert r.status_code == 303

    r2 = c2.get(f"/workbench/project/evidence/fragment/{doc_id}/frag_bad", follow_redirects=False)
    assert r2.status_code == 303


def test_source_file_unknown_document_404(client: TestClient, tmp_path) -> None:
    _session_project(client)
    r = client.get("/workbench/project/evidence/source/doc_nonexistent/file")
    assert r.status_code == 404


def test_pdf_open_url_matches_physical_page_1based(client: TestClient, tmp_path) -> None:
    assert FIXTURE_PDF.is_file()
    _session_project(client)
    pid = re.search(r"<code>(proj_[a-z0-9]+)</code>", client.get("/workbench").text).group(1)
    ps = ProjectService(tmp_path / "ws")
    pdf_path = tmp_path / "ingest.pdf"
    pdf_path.write_bytes(FIXTURE_PDF.read_bytes())
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(pdf_path, title="Align", normative_classification=NormativeClassification.PRIMARY_STANDARD)
    doc = ir.document
    assert doc
    frag = next(f for f in ing.load_fragments(doc.id) if "Page one" in f.text)
    ctx = build_evidence_source_view_context(doc, frag)
    assert ctx["pdf_viewer_target_page_1based"] == frag.page_start
    assert ctx["pdf_open_url"]
    assert ctx["pdf_open_url"].endswith(pdf_url_fragment_page_open_params(frag.page_start))


def test_verified_file_not_labeled_unavailable(client: TestClient, tmp_path) -> None:
    """Hash-verified sources must not use the 'missing file' wording."""
    _session_project(client)
    pid = re.search(r"<code>(proj_[a-z0-9]+)</code>", client.get("/workbench").text).group(1)
    ps = ProjectService(tmp_path / "ws")
    src = tmp_path / "ok.txt"
    src.write_text("Embed note test body.", encoding="utf-8")
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(src, title="E", normative_classification=NormativeClassification.PRIMARY_STANDARD)
    doc_id = ir.document.id
    frag_id = ing.load_fragments(doc_id)[0].id
    page = client.get(f"/workbench/project/evidence/fragment/{doc_id}/{frag_id}")
    assert page.status_code == 200
    assert "Governed file verified" in page.text
    assert "failed integrity check" not in page.text.lower()


def test_pdf_viewer_route_returns_html(client: TestClient, tmp_path) -> None:
    """PDF.js viewer route returns standalone HTML at the correct page."""
    assert FIXTURE_PDF.is_file()
    _session_project(client)
    pid = re.search(r"<code>(proj_[a-z0-9]+)</code>", client.get("/workbench").text).group(1)
    ps = ProjectService(tmp_path / "ws")
    pdf_path = tmp_path / "ingest.pdf"
    pdf_path.write_bytes(FIXTURE_PDF.read_bytes())
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(pdf_path, title="Viewer test", normative_classification=NormativeClassification.PRIMARY_STANDARD)
    doc_id = ir.document.id

    r = client.get(f"/workbench/project/evidence/source/{doc_id}/viewer?page=1")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "pdfjs-dist" in r.text
    assert f"/workbench/project/evidence/source/{doc_id}/file" in r.text
    assert "Viewer test" in r.text


def test_pdf_viewer_route_404_for_unknown_doc(client: TestClient) -> None:
    _session_project(client)
    r = client.get("/workbench/project/evidence/source/doc_nope/viewer?page=1")
    assert r.status_code == 404


def test_pdf_viewer_route_requires_session(client: TestClient, tmp_path) -> None:
    _session_project(client)
    pid = re.search(r"<code>(proj_[a-z0-9]+)</code>", client.get("/workbench").text).group(1)
    ps = ProjectService(tmp_path / "ws")
    pdf_path = tmp_path / "ingest2.pdf"
    pdf_path.write_bytes(FIXTURE_PDF.read_bytes())
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(pdf_path, title="V2", normative_classification=NormativeClassification.PRIMARY_STANDARD)
    doc_id = ir.document.id

    c2 = TestClient(client.app)
    r = c2.get(f"/workbench/project/evidence/source/{doc_id}/viewer?page=1", follow_redirects=False)
    assert r.status_code == 303


def test_evidence_source_view_embeds_viewer_iframe(client: TestClient, tmp_path) -> None:
    """Fragment detail page for PDF must use the PDF.js viewer iframe, not raw object embed."""
    assert FIXTURE_PDF.is_file()
    _session_project(client)
    pid = re.search(r"<code>(proj_[a-z0-9]+)</code>", client.get("/workbench").text).group(1)
    ps = ProjectService(tmp_path / "ws")
    pdf_path = tmp_path / "ingest3.pdf"
    pdf_path.write_bytes(FIXTURE_PDF.read_bytes())
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(pdf_path, title="Iframe test", normative_classification=NormativeClassification.PRIMARY_STANDARD)
    doc_id = ir.document.id
    frags = ing.load_fragments(doc_id)
    frag_id = frags[0].id

    page = client.get(f"/workbench/project/evidence/fragment/{doc_id}/{frag_id}")
    assert page.status_code == 200
    # Must reference the PDF.js viewer route (not raw object/iframe of the PDF file directly)
    assert f"/source/{doc_id}/viewer" in page.text
    assert "<iframe" in page.text
    # Fallback new-tab link should still be present
    assert f"/source/{doc_id}/file" in page.text


def test_pdf_viewer_url_in_context(tmp_path) -> None:
    """build_evidence_source_view_context must return pdf_viewer_url for known PDFs."""
    from structural_tree_app.domain.models import Document, DocumentFragment
    from structural_tree_app.domain.enums import AuthorityLevel, DocumentApprovalStatus, NormativeClassification
    import hashlib

    fake_pdf = tmp_path / "doc.pdf"
    content = b"%PDF-1.4 minimal"
    fake_pdf.write_bytes(content)
    d = Document(
        title="v",
        author="",
        edition="",
        version_label="1",
        publication_year=None,
        document_type="t",
        authority_level=AuthorityLevel.PRIMARY,
        topics=[],
        language="es",
        file_path=str(fake_pdf),
        content_hash=hashlib.sha256(content).hexdigest(),
        approval_status=DocumentApprovalStatus.PENDING,
        normative_classification=NormativeClassification.UNKNOWN,
    )
    f = DocumentFragment(
        document_id=d.id,
        chapter="",
        section="",
        page_start=2,
        page_end=2,
        fragment_type="chunk",
        topic_tags=[],
        authority_level=AuthorityLevel.PRIMARY,
        text="body",
        document_approval_status=DocumentApprovalStatus.PENDING,
        document_normative_classification=NormativeClassification.UNKNOWN,
    )
    ctx = build_evidence_source_view_context(d, f)
    assert ctx["pdf_viewer_url"] is not None
    assert "/viewer?page=2" in ctx["pdf_viewer_url"]
    assert ctx["pdf_open_url"] is not None
    assert "#page=2" in ctx["pdf_open_url"]


def test_view_model_page_range_label() -> None:
    from structural_tree_app.domain.models import Document, DocumentFragment
    from structural_tree_app.domain.enums import AuthorityLevel, DocumentApprovalStatus, NormativeClassification

    d = Document(
        title="x",
        author="",
        edition="",
        version_label="1",
        publication_year=None,
        document_type="t",
        authority_level=AuthorityLevel.PRIMARY,
        topics=[],
        language="es",
        file_path="/fake/doc.pdf",
        content_hash="0" * 64,
        approval_status=DocumentApprovalStatus.PENDING,
        normative_classification=NormativeClassification.UNKNOWN,
    )
    f = DocumentFragment(
        document_id=d.id,
        chapter="",
        section="",
        page_start=2,
        page_end=3,
        fragment_type="chunk",
        topic_tags=[],
        authority_level=AuthorityLevel.PRIMARY,
        text="hi",
        document_approval_status=DocumentApprovalStatus.PENDING,
        document_normative_classification=NormativeClassification.UNKNOWN,
    )
    ctx = build_evidence_source_view_context(d, f)
    assert ctx["location_precision"] == "page_range"
    assert "2" in str(ctx["location_note"]) and "3" in str(ctx["location_note"])
