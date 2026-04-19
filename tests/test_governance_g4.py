"""Phase G4 — governed active knowledge projection wired into retrieval + local assist orchestrator."""

from __future__ import annotations

from pathlib import Path

from structural_tree_app.domain.enums import NormativeClassification
from structural_tree_app.domain.governance_enums import DocumentGovernanceDisposition, GovernanceRetrievalBinding
from structural_tree_app.domain.governance_models import (
    ActiveKnowledgeProjection,
    DocumentGovernanceIndex,
    DocumentGovernanceRecord,
)
from structural_tree_app.domain.local_assist_contract import LocalAssistQuery
from structural_tree_app.domain.models import utc_now
from structural_tree_app.services.document_service import DocumentIngestionService
from structural_tree_app.services.governance_store import GovernanceStore
from structural_tree_app.services.local_assist_orchestrator import LocalAssistOrchestrator
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.services.retrieval_service import DocumentRetrievalService


def _ingest_primary(
    ps: ProjectService,
    project_id: str,
    tmp_path: Path,
    *,
    filename: str,
    body: str,
    title: str,
) -> str:
    src = tmp_path / filename
    src.write_text(body, encoding="utf-8")
    ing = DocumentIngestionService(ps, project_id)
    r = ing.ingest_local_file(
        src,
        title=title,
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="AISC",
    )
    assert r.document
    ing.approve_document(r.document.id)
    ing.activate_for_normative_corpus(r.document.id)
    return r.document.id


def _set_explicit_projection(
    gs: GovernanceStore,
    project_id: str,
    *,
    authoritative_document_ids: tuple[str, ...],
) -> None:
    cur = gs.try_load_active_knowledge_projection(project_id)
    assert cur is not None
    updated = ActiveKnowledgeProjection(
        project_id=cur.project_id,
        schema_version=cur.schema_version,
        updated_at=utc_now(),
        retrieval_binding=GovernanceRetrievalBinding.EXPLICIT_PROJECTION,
        authoritative_document_ids=authoritative_document_ids,
        supporting_document_ids=cur.supporting_document_ids,
        excluded_from_authoritative_document_ids=cur.excluded_from_authoritative_document_ids,
        notes=cur.notes,
    )
    gs.save_active_knowledge_projection(updated)


def test_g4_legacy_binding_default_normative_source(tmp_path: Path) -> None:
    """Projects keep legacy_allowed_documents unless projection explicitly opts into explicit_projection."""
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    doc_id = _ingest_primary(
        ps,
        p.id,
        tmp_path,
        filename="leg.txt",
        body="Steel flexure resistance factors for beam design.",
        title="Manual",
    )
    r = DocumentRetrievalService(ps, p.id).search("flexure", citation_authority="normative_active_primary")
    assert r.status == "ok"
    assert r.hits
    assert r.normative_retrieval_source == "legacy_allowed_documents"
    assert r.hits[0].document_id == doc_id
    assert r.governance_normative_block is None


def test_g4_explicit_projection_normative_only_authoritative_doc(tmp_path: Path) -> None:
    """explicit_projection: normative path ignores allowed_document_ids; only authoritative ids in projection."""
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    da = _ingest_primary(
        ps,
        p.id,
        tmp_path,
        filename="a.txt",
        body="Authoritative corpus unique_token_alpha_only.",
        title="A",
    )
    _ingest_primary(
        ps,
        p.id,
        tmp_path,
        filename="b.txt",
        body="Secondary allowed doc unique_token_beta_only.",
        title="B",
    )
    gs = ps.governance_store()
    _set_explicit_projection(gs, p.id, authoritative_document_ids=(da,))
    dr = DocumentRetrievalService(ps, p.id)
    ra = dr.search("unique_token_alpha_only", citation_authority="normative_active_primary")
    assert ra.status == "ok"
    assert ra.normative_retrieval_source == "explicit_projection"
    assert [h.document_id for h in ra.hits] == [da]
    assert any("explicit active knowledge projection" in w for w in ra.governance_warnings)

    rb = dr.search("unique_token_beta_only", citation_authority="normative_active_primary")
    assert rb.status == "insufficient_evidence"
    assert rb.normative_retrieval_source == "explicit_projection"
    assert not rb.hits


def test_g4_explicit_conflict_blocks_normative_retrieval_and_orchestrator(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    doc_id = _ingest_primary(
        ps,
        p.id,
        tmp_path,
        filename="c.txt",
        body="Normative text about conflicting governance state.",
        title="C",
    )
    gs = ps.governance_store()
    idx = gs.try_load_document_governance_index(p.id)
    assert idx is not None
    rec = idx.by_document_id[doc_id]
    bumped = DocumentGovernanceRecord(
        document_id=doc_id,
        pipeline_stage=rec.pipeline_stage,
        disposition=DocumentGovernanceDisposition.CONFLICTING_UNRESOLVED,
        updated_at=utc_now(),
        notes=rec.notes,
        analysis=rec.analysis,
        classification=rec.classification,
    )
    gs.save_document_governance_index(
        DocumentGovernanceIndex(
            project_id=p.id,
            schema_version=idx.schema_version,
            updated_at=utc_now(),
            by_document_id={**idx.by_document_id, doc_id: bumped},
        )
    )
    _set_explicit_projection(gs, p.id, authoritative_document_ids=(doc_id,))
    rr = DocumentRetrievalService(ps, p.id).search("Normative", citation_authority="normative_active_primary")
    assert rr.status == "insufficient_evidence"
    assert rr.governance_normative_block == "conflict"
    assert "conflicting_unresolved" in rr.message

    orch = LocalAssistOrchestrator(ps)
    resp = orch.run(LocalAssistQuery(project_id=p.id, retrieval_query_text="Normative"))
    assert resp.answer_status == "insufficient_evidence"
    assert resp.refusal_reasons
    assert resp.refusal_reasons[0].code == "GOVERNANCE_CONFLICT_BLOCKS_NORMATIVE"


def test_g4_explicit_missing_governance_index_refuses(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    doc_id = _ingest_primary(
        ps,
        p.id,
        tmp_path,
        filename="d.txt",
        body="Some normative provisions.",
        title="D",
    )
    gs = ps.governance_store()
    _set_explicit_projection(gs, p.id, authoritative_document_ids=(doc_id,))
    idx_path = tmp_path / "ws" / p.id / "governance" / "document_governance_index.json"
    assert idx_path.is_file()
    idx_path.unlink()
    rr = DocumentRetrievalService(ps, p.id).search("provisions", citation_authority="normative_active_primary")
    assert rr.status == "insufficient_evidence"
    assert rr.governance_normative_block == "missing_index"
    resp = LocalAssistOrchestrator(ps).run(LocalAssistQuery(project_id=p.id, retrieval_query_text="provisions"))
    assert resp.refusal_reasons[0].code == "GOVERNANCE_EXPLICIT_PROJECTION_UNAVAILABLE"


def test_g4_explicit_empty_authoritative_set_refuses(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    _ingest_primary(
        ps,
        p.id,
        tmp_path,
        filename="e.txt",
        body="Body.",
        title="E",
    )
    gs = ps.governance_store()
    _set_explicit_projection(gs, p.id, authoritative_document_ids=())
    rr = DocumentRetrievalService(ps, p.id).search("Body", citation_authority="normative_active_primary")
    assert rr.status == "insufficient_evidence"
    assert rr.governance_normative_block == "empty_authoritative"


def test_g4_approved_ingested_stays_distinct_from_explicit_normative(tmp_path: Path) -> None:
    """approved_ingested is not narrowed by explicit authoritative lists (supporting / audit path)."""
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    da = _ingest_primary(
        ps,
        p.id,
        tmp_path,
        filename="fa.txt",
        body="Alpha segment for normative.",
        title="FA",
    )
    db = _ingest_primary(
        ps,
        p.id,
        tmp_path,
        filename="fb.txt",
        body="Beta_segment_supporting_only_xyz.",
        title="FB",
    )
    gs = ps.governance_store()
    _set_explicit_projection(gs, p.id, authoritative_document_ids=(da,))
    dr = DocumentRetrievalService(ps, p.id)
    sup = dr.search("Beta_segment_supporting_only_xyz", citation_authority="approved_ingested")
    assert sup.status == "ok"
    assert sup.hits
    assert sup.hits[0].document_id == db
    assert sup.normative_retrieval_source == "n_a"

    norm = dr.search("Beta_segment_supporting_only_xyz", citation_authority="normative_active_primary")
    assert norm.status == "insufficient_evidence"
    assert norm.normative_retrieval_source == "explicit_projection"


def test_g4_orchestrator_normative_uses_retrieval_binding_explicit(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    da = _ingest_primary(
        ps,
        p.id,
        tmp_path,
        filename="g.txt",
        body="Orchestrator token orch_unique_aa.",
        title="G",
    )
    gs = ps.governance_store()
    _set_explicit_projection(gs, p.id, authoritative_document_ids=(da,))
    r = LocalAssistOrchestrator(ps).run(
        LocalAssistQuery(project_id=p.id, retrieval_query_text="orch_unique_aa")
    )
    assert r.answer_status == "evidence_passages_assembled"
    assert r.citations
    assert r.normative_retrieval_binding == "explicit_projection"
    assert any("explicit active knowledge projection" in w for w in r.warnings)


def test_g4_governance_warnings_deterministic_ordering(tmp_path: Path) -> None:
    """explicit_projection + ids missing from index produce sorted, stable warning lines."""
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    da = _ingest_primary(
        ps,
        p.id,
        tmp_path,
        filename="h1.txt",
        body="Hit text.",
        title="H1",
    )
    gs = ps.governance_store()
    # Authoritative lists a fake id (sorted before/after real ids) and the real id — warnings sorted by id.
    _set_explicit_projection(gs, p.id, authoritative_document_ids=("doc_zzzzzzzzzzzz", da))
    rr = DocumentRetrievalService(ps, p.id).search("Hit", citation_authority="normative_active_primary")
    assert rr.status == "ok"
    assert rr.hits[0].document_id == da
    index_warns = [w for w in rr.governance_warnings if "not present in governance index" in w]
    assert len(index_warns) == 1
    assert "doc_zzzzzzzzzzzz" in index_warns[0]
    # _filter_authoritative_ids_against_index iterates sorted(authoritative_ids); order is stable.
    assert index_warns == sorted(index_warns)