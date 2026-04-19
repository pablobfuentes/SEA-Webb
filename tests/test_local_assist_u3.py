"""U3 — optional local model synthesis boundary; retrieval and contract boundaries preserved."""

from __future__ import annotations

from pathlib import Path

import pytest

from structural_tree_app.domain.enums import NormativeClassification, SourceType
from structural_tree_app.domain.governance_enums import GovernanceRetrievalBinding
from structural_tree_app.domain.governance_models import ActiveKnowledgeProjection, DocumentGovernanceIndex, DocumentGovernanceRecord
from structural_tree_app.domain.governance_enums import DocumentGovernanceDisposition
from structural_tree_app.domain.local_assist_contract import LocalAssistQuery
from structural_tree_app.domain.models import Assumption, Calculation, utc_now
from structural_tree_app.services.document_service import DocumentIngestionService
from structural_tree_app.services.local_assist_orchestrator import LocalAssistOrchestrator
from structural_tree_app.services.local_model_config import LocalModelRuntimeConfig
from structural_tree_app.services.local_model_synthesis import StubLocalModelSynthesizer, UnavailableLocalModelSynthesizer
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.services.simple_span_m5_service import METHOD_LABEL as M5_METHOD_LABEL
from structural_tree_app.storage.tree_store import TreeStore


def _ingest_normative(ps: ProjectService, project_id: str, tmp_path: Path, text: str = "Steel beam flexure design limit state.") -> None:
    src = tmp_path / "n.txt"
    src.write_text(text, encoding="utf-8")
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


def test_u3_model_disabled_matches_r1_answer_text(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STRUCTURAL_LOCAL_MODEL_ENABLED", raising=False)
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    _ingest_normative(ps, p.id, tmp_path)

    orch = LocalAssistOrchestrator(ps)
    r = orch.run(
        LocalAssistQuery(
            project_id=p.id,
            retrieval_query_text="steel flexure",
            request_local_model_synthesis=True,
        )
    )
    assert r.answer_status == "evidence_passages_assembled"
    assert r.response_authority_summary == "retrieval_passages_only_not_synthesized"
    assert "[R1 bounded assembly]" in r.answer_text
    assert "Passages below come only from approved-corpus retrieval" in r.answer_text


def test_u3_model_enabled_stub_preserves_citations_and_evidence_slots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRUCTURAL_LOCAL_MODEL_ENABLED", "1")
    monkeypatch.setenv("STRUCTURAL_LOCAL_MODEL_PROVIDER", "stub")
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    _ingest_normative(ps, p.id, tmp_path)

    orch = LocalAssistOrchestrator(ps)
    r = orch.run(
        LocalAssistQuery(project_id=p.id, retrieval_query_text="steel flexure", request_local_model_synthesis=True)
    )
    assert r.answer_status == "evidence_passages_assembled"
    assert r.response_authority_summary == "local_model_synthesis_bounded"
    assert "[U3 stub" in r.answer_text
    assert r.citations
    assert len(r.evidence_items) == len(r.citations)
    assert all("answer_text includes bounded local model restatement" in w for w in r.warnings)
    assert r.refusal_reasons == ()


def test_u3_insufficient_evidence_no_synthesis(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRUCTURAL_LOCAL_MODEL_ENABLED", "1")
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    _ingest_normative(ps, p.id, tmp_path)

    orch = LocalAssistOrchestrator(ps)
    r = orch.run(
        LocalAssistQuery(
            project_id=p.id,
            retrieval_query_text="zzznonexistenttoken999",
            request_local_model_synthesis=True,
        )
    )
    assert r.answer_status == "insufficient_evidence"
    assert "[U3 stub" not in r.answer_text
    assert not r.citations
    assert r.refusal_reasons


def test_u3_governance_conflict_no_synthesis(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRUCTURAL_LOCAL_MODEL_ENABLED", "1")
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    src = tmp_path / "c.txt"
    src.write_text("Conflict body u3.", encoding="utf-8")
    ing = DocumentIngestionService(ps, p.id)
    ir = ing.ingest_local_file(
        src,
        title="C",
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="AISC",
    )
    did = ir.document.id
    ing.approve_document(did)
    ing.activate_for_normative_corpus(did)
    gs = ps.governance_store()
    idx = gs.try_load_document_governance_index(p.id)
    assert idx
    rec = idx.by_document_id[did]
    bumped = DocumentGovernanceRecord(
        document_id=did,
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
            by_document_id={**idx.by_document_id, did: bumped},
        )
    )
    cur = gs.try_load_active_knowledge_projection(p.id)
    assert cur
    gs.save_active_knowledge_projection(
        ActiveKnowledgeProjection(
            project_id=p.id,
            schema_version=cur.schema_version,
            updated_at=utc_now(),
            retrieval_binding=GovernanceRetrievalBinding.EXPLICIT_PROJECTION,
            authoritative_document_ids=(did,),
            supporting_document_ids=cur.supporting_document_ids,
            excluded_from_authoritative_document_ids=cur.excluded_from_authoritative_document_ids,
            notes=cur.notes,
        )
    )

    orch = LocalAssistOrchestrator(ps)
    r = orch.run(
        LocalAssistQuery(project_id=p.id, retrieval_query_text="Conflict", request_local_model_synthesis=True)
    )
    assert r.answer_status == "insufficient_evidence"
    assert "[U3 stub" not in r.answer_text
    assert r.refusal_reasons
    assert r.refusal_reasons[0].code == "GOVERNANCE_CONFLICT_BLOCKS_NORMATIVE"


def test_u3_authority_classes_preserved_normative_vs_supporting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRUCTURAL_LOCAL_MODEL_ENABLED", "1")
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    _ingest_normative(ps, p.id, tmp_path)

    orch = LocalAssistOrchestrator(ps)
    rn = orch.run(
        LocalAssistQuery(
            project_id=p.id,
            retrieval_query_text="steel",
            citation_authority="normative_active_primary",
            request_local_model_synthesis=True,
        )
    )
    rs = orch.run(
        LocalAssistQuery(
            project_id=p.id,
            retrieval_query_text="steel",
            citation_authority="approved_ingested",
            request_local_model_synthesis=True,
        )
    )
    assert all(c.authority_class == "authoritative_normative_active_primary" for c in rn.citations)
    assert all(c.authority_class == "approved_supporting_corpus" for c in rs.citations)


def test_u3_deterministic_hooks_separate_from_citations(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRUCTURAL_LOCAL_MODEL_ENABLED", "1")
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    _ingest_normative(ps, p.id, tmp_path)
    store = TreeStore.for_live_project(ps.repository, p.id)
    store.ensure_layout()
    calc = Calculation(
        project_id=p.id,
        node_id="n1",
        objective="x",
        method_label=M5_METHOD_LABEL,
        formula_text="n/a",
        inputs={},
        substitutions={},
        result={},
    )
    store.save_calculation(calc)

    orch = LocalAssistOrchestrator(ps)
    r = orch.run(
        LocalAssistQuery(
            project_id=p.id,
            retrieval_query_text="steel flexure",
            include_deterministic_hooks=True,
            request_local_model_synthesis=True,
        )
    )
    assert r.deterministic_hooks
    assert r.citations
    assert r.deterministic_hooks[0].calculation_id == calc.id
    assert r.deterministic_hooks[0].authority_boundary == "preliminary_deterministic_m5"
    assert all(c.document_id and c.fragment_id for c in r.citations)
    assert any("not generated by the model" in w for w in r.warnings)


def test_u3_unavailable_provider_fallback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRUCTURAL_LOCAL_MODEL_ENABLED", "1")
    monkeypatch.setenv("STRUCTURAL_LOCAL_MODEL_PROVIDER", "unavailable")
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    _ingest_normative(ps, p.id, tmp_path)

    orch = LocalAssistOrchestrator(
        ps,
        runtime_config=LocalModelRuntimeConfig(enabled=True, provider="unavailable"),
        synthesis_adapter=UnavailableLocalModelSynthesizer(),
    )
    r = orch.run(
        LocalAssistQuery(project_id=p.id, retrieval_query_text="steel flexure", request_local_model_synthesis=True)
    )
    assert r.response_authority_summary == "retrieval_passages_only_not_synthesized"
    assert "[R1 bounded assembly]" in r.answer_text
    assert any("runtime produced no text" in w for w in r.warnings)


def test_u3_explicit_stub_injection_independent_of_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("STRUCTURAL_LOCAL_MODEL_ENABLED", raising=False)
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    _ingest_normative(ps, p.id, tmp_path)

    orch = LocalAssistOrchestrator(
        ps,
        runtime_config=LocalModelRuntimeConfig(enabled=True, provider="stub"),
        synthesis_adapter=StubLocalModelSynthesizer(),
    )
    r = orch.run(LocalAssistQuery(project_id=p.id, retrieval_query_text="steel", request_local_model_synthesis=True))
    assert r.response_authority_summary == "local_model_synthesis_bounded"


def test_u3_assumptions_not_invented_by_stub(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("STRUCTURAL_LOCAL_MODEL_ENABLED", "1")
    ps = ProjectService(tmp_path / "ws")
    p = ps.create_project("P", "D", "es", "SI", "AISC")
    _ingest_normative(ps, p.id, tmp_path)
    ps.save_assumptions(
        p.id,
        [
            Assumption(
                project_id=p.id,
                node_id="n1",
                label="Lspan",
                value="10",
                unit="m",
                source_type=SourceType.USER_CONFIRMED,
                rationale="",
            )
        ],
    )

    orch = LocalAssistOrchestrator(ps)
    r = orch.run(
        LocalAssistQuery(
            project_id=p.id,
            retrieval_query_text="steel",
            include_project_assumptions=True,
            request_local_model_synthesis=True,
        )
    )
    assert len(r.assumptions) == 1
    assert r.assumptions[0].label == "Lspan"
