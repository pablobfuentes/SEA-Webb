from __future__ import annotations

from pathlib import Path

from structural_tree_app.domain.enums import NormativeClassification
from structural_tree_app.services.document_service import DocumentIngestionService
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.services.retrieval_service import DocumentRetrievalService


def _ingest_approved_active_normative(
    tmp_path: Path,
) -> tuple[ProjectService, str, str]:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    src = tmp_path / "code.txt"
    src.write_text(
        "Steel design provisions for beam flexure. Limit state and resistance factors.",
        encoding="utf-8",
    )
    ing = DocumentIngestionService(ps, p.id)
    res = ing.ingest_local_file(
        src,
        title="Steel manual",
        topics=["steel", "beams"],
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="AISC",
    )
    assert res.document
    doc_id = res.document.id
    ing.approve_document(doc_id)
    ing.activate_for_normative_corpus(doc_id)
    return ps, p.id, doc_id


def test_retrieval_hits_normative_corpus(tmp_path: Path) -> None:
    ps, project_id, doc_id = _ingest_approved_active_normative(tmp_path)
    r = DocumentRetrievalService(ps, project_id)
    out = r.search("flexure resistance", citation_authority="normative_active_primary")
    assert out.status == "ok"
    assert out.hits
    h = out.hits[0]
    assert h.document_id == doc_id
    assert h.chunk_index >= 0
    assert h.fragment_id
    assert h.content_hash
    assert h.fragment_content_hash
    assert h.document_title == "Steel manual"
    assert h.normative_classification == "primary_standard"
    assert h.standard_family == "AISC"
    assert h.snippet


def test_retrieval_filtered_by_document_id(tmp_path: Path) -> None:
    ps, project_id, doc_id = _ingest_approved_active_normative(tmp_path)
    r = DocumentRetrievalService(ps, project_id)
    out = r.search("steel", document_ids={doc_id}, citation_authority="normative_active_primary")
    assert out.status == "ok"
    out2 = r.search("steel", document_ids={"doc_nonexistent_aaaaaaaaaaaa"}, citation_authority="normative_active_primary")
    assert out2.status == "insufficient_evidence"


def test_unknown_classification_excluded_from_normative(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    src = tmp_path / "u.txt"
    src.write_text("Supporting commentary only.", encoding="utf-8")
    ing = DocumentIngestionService(ps, p.id)
    res = ing.ingest_local_file(
        src,
        title="Support doc",
        normative_classification=NormativeClassification.UNKNOWN,
    )
    assert res.document
    ing.approve_document(res.document.id)
    ing.activate_for_normative_corpus(res.document.id)
    r = DocumentRetrievalService(ps, p.id)
    out = r.search("commentary", citation_authority="normative_active_primary")
    assert out.status == "insufficient_evidence"
    assert "No passages" in out.message


def test_insufficient_evidence_when_not_active(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    src = tmp_path / "n.txt"
    src.write_text("Beam design flexure formula.", encoding="utf-8")
    ing = DocumentIngestionService(ps, p.id)
    res = ing.ingest_local_file(
        src,
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="AISC",
    )
    assert res.document
    ing.approve_document(res.document.id)
    r = DocumentRetrievalService(ps, p.id)
    out = r.search("flexure", citation_authority="normative_active_primary")
    assert out.status == "insufficient_evidence"


def test_approved_ingested_mode_finds_unknown_classification(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    src = tmp_path / "u.txt"
    src.write_text("Supporting commentary only.", encoding="utf-8")
    ing = DocumentIngestionService(ps, p.id)
    res = ing.ingest_local_file(src, title="S", normative_classification=NormativeClassification.UNKNOWN)
    assert res.document
    ing.approve_document(res.document.id)
    r = DocumentRetrievalService(ps, p.id)
    out = r.search("commentary", citation_authority="approved_ingested")
    assert out.status == "ok"
    assert out.hits
