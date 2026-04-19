from __future__ import annotations

import json
from pathlib import Path

import pytest

from structural_tree_app.domain.enums import NormativeClassification
from structural_tree_app.domain.governance_codec import document_governance_index_to_dict
from structural_tree_app.domain.governance_enums import GovernancePipelineStage
from structural_tree_app.domain.governance_models import DocumentClassificationSnapshot
from structural_tree_app.services.document_service import DocumentIngestionService
from structural_tree_app.services.governance_document_pipeline import (
    classification_complete_for_g1,
    promote_document_to_classified,
)
from structural_tree_app.services.governance_store import GovernanceStore, GovernanceStoreError
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.services.retrieval_service import DocumentRetrievalService
from structural_tree_app.storage.json_repository import JsonRepository
from structural_tree_app.validation.json_schema import validate_document_governance_index_payload


def test_ingest_creates_governance_record_and_events(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "en", "SI", "AISC")
    src = tmp_path / "a.txt"
    src.write_text("One paragraph.\n\nTwo.", encoding="utf-8")
    ing = DocumentIngestionService(ps, p.id)
    res = ing.ingest_local_file(
        src,
        title="T",
        normative_classification=NormativeClassification.UNKNOWN,
    )
    assert res.status == "ingested"
    assert res.document
    gs = ps.governance_store()
    idx = gs.try_load_document_governance_index(p.id)
    assert idx is not None
    rec = idx.by_document_id[res.document.id]
    assert rec.pipeline_stage == GovernancePipelineStage.ANALYZED
    assert rec.analysis is not None
    assert rec.analysis.fragment_count == res.fragment_count
    assert rec.classification is not None
    assert rec.classification.classification_incomplete is True
    log = gs.try_load_governance_event_log(p.id)
    assert log is not None
    types = [e.event_type.value for e in log.events]
    assert types.count("pipeline_stage_changed") >= 2


def test_ingest_primary_standard_with_family_is_classified(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "en", "SI", "AISC")
    src = tmp_path / "b.txt"
    src.write_text("Normative text about beams and flexure.", encoding="utf-8")
    ing = DocumentIngestionService(ps, p.id)
    res = ing.ingest_local_file(
        src,
        title="Manual",
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="AISC",
    )
    assert res.status == "ingested"
    gs = ps.governance_store()
    idx = gs.try_load_document_governance_index(p.id)
    assert idx is not None
    rec = idx.by_document_id[res.document.id]
    assert rec.pipeline_stage == GovernancePipelineStage.CLASSIFIED
    assert rec.classification is not None
    assert rec.classification.classification_incomplete is False
    assert rec.classification.normative_classification == "primary_standard"


def test_promote_to_classified_explicit(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "en", "SI", "AISC")
    src = tmp_path / "c.txt"
    src.write_text("Body.", encoding="utf-8")
    ing = DocumentIngestionService(ps, p.id)
    res = ing.ingest_local_file(src, title="X", normative_classification=NormativeClassification.UNKNOWN)
    assert res.document
    doc_id = res.document.id
    gs = ps.governance_store()
    cl = DocumentClassificationSnapshot(
        normative_classification="supporting_document",
        authority_level="complementary",
        standard_family="EC3",
        discipline="steel",
        topic_scope_tags=("beams",),
        classification_incomplete=False,
    )
    promote_document_to_classified(gs, p.id, doc_id, cl, rationale="test promote")
    idx = gs.try_load_document_governance_index(p.id)
    assert idx is not None
    assert idx.by_document_id[doc_id].pipeline_stage == GovernancePipelineStage.CLASSIFIED
    assert idx.by_document_id[doc_id].classification == cl


def test_classification_persistence_round_trip_deterministic(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "en", "SI", "AISC")
    src = tmp_path / "d.txt"
    src.write_text("Hello world.", encoding="utf-8")
    ing = DocumentIngestionService(ps, p.id)
    res = ing.ingest_local_file(
        src,
        topics=["z", "a"],
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="X",
    )
    assert res.document
    gs = ps.governance_store()
    idx1 = gs.try_load_document_governance_index(p.id)
    idx2 = gs.try_load_document_governance_index(p.id)
    assert idx1 and idx2
    assert json.dumps(document_governance_index_to_dict(idx1), sort_keys=True) == json.dumps(
        document_governance_index_to_dict(idx2), sort_keys=True
    )
    tags = idx1.by_document_id[res.document.id].classification
    assert tags is not None
    assert list(tags.topic_scope_tags) == ["a", "z"]


def test_validation_failure_bad_record_in_index(tmp_path: Path) -> None:
    repo = JsonRepository(tmp_path / "ws")
    pid = "proj_aaaaaaaaaaaa"
    bad = {
        "schema_version": "g1.1",
        "project_id": pid,
        "updated_at": "t",
        "by_document_id": {
            "doc_bbbbbbbbbbbb": {
                "document_id": "doc_bbbbbbbbbbbb",
                "pipeline_stage": "not_a_stage",
                "disposition": "pending_review",
                "updated_at": "t",
                "notes": "",
            }
        },
    }
    rel = str(Path(pid, "governance", "document_governance_index.json"))
    repo.base_path.mkdir(parents=True, exist_ok=True)
    (repo.base_path / pid / "governance").mkdir(parents=True, exist_ok=True)
    repo.write(rel, bad)
    gs = GovernanceStore(repo)
    with pytest.raises(GovernanceStoreError):
        gs.try_load_document_governance_index(pid)


def test_backward_compat_project_without_governance_before_ingest(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "en", "SI", "AISC")
    assert not (tmp_path / "ws" / p.id / "governance" / "active_knowledge_projection.json").is_file()
    src = tmp_path / "e.txt"
    src.write_text("Content here.", encoding="utf-8")
    DocumentIngestionService(ps, p.id).ingest_local_file(src, title="Old style")
    assert (tmp_path / "ws" / p.id / "governance" / "active_knowledge_projection.json").is_file()


def test_retrieval_behavior_unchanged_from_g1_ingest(tmp_path: Path) -> None:
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
    r = DocumentRetrievalService(ps, p.id)
    out = r.search("flexure resistance", citation_authority="normative_active_primary")
    assert out.status == "ok"
    assert out.hits
    assert out.hits[0].document_id == doc_id


def test_apply_governance_standalone_validate_payload(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "en", "SI", "AISC")
    src = tmp_path / "f.txt"
    src.write_text("x", encoding="utf-8")
    ing = DocumentIngestionService(ps, p.id)
    res = ing.ingest_local_file(src, title="Y", normative_classification=NormativeClassification.UNKNOWN)
    assert res.document
    raw = json.loads(
        (tmp_path / "ws" / p.id / "governance" / "document_governance_index.json").read_text(encoding="utf-8")
    )
    validate_document_governance_index_payload(raw)


def test_classification_complete_helper() -> None:
    from structural_tree_app.domain.models import Document
    from structural_tree_app.domain.enums import AuthorityLevel, DocumentApprovalStatus

    d = Document(
        title="t",
        author="a",
        edition="e",
        version_label="1",
        publication_year=None,
        document_type="c",
        authority_level=AuthorityLevel.PRIMARY,
        topics=[],
        language="en",
        file_path="/x",
        content_hash="0" * 64,
        approval_status=DocumentApprovalStatus.PENDING,
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family=None,
    )
    assert classification_complete_for_g1(d) is False
