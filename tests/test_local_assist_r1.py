"""R1 — local assist orchestrator contract (retrieval authority, no LLM)."""

from __future__ import annotations

import json
from pathlib import Path

from structural_tree_app.domain.enums import NormativeClassification, SourceType
from structural_tree_app.domain.local_assist_contract import (
    LocalAssistQuery,
    local_assist_response_to_dict,
)
from structural_tree_app.domain.models import Assumption, Calculation
from structural_tree_app.services.document_service import DocumentIngestionService
from structural_tree_app.services.local_assist_orchestrator import LocalAssistOrchestrator, _MAX_QUERY_LEN
from structural_tree_app.services.simple_span_m5_service import METHOD_LABEL as M5_METHOD_LABEL
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.storage.tree_store import TreeStore


def _ingest_normative_doc(ps: ProjectService, project_id: str, tmp_path: Path) -> None:
    src = tmp_path / "norm.txt"
    src.write_text(
        "Steel beam flexure design limit state and resistance factor provisions for bending.",
        encoding="utf-8",
    )
    ing = DocumentIngestionService(ps, project_id)
    ir = ing.ingest_local_file(
        src,
        title="Steel ref",
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="AISC",
    )
    assert ir.document
    ing.approve_document(ir.document.id)
    ing.activate_for_normative_corpus(ir.document.id)


def test_r1_approved_corpus_only_path_returns_citations(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    _ingest_normative_doc(ps, p.id, tmp_path)

    orch = LocalAssistOrchestrator(ps)
    q = LocalAssistQuery(project_id=p.id, retrieval_query_text="flexure bending resistance")
    r = orch.run(q)

    assert r.answer_status == "evidence_passages_assembled"
    assert r.citations
    assert r.evidence_items
    assert len(r.evidence_items) == len(r.citations)
    assert r.refusal_reasons == ()
    assert all(c.authority_class == "authoritative_normative_active_primary" for c in r.citations)
    assert all(c.retrieval_citation_authority == "normative_active_primary" for c in r.citations)
    for c in r.citations:
        assert c.document_id
        assert c.fragment_id
        assert c.snippet
        assert c.content_hash
        assert c.fragment_content_hash


def test_r1_insufficient_evidence_refusal(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    _ingest_normative_doc(ps, p.id, tmp_path)

    orch = LocalAssistOrchestrator(ps)
    q = LocalAssistQuery(project_id=p.id, retrieval_query_text="xyznonmatchingtoken12345")
    r = orch.run(q)

    assert r.answer_status == "insufficient_evidence"
    assert not r.citations
    assert r.refusal_reasons
    assert r.refusal_reasons[0].code == "INSUFFICIENT_CORPUS_EVIDENCE"
    assert "No passages" in r.refusal_reasons[0].message or "insufficient" in r.answer_text.lower()


def test_r1_citation_payload_completeness_in_dict(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    _ingest_normative_doc(ps, p.id, tmp_path)

    r = LocalAssistOrchestrator(ps).run(
        LocalAssistQuery(project_id=p.id, retrieval_query_text="steel beam", retrieval_limit=3)
    )
    d = local_assist_response_to_dict(r)
    assert d["citations"]
    keys_required = {
        "authority_class",
        "chunk_index",
        "citation_id",
        "content_hash",
        "document_approval_status",
        "document_id",
        "document_title",
        "fragment_content_hash",
        "fragment_id",
        "ingestion_method",
        "normative_classification",
        "page_end",
        "page_start",
        "retrieval_citation_authority",
        "score",
        "snippet",
        "standard_family",
    }
    for row in d["citations"]:
        assert keys_required <= set(row.keys())


def test_r1_authority_class_separation_normative_vs_supporting(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    _ingest_normative_doc(ps, p.id, tmp_path)

    r_norm = LocalAssistOrchestrator(ps).run(
        LocalAssistQuery(project_id=p.id, retrieval_query_text="steel", citation_authority="normative_active_primary")
    )
    r_sup = LocalAssistOrchestrator(ps).run(
        LocalAssistQuery(project_id=p.id, retrieval_query_text="steel", citation_authority="approved_ingested")
    )
    assert r_norm.citations[0].authority_class == "authoritative_normative_active_primary"
    assert r_sup.citations[0].authority_class == "approved_supporting_corpus"


def test_r1_deterministic_hooks_preliminary_m5_distinct_from_citations(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    store = TreeStore.for_live_project(ps.repository, p.id)
    store.ensure_layout()
    calc = Calculation(
        project_id=p.id,
        node_id="node-test",
        objective="prelim",
        method_label=M5_METHOD_LABEL,
        formula_text="n/a",
        inputs={},
        substitutions={},
        result={"ok": True},
    )
    store.save_calculation(calc)

    r = LocalAssistOrchestrator(ps).run(
        LocalAssistQuery(
            project_id=p.id,
            retrieval_query_text="ignored",
            include_deterministic_hooks=True,
        )
    )
    # No corpus match -> insufficient evidence, but hooks still listed
    assert r.answer_status == "insufficient_evidence"
    assert r.deterministic_hooks
    h = r.deterministic_hooks[0]
    assert h.calculation_id == calc.id
    assert h.authority_boundary == "preliminary_deterministic_m5"
    assert "not a normative document citation" in h.disclosure.lower()


def test_r1_stable_serialization(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    _ingest_normative_doc(ps, p.id, tmp_path)

    orch = LocalAssistOrchestrator(ps)
    q = LocalAssistQuery(project_id=p.id, retrieval_query_text="steel beam")
    d1 = json.dumps(local_assist_response_to_dict(orch.run(q)), sort_keys=True)
    d2 = json.dumps(local_assist_response_to_dict(orch.run(q)), sort_keys=True)
    assert d1 == d2


def test_r1_project_context_missing_project(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    r = LocalAssistOrchestrator(ps).run(
        LocalAssistQuery(project_id="does-not-exist", retrieval_query_text="x")
    )
    assert r.answer_status == "error"
    assert r.refusal_reasons[0].code == "PROJECT_NOT_FOUND"


def test_r1_empty_query_unsupported(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    r = LocalAssistOrchestrator(ps).run(LocalAssistQuery(project_id=p.id, retrieval_query_text="   "))
    assert r.answer_status == "unsupported_query"
    assert r.refusal_reasons[0].code == "EMPTY_QUERY"


def test_r1_query_too_long(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    r = LocalAssistOrchestrator(ps).run(
        LocalAssistQuery(project_id=p.id, retrieval_query_text="x" * (_MAX_QUERY_LEN + 1))
    )
    assert r.answer_status == "unsupported_query"
    assert r.refusal_reasons[0].code == "QUERY_TOO_LONG"


def test_r1_assumptions_exposed_with_distinct_authority_note(tmp_path: Path) -> None:
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    ps.save_assumptions(
        p.id,
        [
            Assumption(
                project_id=p.id,
                node_id="n1",
                label="span",
                value="15",
                unit="m",
                source_type=SourceType.USER_CONFIRMED,
                rationale="test",
            )
        ],
    )
    r = LocalAssistOrchestrator(ps).run(
        LocalAssistQuery(project_id=p.id, retrieval_query_text="nomatchzzz", include_project_assumptions=True)
    )
    assert r.assumptions
    assert r.assumptions[0].label == "span"
    assert "project_assumption" in r.assumptions[0].authority_note


def test_r1_orchestrator_does_not_write_workspace_files(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ps = ProjectService(ws)
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    _ingest_normative_doc(ps, p.id, tmp_path)
    before = {f.relative_to(ws) for f in ws.rglob("*") if f.is_file()}

    LocalAssistOrchestrator(ps).run(LocalAssistQuery(project_id=p.id, retrieval_query_text="steel"))
    after = {f.relative_to(ws) for f in ws.rglob("*") if f.is_file()}
    assert before == after
