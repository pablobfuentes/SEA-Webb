from __future__ import annotations

import json
from pathlib import Path

import pytest

from structural_tree_app.domain.enums import NormativeClassification
from structural_tree_app.domain.governance_codec import document_corpus_assessment_to_dict
from structural_tree_app.domain.governance_enums import CorpusAssessmentCandidateRelation
from structural_tree_app.services.corpus_assessment_service import build_document_corpus_assessment
from structural_tree_app.services.document_service import DocumentIngestionService
from structural_tree_app.services.governance_store import GovernanceStore, GovernanceStoreError
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.services.retrieval_service import DocumentRetrievalService
from structural_tree_app.storage.json_repository import JsonRepository
from structural_tree_app.validation.json_schema import validate_document_corpus_assessment_payload


def _relations(assessment):
    return {(c.other_document_id, c.relation) for c in assessment.candidates}


def test_duplicate_candidate_on_reingest_same_bytes(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "en", "SI", "AISC")
    src1 = tmp_path / "same.txt"
    src1.write_text("Identical bytes for duplicate assessment.", encoding="utf-8")
    ing = DocumentIngestionService(ps, p.id)
    r1 = ing.ingest_local_file(src1, title="Doc one", normative_classification=NormativeClassification.UNKNOWN)
    assert r1.document
    d1 = r1.document.id
    src2 = tmp_path / "same_copy.txt"
    src2.write_bytes(src1.read_bytes())
    r2 = ing.ingest_local_file(
        src2,
        title="Doc two",
        normative_classification=NormativeClassification.UNKNOWN,
        duplicate_policy="reingest",
    )
    assert r2.document
    d2 = r2.document.id
    assert d1 != d2
    gs = ps.governance_store()
    a2 = gs.try_load_document_corpus_assessment(p.id, d2)
    assert a2 is not None
    dups = [c for c in a2.candidates if c.relation == CorpusAssessmentCandidateRelation.DUPLICATE_CANDIDATE]
    assert len(dups) == 1
    assert dups[0].other_document_id == d1


def test_overlap_contradiction_supporting_supersession_narrow_cases(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "en", "SI", "AISC")
    ing = DocumentIngestionService(ps, p.id)
    shared = (
        "Eurocode steel design structural analysis beams columns frames "
        "provisions resistance factors partial factors gamma combination rules "
        "alpha beta gamma delta epsilon zeta eta theta kappa lambda mu nu xi pi rho sigma tau phi chi psi omega"
    )
    a_txt = tmp_path / "a.txt"
    b_txt = tmp_path / "b.txt"
    a_txt.write_text(shared + " unique_a_tail_aaaa.", encoding="utf-8")
    b_txt.write_text(shared + " unique_b_tail_bbbb.", encoding="utf-8")
    r1 = ing.ingest_local_file(
        a_txt,
        title="Eurocode Steel Structures Manual",
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="EN1993",
        publication_year=2010,
        edition="1",
        version_label="v1",
    )
    r2 = ing.ingest_local_file(
        b_txt,
        title="Eurocode Steel Structures Manual",
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="EN1993",
        publication_year=2016,
        edition="2",
        version_label="v2",
    )
    assert r1.document and r2.document
    gs = ps.governance_store()
    subj = r2.document.id
    other = r1.document.id
    a_sub = gs.try_load_document_corpus_assessment(p.id, subj)
    assert a_sub is not None
    rels = _relations(a_sub)
    assert (other, CorpusAssessmentCandidateRelation.SUPERSESSION_CANDIDATE) in rels
    assert (other, CorpusAssessmentCandidateRelation.CONTRADICTION_CANDIDATE) not in rels
    assert (other, CorpusAssessmentCandidateRelation.OVERLAP_CANDIDATE) not in rels

    sup_txt = tmp_path / "sup.txt"
    sup_txt.write_text("Supporting commentary for EN1993 application notes.", encoding="utf-8")
    r3 = ing.ingest_local_file(
        sup_txt,
        title="EN1993 supporting commentary",
        normative_classification=NormativeClassification.SUPPORTING_DOCUMENT,
        standard_family="EN1993",
    )
    assert r3.document
    a_sup = gs.try_load_document_corpus_assessment(p.id, r3.document.id)
    assert a_sup is not None
    primaries = {r1.document.id, r2.document.id}
    sup_cands = [
        c
        for c in a_sup.candidates
        if c.relation == CorpusAssessmentCandidateRelation.SUPPORTING_CANDIDATE
        and c.other_document_id in primaries
    ]
    assert sup_cands, "expected supporting_candidate toward at least one primary"

    c_txt = tmp_path / "c.txt"
    c_txt.write_text(shared + " contradiction_pair_no_meta.", encoding="utf-8")
    r4 = ing.ingest_local_file(
        c_txt,
        title="Quasar Manual Alpha ZZ_ONLY_A",
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="EN1993",
        publication_year=2012,
        edition="1",
        version_label="same-line",
    )
    d_txt = tmp_path / "d.txt"
    d_txt.write_text(shared + " contradiction_pair_no_meta_alt.", encoding="utf-8")
    r5 = ing.ingest_local_file(
        d_txt,
        title="Nebula Manual Beta ZZ_ONLY_B",
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="EN1993",
        publication_year=2012,
        edition="1",
        version_label="same-line",
    )
    assert r4.document and r5.document
    a5 = gs.try_load_document_corpus_assessment(p.id, r5.document.id)
    assert a5 is not None
    rels5 = _relations(a5)
    assert (r4.document.id, CorpusAssessmentCandidateRelation.CONTRADICTION_CANDIDATE) in rels5
    assert (r4.document.id, CorpusAssessmentCandidateRelation.OVERLAP_CANDIDATE) in rels5


def test_assessment_persistence_round_trip_and_deterministic_json(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "en", "SI", "AISC")
    src = tmp_path / "x.txt"
    src.write_text("Hello world.\n\nSecond paragraph.", encoding="utf-8")
    ing = DocumentIngestionService(ps, p.id)
    res = ing.ingest_local_file(src, title="T", normative_classification=NormativeClassification.UNKNOWN)
    assert res.document
    gs = ps.governance_store()
    a1 = gs.try_load_document_corpus_assessment(p.id, res.document.id)
    a2 = gs.try_load_document_corpus_assessment(p.id, res.document.id)
    assert a1 and a2
    j1 = json.dumps(document_corpus_assessment_to_dict(a1), sort_keys=True)
    j2 = json.dumps(document_corpus_assessment_to_dict(a2), sort_keys=True)
    assert j1 == j2
    validate_document_corpus_assessment_payload(document_corpus_assessment_to_dict(a1))


def test_validation_failure_bad_assessment_file(tmp_path: Path) -> None:
    repo = JsonRepository(tmp_path / "ws")
    pid = "proj_aaaaaaaaaaaa"
    doc_id = "doc_bbbbbbbbbbbb"
    bad = {
        "schema_version": "g2.1",
        "project_id": pid,
        "subject_document_id": doc_id,
        "assessed_at": "t",
        "assessment_framing": "x",
        "notes": "",
        "candidates": [
            {
                "other_document_id": "doc_cccccccccccc",
                "relation": "not_a_relation",
                "confidence": "high",
                "signals": [],
                "details": {},
            }
        ],
    }
    rel = str(Path(pid, "governance", "assessments", f"{doc_id}.json"))
    (repo.base_path / pid / "governance" / "assessments").mkdir(parents=True, exist_ok=True)
    repo.write(rel, bad)
    gs = GovernanceStore(repo)
    with pytest.raises(GovernanceStoreError):
        gs.try_load_document_corpus_assessment(pid, doc_id)


def test_backward_compat_no_assessment_files(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "en", "SI", "AISC")
    gs = ps.governance_store()
    assert gs.try_load_document_corpus_assessment(p.id, "doc_nonexistent") is None


def test_build_assessment_empty_corpus_first_document(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "en", "SI", "AISC")
    src = tmp_path / "only.txt"
    src.write_text("Solo document body text.", encoding="utf-8")
    ing = DocumentIngestionService(ps, p.id)
    res = ing.ingest_local_file(src, title="Only", normative_classification=NormativeClassification.UNKNOWN)
    assert res.document
    gs = ps.governance_store()
    a = build_document_corpus_assessment(
        gs,
        project_id=p.id,
        subject_document_id=res.document.id,
        ingestion=ing,
    )
    assert a.candidates == ()


def test_retrieval_unchanged_after_g2_ingest(tmp_path: Path) -> None:
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
    assert (tmp_path / "ws" / p.id / "governance" / "assessments" / f"{doc_id}.json").is_file()
    ing.approve_document(doc_id)
    ing.activate_for_normative_corpus(doc_id)
    r = DocumentRetrievalService(ps, p.id)
    out = r.search("flexure resistance", citation_authority="normative_active_primary")
    assert out.status == "ok"
    assert out.hits
    assert out.hits[0].document_id == doc_id
