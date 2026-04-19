"""R2B — reasoning / formula-selection bridge: contracts, evidence linkage, determinism, orchestrator isolation."""

from __future__ import annotations

import json
from pathlib import Path

from structural_tree_app.domain.enums import NormativeClassification
from structural_tree_app.domain.local_assist_contract import LocalAssistQuery
from structural_tree_app.domain.reasoning_bridge_codec import reasoning_bridge_result_from_dict, reasoning_bridge_result_to_dict
from structural_tree_app.domain.reasoning_bridge_contract import ReasoningBridgeRequest
from structural_tree_app.services.derived_knowledge_service import DerivedKnowledgeService
from structural_tree_app.services.document_service import DocumentIngestionService
from structural_tree_app.services.local_assist_orchestrator import LocalAssistOrchestrator
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.services.reasoning_bridge_service import ReasoningBridgeService
from structural_tree_app.services.retrieval_service import DocumentRetrievalService
from structural_tree_app.domain.tree_codec import canonicalize_json
from structural_tree_app.validation.json_schema import validate_reasoning_bridge_result_payload


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


def test_r2b_vertical_slice_query_structured_output(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    _ingest_normative(
        ps,
        p.id,
        tmp_path,
        "Steel simple span beam flexure equation capacity check limit state phi.",
    )
    DerivedKnowledgeService(ps).regenerate(p.id)

    bridge = ReasoningBridgeService(ps)
    req = ReasoningBridgeRequest(project_id=p.id, query_text="simple span steel beam flexure capacity")
    out = bridge.analyze(req)
    assert out.analysis_status == "ok"
    assert out.interpretation is not None
    assert out.interpretation.problem_family_id == "simple_span_steel_vertical_slice"
    assert out.retrieval_status == "ok"
    assert any(a.anchor_kind == "retrieval_hit" for a in out.evidence_anchors)
    assert any(cf.source == "derived_registry" for cf in out.candidate_formulas)
    # Derived registry rows link to fragments
    for cf in out.candidate_formulas:
        if cf.source == "derived_registry":
            assert cf.supported_by_anchors
            assert all(a.document_id for a in cf.supported_by_anchors)
            assert all(a.fragment_id for a in cf.supported_by_anchors)
    d = reasoning_bridge_result_to_dict(out)
    validate_reasoning_bridge_result_payload(d)
    round_trip = reasoning_bridge_result_from_dict(d)
    assert round_trip.project_id == out.project_id
    assert len(round_trip.candidate_formulas) == len(out.candidate_formulas)


def test_r2b_unsupported_scope_explicit_gaps(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    _ingest_normative(ps, p.id, tmp_path, "Some steel text.", name="x.txt")
    out = ReasoningBridgeService(ps).analyze(
        ReasoningBridgeRequest(project_id=p.id, query_text="quantum banana cosmology")
    )
    assert out.analysis_status == "ok"
    assert out.interpretation is not None
    assert out.interpretation.problem_family_id == "unknown"
    cats = {g.category for g in out.unsupported_gaps}
    assert "outside_vertical_slice" in cats
    assert "no_derived_knowledge_bundle" in cats


def test_r2b_m5_recognition_vs_executable(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    _ingest_normative(
        ps,
        p.id,
        tmp_path,
        "Equation for flexure capacity demand check phi.",
        name="y.txt",
    )
    DerivedKnowledgeService(ps).regenerate(p.id)
    out = ReasoningBridgeService(ps).analyze(
        ReasoningBridgeRequest(project_id=p.id, query_text="steel span beam flexure equation")
    )
    derived = [f for f in out.candidate_formulas if f.source == "derived_registry"]
    assert derived
    statuses = {f.execution_status for f in derived}
    # Without tree calcs, M5 hook capability stays recognition if registry says m5_hook
    assert statuses <= {"deterministic_m5_available", "recognition_only"}


def test_r2b_deterministic_steps_not_normative_citations(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    _ingest_normative(ps, p.id, tmp_path, "text", name="z.txt")
    out = ReasoningBridgeService(ps).analyze(
        ReasoningBridgeRequest(project_id=p.id, query_text="beam", include_deterministic_context=True)
    )
    for s in out.supported_execution_steps:
        assert "preliminary" in s.authority_boundary or "deterministic" in s.authority_boundary
        assert "not" in s.notes.lower() or "separate" in s.notes.lower() or "engine" in s.notes.lower()


def test_r2b_deterministic_serialization_ordering(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    _ingest_normative(ps, p.id, tmp_path, "flexure steel span beam formula.", name="d.txt")
    DerivedKnowledgeService(ps).regenerate(p.id)
    out = ReasoningBridgeService(ps).analyze(
        ReasoningBridgeRequest(project_id=p.id, query_text="steel simple span flexure")
    )
    d1 = canonicalize_json(reasoning_bridge_result_to_dict(out))
    d2 = canonicalize_json(reasoning_bridge_result_to_dict(out))
    assert json.dumps(d1, sort_keys=True) == json.dumps(d2, sort_keys=True)


def test_r2b_orchestrator_and_retrieval_unchanged(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    _ingest_normative(ps, p.id, tmp_path, "Unique token omega steel span flexure.", name="o.txt")
    q = LocalAssistQuery(project_id=p.id, retrieval_query_text="omega steel span")
    r_before = DocumentRetrievalService(ps, p.id).search("omega", citation_authority="normative_active_primary")
    o_before = LocalAssistOrchestrator(ps).run(q)

    ReasoningBridgeService(ps).analyze(
        ReasoningBridgeRequest(project_id=p.id, query_text="omega steel span flexure")
    )
    DerivedKnowledgeService(ps).regenerate(p.id)
    ReasoningBridgeService(ps).analyze(
        ReasoningBridgeRequest(project_id=p.id, query_text="omega steel span flexure beam")
    )

    r_after = DocumentRetrievalService(ps, p.id).search("omega", citation_authority="normative_active_primary")
    o_after = LocalAssistOrchestrator(ps).run(q)
    assert r_before.status == r_after.status
    assert [h.document_id for h in r_before.hits] == [h.document_id for h in r_after.hits]
    assert o_before.answer_status == o_after.answer_status
    assert o_before.citations == o_after.citations
