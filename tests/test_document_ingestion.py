from __future__ import annotations

from pathlib import Path

from structural_tree_app.domain.enums import NormativeClassification
from structural_tree_app.services.document_service import DocumentIngestionService
from structural_tree_app.services.project_service import ProjectService


def test_ingest_text_file_metadata_and_chunks(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ps = ProjectService(ws)
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    src = tmp_path / "sample.txt"
    src.write_text("Paragraph one.\n\nParagraph two.\n\n" + ("x" * 100), encoding="utf-8")
    svc = DocumentIngestionService(ps, p.id)
    res = svc.ingest_local_file(
        src,
        title="My doc",
        author="A",
        topics=["steel"],
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="AISC",
    )
    assert res.status == "ingested"
    assert res.document is not None
    assert res.fragment_count >= 1
    doc = svc.load_document(res.document.id)
    assert doc.title == "My doc"
    assert doc.content_hash
    assert doc.normative_classification == NormativeClassification.PRIMARY_STANDARD
    assert doc.standard_family == "AISC"
    proj = ps.load_project(p.id)
    assert res.document.id in proj.ingested_document_ids
    assert res.document.id not in proj.active_code_context.allowed_document_ids
    frags = svc.load_fragments(res.document.id)
    assert len(frags) == res.fragment_count
    assert all(f.document_id == res.document.id for f in frags)
    assert all(f.material_content_hash == doc.content_hash for f in frags)
    assert all(f.fragment_content_hash for f in frags)


def test_duplicate_skip(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    src = tmp_path / "d.txt"
    src.write_text("same bytes", encoding="utf-8")
    svc = DocumentIngestionService(ps, p.id)
    r1 = svc.ingest_local_file(src)
    r2 = svc.ingest_local_file(src)
    assert r1.status == "ingested"
    assert r2.status == "duplicate_skipped"
    assert r1.document and r2.document
    assert r1.document.id == r2.document.id


def test_stable_fragment_ids_deterministic(tmp_path: Path) -> None:
    from structural_tree_app.services.document_service import stable_fragment_id

    a = stable_fragment_id("doc_x", 0, "hello")
    b = stable_fragment_id("doc_x", 0, "hello")
    assert a == b


def test_ingest_does_not_default_standard_family_to_project_primary(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    src = tmp_path / "nf.txt"
    src.write_text("Some normative text about beams.", encoding="utf-8")
    svc = DocumentIngestionService(ps, p.id)
    res = svc.ingest_local_file(src, title="T")
    assert res.document is not None
    doc = svc.load_document(res.document.id)
    assert doc.standard_family is None
