from __future__ import annotations

import json
from pathlib import Path

import pytest

from structural_tree_app.domain.enums import NormativeClassification
from structural_tree_app.domain.governance_codec import truth_proposal_to_dict
from structural_tree_app.domain.governance_enums import (
    CorpusAssessmentCandidateRelation,
    DocumentGovernanceDisposition,
    GovernanceEventType,
)
from structural_tree_app.domain.governance_models import (
    CorpusAssessmentCandidate,
    DocumentCorpusAssessment,
    DocumentGovernanceRecord,
    DocumentGovernanceIndex,
    TruthProposal,
    TruthProposalStatus,
)
from structural_tree_app.domain.models import new_id, utc_now
from structural_tree_app.services.document_service import DocumentIngestionService
from structural_tree_app.services.retrieval_service import DocumentRetrievalService
from structural_tree_app.services.truth_proposal_service import (
    approve_truth_proposal,
    build_truth_proposal,
    persist_new_truth_proposal,
    reject_truth_proposal,
)
from structural_tree_app.services.project_service import ProjectService


def test_duplicate_proposal_then_approve_updates_projection_excluded(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "en", "SI", "AISC")
    src1 = tmp_path / "same.txt"
    src1.write_text("Identical bytes for G3 duplicate proposal.", encoding="utf-8")
    ing = DocumentIngestionService(ps, p.id)
    r1 = ing.ingest_local_file(src1, title="One", normative_classification=NormativeClassification.UNKNOWN)
    assert r1.document
    d1 = r1.document.id
    src2 = tmp_path / "same_copy.txt"
    src2.write_bytes(src1.read_bytes())
    r2 = ing.ingest_local_file(
        src2,
        title="Two",
        normative_classification=NormativeClassification.UNKNOWN,
        duplicate_policy="reingest",
    )
    assert r2.document
    d2 = r2.document.id
    gs = ps.governance_store()
    prop = build_truth_proposal(gs, p.id, d2)
    assert "g3.duplicate_exclude_copy_from_authoritative_lists" in prop.rules_applied
    assert d2 in prop.projection_delta.add_excluded_document_ids
    persist_new_truth_proposal(gs, prop)
    assert gs.try_load_truth_proposal(p.id, prop.proposal_id) is not None
    log = gs.try_load_governance_event_log(p.id)
    assert log is not None
    assert any(e.event_type == GovernanceEventType.TRUTH_PROPOSAL_CREATED for e in log.events)

    approve_truth_proposal(gs, p.id, prop.proposal_id, actor="tester", notes="ok")
    proj = gs.try_load_active_knowledge_projection(p.id)
    assert proj is not None
    assert proj.schema_version == "g3.1"
    assert d2 in proj.excluded_from_authoritative_document_ids
    approved = gs.try_load_truth_proposal(p.id, prop.proposal_id)
    assert approved is not None
    assert approved.status == TruthProposalStatus.APPROVED
    log2 = gs.try_load_governance_event_log(p.id)
    assert log2 is not None
    tail = [e.event_type for e in log2.events[-3:]]
    assert GovernanceEventType.TRUTH_PROPOSAL_APPROVED in tail
    assert GovernanceEventType.PROJECTION_UPDATED in tail


def test_contradiction_proposal_marks_both_conflicting_unresolved(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "en", "SI", "AISC")
    ing = DocumentIngestionService(ps, p.id)
    a = tmp_path / "x.txt"
    b = tmp_path / "y.txt"
    # Distinct bytes so second ingest is a separate document (same bytes would dedupe ingest).
    a.write_text("Shared stem alpha beta gamma delta.", encoding="utf-8")
    b.write_text("Shared stem alpha beta gamma delta. unique_tail_b.", encoding="utf-8")
    ra = ing.ingest_local_file(a, title="A", normative_classification=NormativeClassification.UNKNOWN)
    rb = ing.ingest_local_file(b, title="B", normative_classification=NormativeClassification.UNKNOWN)
    assert ra.document and rb.document
    da, db = ra.document.id, rb.document.id
    gs = ps.governance_store()
    assessment = DocumentCorpusAssessment(
        project_id=p.id,
        subject_document_id=da,
        candidates=(
            CorpusAssessmentCandidate(
                other_document_id=db,
                relation=CorpusAssessmentCandidateRelation.CONTRADICTION_CANDIDATE,
                confidence="high",
                signals=("test",),
            ),
        ),
    )
    gs.save_document_corpus_assessment(assessment)
    prop = build_truth_proposal(gs, p.id, da)
    assert "g3.contradiction_no_authoritative_activation" in prop.rules_applied
    assert len(prop.disposition_changes) == 2
    persist_new_truth_proposal(gs, prop)
    approve_truth_proposal(gs, p.id, prop.proposal_id)
    idx = gs.try_load_document_governance_index(p.id)
    assert idx is not None
    assert idx.by_document_id[da].disposition == DocumentGovernanceDisposition.CONFLICTING_UNRESOLVED
    assert idx.by_document_id[db].disposition == DocumentGovernanceDisposition.CONFLICTING_UNRESOLVED


def test_approve_raises_when_index_stale(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "en", "SI", "AISC")
    ing = DocumentIngestionService(ps, p.id)
    a = tmp_path / "s.txt"
    a.write_text("Body one.", encoding="utf-8")
    r = ing.ingest_local_file(a, title="S", normative_classification=NormativeClassification.UNKNOWN)
    assert r.document
    da = r.document.id
    gs = ps.governance_store()
    assessment = DocumentCorpusAssessment(
        project_id=p.id,
        subject_document_id=da,
        candidates=(
            CorpusAssessmentCandidate(
                other_document_id=da,
                relation=CorpusAssessmentCandidateRelation.SUPPORTING_CANDIDATE,
                confidence="low",
            ),
        ),
    )
    gs.save_document_corpus_assessment(assessment)
    prop = build_truth_proposal(gs, p.id, da)
    persist_new_truth_proposal(gs, prop)
    idx0 = gs.try_load_document_governance_index(p.id)
    assert idx0 is not None
    rec = idx0.by_document_id[da]
    bumped = DocumentGovernanceRecord(
        document_id=da,
        pipeline_stage=rec.pipeline_stage,
        disposition=DocumentGovernanceDisposition.ACTIVE,
        updated_at=utc_now(),
        notes=rec.notes,
        analysis=rec.analysis,
        classification=rec.classification,
    )
    gs.save_document_governance_index(
        DocumentGovernanceIndex(
            project_id=p.id,
            schema_version=idx0.schema_version,
            updated_at=utc_now(),
            by_document_id={**idx0.by_document_id, da: bumped},
        )
    )
    with pytest.raises(ValueError, match="Stale proposal"):
        approve_truth_proposal(gs, p.id, prop.proposal_id)


def test_reject_does_not_touch_projection_lists(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "en", "SI", "AISC")
    ing = DocumentIngestionService(ps, p.id)
    f = tmp_path / "z.txt"
    f.write_text("Z content.", encoding="utf-8")
    r = ing.ingest_local_file(f, title="Z", normative_classification=NormativeClassification.UNKNOWN)
    assert r.document
    gs = ps.governance_store()
    assessment = DocumentCorpusAssessment(
        project_id=p.id,
        subject_document_id=r.document.id,
        candidates=(),
    )
    gs.save_document_corpus_assessment(assessment)
    prop = build_truth_proposal(gs, p.id, r.document.id)
    persist_new_truth_proposal(gs, prop)
    before = gs.try_load_active_knowledge_projection(p.id)
    assert before is not None
    reject_truth_proposal(gs, p.id, prop.proposal_id, notes="no")
    after = gs.try_load_active_knowledge_projection(p.id)
    assert after is not None
    assert after.authoritative_document_ids == before.authoritative_document_ids
    assert after.supporting_document_ids == before.supporting_document_ids
    assert after.excluded_from_authoritative_document_ids == before.excluded_from_authoritative_document_ids


def test_truth_proposal_json_deterministic(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "en", "SI", "AISC")
    prop = TruthProposal(
        proposal_id=new_id("tpr"),
        project_id=p.id,
        subject_document_id=new_id("doc"),
        created_at="2026-01-01T00:00:00+00:00",
        status=TruthProposalStatus.PENDING_APPROVAL,
        rules_applied=("z_rule", "a_rule"),
        narrative="n",
        decision=None,
    )
    a = json.dumps(truth_proposal_to_dict(prop), sort_keys=True)
    b = json.dumps(truth_proposal_to_dict(prop), sort_keys=True)
    assert a == b
    assert '"a_rule"' in a and '"z_rule"' in a


def test_try_load_truth_proposal_missing_is_none(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "en", "SI", "AISC")
    gs = ps.governance_store()
    assert gs.try_load_truth_proposal(p.id, "tpr_aaaaaaaaaaaa") is None


def test_retrieval_unchanged_after_truth_proposal_approval(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "en", "SI", "AISC")
    src = tmp_path / "norm.txt"
    src.write_text(
        "Steel beam flexure design provisions AISC LRFD resistance factors.",
        encoding="utf-8",
    )
    ing = DocumentIngestionService(ps, p.id)
    r = ing.ingest_local_file(
        src,
        title="AISC Manual",
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="AISC",
    )
    assert r.document
    doc_id = r.document.id
    ing.approve_document(doc_id)
    ing.activate_for_normative_corpus(doc_id)
    gs = ps.governance_store()
    assessment = DocumentCorpusAssessment(
        project_id=p.id,
        subject_document_id=doc_id,
        candidates=(),
    )
    gs.save_document_corpus_assessment(assessment)
    prop = build_truth_proposal(gs, p.id, doc_id)
    persist_new_truth_proposal(gs, prop)
    dr = DocumentRetrievalService(ps, p.id)
    q = "flexure steel"
    before = dr.search(q, limit=5)
    approve_truth_proposal(gs, p.id, prop.proposal_id)
    after = dr.search(q, limit=5)
    assert before.status == after.status
    assert [h.document_id for h in before.hits] == [h.document_id for h in after.hits]
