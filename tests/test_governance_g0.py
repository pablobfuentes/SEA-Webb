from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema.exceptions import ValidationError

from structural_tree_app.domain.governance_codec import (
    active_knowledge_projection_from_dict,
    active_knowledge_projection_to_dict,
    document_governance_index_from_dict,
    document_governance_index_to_dict,
    governance_event_log_from_dict,
    governance_event_log_to_dict,
    governance_event_to_dict,
)
from structural_tree_app.domain.governance_enums import (
    DocumentGovernanceDisposition,
    GovernanceEventType,
    GovernancePipelineStage,
    GovernanceRetrievalBinding,
)
from structural_tree_app.domain.governance_models import (
    ActiveKnowledgeProjection,
    DocumentGovernanceIndex,
    DocumentGovernanceRecord,
    GovernanceEvent,
    GovernanceEventLog,
)
from structural_tree_app.storage.json_repository import JsonRepository
from structural_tree_app.services.governance_store import GovernanceStore, GovernanceStoreError
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.validation.json_schema import (
    validate_active_knowledge_projection_payload,
    validate_governance_event_log_payload,
)


def test_governance_enum_json_round_trip() -> None:
    assert GovernancePipelineStage("ingested") == GovernancePipelineStage.INGESTED
    assert DocumentGovernanceDisposition("active") == DocumentGovernanceDisposition.ACTIVE
    assert GovernanceRetrievalBinding("legacy_allowed_documents") == GovernanceRetrievalBinding.LEGACY_ALLOWED_DOCUMENTS
    dumped = json.dumps(
        {
            "stage": GovernancePipelineStage.CLASSIFIED.value,
            "disp": DocumentGovernanceDisposition.PENDING_REVIEW.value,
            "bind": GovernanceRetrievalBinding.EXPLICIT_PROJECTION.value,
        }
    )
    raw = json.loads(dumped)
    assert GovernancePipelineStage(raw["stage"]) == GovernancePipelineStage.CLASSIFIED


def test_active_projection_codec_round_trip() -> None:
    p = ActiveKnowledgeProjection(
        project_id="proj_aaaaaaaaaaaa",
        schema_version="g0.1",
        updated_at="2026-01-01T00:00:00+00:00",
        retrieval_binding=GovernanceRetrievalBinding.LEGACY_ALLOWED_DOCUMENTS,
        authoritative_document_ids=("doc_bbbbbbbbbbbb",),
        supporting_document_ids=(),
        excluded_from_authoritative_document_ids=(),
        notes="",
    )
    d = active_knowledge_projection_to_dict(p)
    validate_active_knowledge_projection_payload(d)
    again = active_knowledge_projection_from_dict(d)
    assert again == p


def test_deterministic_projection_serialization() -> None:
    p = ActiveKnowledgeProjection(
        project_id="proj_aaaaaaaaaaaa",
        schema_version="g0.1",
        updated_at="2026-01-01T00:00:00+00:00",
        retrieval_binding=GovernanceRetrievalBinding.EXPLICIT_PROJECTION,
        authoritative_document_ids=("doc_111111111111", "doc_222222222222"),
        supporting_document_ids=("doc_333333333333",),
        excluded_from_authoritative_document_ids=("doc_444444444444",),
        notes="n",
    )
    a = json.dumps(active_knowledge_projection_to_dict(p), sort_keys=True)
    b = json.dumps(active_knowledge_projection_to_dict(p), sort_keys=True)
    assert a == b


def test_governance_event_log_persist_round_trip(tmp_path: Path) -> None:
    gs = GovernanceStore(JsonRepository(tmp_path / "ws"))
    pid = "proj_aaaaaaaaaaaa"
    ev = GovernanceEvent(
        project_id=pid,
        event_type=GovernanceEventType.PROJECTION_UPDATED,
        rationale="test",
        occurred_at="2026-01-02T00:00:00+00:00",
        id="gov_aaaaaaaaaaaa",
        actor="tester",
        affected_document_ids=("doc_bbbbbbbbbbbb",),
        prior_retrieval_binding="legacy_allowed_documents",
        new_retrieval_binding="explicit_projection",
        prior_projection_schema_version="g0.1",
        payload={"k": "v"},
    )
    log = GovernanceEventLog(schema_version="g0.1", project_id=pid, events=(ev,))
    gs.save_governance_event_log(log)
    loaded = gs.try_load_governance_event_log(pid)
    assert loaded is not None
    assert len(loaded.events) == 1
    assert loaded.events[0].event_type == GovernanceEventType.PROJECTION_UPDATED
    assert loaded.events[0].payload == {"k": "v"}
    raw_path = tmp_path / "ws" / pid / "governance" / GovernanceStore.GOVERNANCE_EVENT_LOG_JSON
    raw = json.loads(raw_path.read_text(encoding="utf-8"))
    validate_governance_event_log_payload(raw)


def test_document_governance_index_round_trip(tmp_path: Path) -> None:
    gs = GovernanceStore(JsonRepository(tmp_path / "ws"))
    pid = "proj_aaaaaaaaaaaa"
    rec = DocumentGovernanceRecord(
        document_id="doc_bbbbbbbbbbbb",
        pipeline_stage=GovernancePipelineStage.INGESTED,
        disposition=DocumentGovernanceDisposition.PENDING_REVIEW,
        updated_at="2026-01-01T00:00:00+00:00",
        notes="",
    )
    idx = DocumentGovernanceIndex(
        project_id=pid,
        schema_version="g0.1",
        updated_at="2026-01-01T00:00:00+00:00",
        by_document_id={rec.document_id: rec},
    )
    gs.save_document_governance_index(idx)
    loaded = gs.try_load_document_governance_index(pid)
    assert loaded is not None
    d1 = document_governance_index_to_dict(idx)
    d2 = document_governance_index_to_dict(loaded)
    assert json.dumps(d1, sort_keys=True) == json.dumps(d2, sort_keys=True)


def test_governance_event_deterministic_dict() -> None:
    ev = GovernanceEvent(
        project_id="proj_aaaaaaaaaaaa",
        event_type=GovernanceEventType.BASELINE_INITIALIZED,
        rationale="r",
        occurred_at="2026-01-01T00:00:00+00:00",
        id="gov_aaaaaaaaaaaa",
        actor="system",
        affected_document_ids=(),
        prior_retrieval_binding=None,
        new_retrieval_binding="legacy_allowed_documents",
        prior_projection_schema_version=None,
        payload={"z": 1, "a": 2},
    )
    d1 = json.dumps(governance_event_to_dict(ev), sort_keys=True)
    d2 = json.dumps(governance_event_to_dict(ev), sort_keys=True)
    assert d1 == d2
    assert governance_event_to_dict(ev)["payload"] == {"a": 2, "z": 1}


def test_backward_compat_project_without_governance(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("N", "D", "en", "SI", "AISC")
    gs = ps.governance_store()
    assert gs.try_load_active_knowledge_projection(p.id) is None
    assert gs.try_load_document_governance_index(p.id) is None
    assert gs.try_load_governance_event_log(p.id) is None
    loaded = ps.load_project(p.id)
    assert loaded.id == p.id


def test_validation_failure_on_bad_projection_file(tmp_path: Path) -> None:
    repo = JsonRepository(tmp_path / "ws")
    pid = "proj_aaaaaaaaaaaa"
    rel = str(Path(pid, "governance", "active_knowledge_projection.json"))
    repo.write(
        rel,
        {
            "schema_version": "g0.1",
            "project_id": pid,
            "updated_at": "x",
            "retrieval_binding": "not_a_valid_binding",
            "authoritative_document_ids": [],
            "supporting_document_ids": [],
            "excluded_from_authoritative_document_ids": [],
            "notes": "",
        },
    )
    gs = GovernanceStore(repo)
    with pytest.raises(GovernanceStoreError, match="Invalid active knowledge projection"):
        gs.try_load_active_knowledge_projection(pid)


def test_schema_validate_rejects_bad_event_log() -> None:
    with pytest.raises(ValidationError):
        validate_governance_event_log_payload({"project_id": "proj_aaaaaaaaaaaa", "events": []})


def test_initialize_baseline_idempotent(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("N", "D", "en", "SI", "AISC")
    gs = ps.governance_store()
    assert gs.initialize_governance_baseline(p.id) is True
    assert gs.try_load_active_knowledge_projection(p.id) is not None
    assert gs.initialize_governance_baseline(p.id) is False


def test_partial_governance_state_rejected(tmp_path: Path) -> None:
    repo = JsonRepository(tmp_path / "ws")
    pid = "proj_aaaaaaaaaaaa"
    Path(repo.base_path / pid / "governance").mkdir(parents=True)
    (repo.base_path / pid / "governance" / "document_governance_index.json").write_text(
        '{"schema_version":"g0.1","project_id":"proj_aaaaaaaaaaaa","updated_at":"t","by_document_id":{}}',
        encoding="utf-8",
    )
    gs = GovernanceStore(repo)
    with pytest.raises(GovernanceStoreError, match="Partial governance"):
        gs.initialize_governance_baseline(pid)


def test_create_project_ensures_governance_directory(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("N", "D", "en", "SI", "AISC")
    assert (tmp_path / "ws" / p.id / "governance").is_dir()
