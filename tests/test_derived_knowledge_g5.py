"""G5 — derived knowledge layer: generation, linkage, regeneration, determinism, non-interference."""

from __future__ import annotations

import json
from pathlib import Path

from structural_tree_app.domain.enums import NormativeClassification
from structural_tree_app.domain.governance_enums import GovernanceRetrievalBinding
from structural_tree_app.domain.governance_models import ActiveKnowledgeProjection
from structural_tree_app.domain.local_assist_contract import LocalAssistQuery
from structural_tree_app.domain.models import utc_now
from structural_tree_app.services.derived_knowledge_service import DerivedKnowledgeService
from structural_tree_app.services.document_service import DocumentIngestionService
from structural_tree_app.services.governance_store import GovernanceStore
from structural_tree_app.services.local_assist_orchestrator import LocalAssistOrchestrator
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.services.retrieval_service import DocumentRetrievalService


def _ingest_normative(ps: ProjectService, project_id: str, tmp: Path, body: str, name: str = "a.txt") -> str:
    src = tmp / name
    src.write_text(body, encoding="utf-8")
    ing = DocumentIngestionService(ps, project_id)
    r = ing.ingest_local_file(
        src,
        title="Manual",
        topics=["beams", "steel"],
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="AISC",
    )
    assert r.document
    ing.approve_document(r.document.id)
    ing.activate_for_normative_corpus(r.document.id)
    return r.document.id


def test_g5_generates_digest_and_fragment_anchors(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    doc_id = _ingest_normative(
        ps,
        p.id,
        tmp_path,
        "Steel flexure equation check capacity demand limit state phi.",
    )
    dk = DerivedKnowledgeService(ps)
    b = dk.regenerate(p.id)
    assert b.source_fingerprint
    assert len(b.source_fingerprint) == 64
    assert b.artifacts.document_digests
    d0 = b.artifacts.document_digests[0]
    assert d0.document_id == doc_id
    assert d0.fragment_anchors
    a0 = d0.fragment_anchors[0]
    assert a0.document_id == doc_id
    assert a0.fragment_id
    assert a0.document_content_hash
    assert a0.fragment_content_hash
    assert b.artifacts.formula_registry_entries
    assert all(f.non_authoritative for f in b.artifacts.formula_registry_entries)


def test_g5_regeneration_bumps_version_when_fingerprint_changes(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    _ingest_normative(ps, p.id, tmp_path, "First corpus text equation.", name="one.txt")
    dk = DerivedKnowledgeService(ps)
    b1 = dk.regenerate(p.id)
    assert b1.bundle_version == 1
    # Same corpus → idempotent (no version bump)
    b1b = dk.regenerate(p.id)
    assert b1b.bundle_version == 1

    _ingest_normative(ps, p.id, tmp_path, "Second document adds new material check.", name="two.txt")
    b2 = dk.regenerate(p.id)
    assert b2.bundle_version == 2
    assert b2.source_fingerprint != b1.source_fingerprint


def test_g5_backward_compat_missing_bundle(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    dk = DerivedKnowledgeService(ps)
    assert dk.try_load_bundle(p.id) is None


def test_g5_deterministic_canonical_payload_ordering(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    _ingest_normative(ps, p.id, tmp_path, "Deterministic ordering equation formula.", name="d.txt")
    dk = DerivedKnowledgeService(ps)
    b = dk.regenerate(p.id)
    c1 = json.dumps(dk.bundle_to_canonical_dict(b), sort_keys=True)
    b2 = dk.regenerate(p.id)
    c2 = json.dumps(dk.bundle_to_canonical_dict(b2), sort_keys=True)
    assert c1 == c2


def test_g5_retrieval_and_orchestrator_unchanged_by_default(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    _ingest_normative(ps, p.id, tmp_path, "Unique token zeta equation flexure.", name="z.txt")
    r_before = DocumentRetrievalService(ps, p.id).search("zeta", citation_authority="normative_active_primary")
    q = LocalAssistQuery(project_id=p.id, retrieval_query_text="zeta flexure")
    o_before = LocalAssistOrchestrator(ps).run(q)

    DerivedKnowledgeService(ps).regenerate(p.id)

    r_after = DocumentRetrievalService(ps, p.id).search("zeta", citation_authority="normative_active_primary")
    o_after = LocalAssistOrchestrator(ps).run(q)

    assert r_before.status == r_after.status
    assert len(r_before.hits) == len(r_after.hits)
    if r_before.hits:
        assert [h.document_id for h in r_before.hits] == [h.document_id for h in r_after.hits]
        assert [h.fragment_id for h in r_before.hits] == [h.fragment_id for h in r_after.hits]
    assert o_before.answer_status == o_after.answer_status
    assert o_before.citations == o_after.citations


def test_g5_explicit_projection_links_only_authoritative_docs(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    da = _ingest_normative(ps, p.id, tmp_path, "Auth only token alpha.", name="aa.txt")
    _ingest_normative(ps, p.id, tmp_path, "Other token beta.", name="bb.txt")
    gs: GovernanceStore = ps.governance_store()
    cur = gs.try_load_active_knowledge_projection(p.id)
    assert cur is not None
    gs.save_active_knowledge_projection(
        ActiveKnowledgeProjection(
            project_id=p.id,
            schema_version=cur.schema_version,
            updated_at=utc_now(),
            retrieval_binding=GovernanceRetrievalBinding.EXPLICIT_PROJECTION,
            authoritative_document_ids=(da,),
            supporting_document_ids=cur.supporting_document_ids,
            excluded_from_authoritative_document_ids=cur.excluded_from_authoritative_document_ids,
            notes=cur.notes,
        )
    )
    b = DerivedKnowledgeService(ps).regenerate(p.id)
    ids = {d.document_id for d in b.artifacts.document_digests}
    assert ids == {da}
