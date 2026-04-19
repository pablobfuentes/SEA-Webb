"""Corpus readiness / approval bridge — evaluation, UI strings, evidence hints."""

from __future__ import annotations

import re

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from structural_tree_app.domain.enums import DocumentApprovalStatus, NormativeClassification
from structural_tree_app.domain.governance_enums import (
    DocumentGovernanceDisposition,
    GovernancePipelineStage,
    GovernanceRetrievalBinding,
)
from structural_tree_app.domain.governance_models import (
    ActiveKnowledgeProjection,
    DocumentGovernanceIndex,
    DocumentGovernanceRecord,
)
from structural_tree_app.domain.models import ActiveCodeContext, Project
from structural_tree_app.services.corpus_readiness import (
    BLOCKED_MISSING_APPROVAL,
    BLOCKED_MISSING_PRIMARY_CLASSIFICATION,
    BLOCKED_MISSING_STANDARD_FAMILY,
    BLOCKED_NOT_IN_AUTHORITATIVE_PROJECTION,
    BLOCKED_NOT_IN_LEGACY_ALLOWED,
    BLOCKED_STANDARD_FAMILY_MISMATCH,
    READY_FOR_NORMATIVE_RETRIEVAL,
    READY_FOR_SUPPORTING_ONLY,
    evaluate_document_readiness,
    readiness_hint_html_for_evidence,
)
from structural_tree_app.services.corpus_bootstrap_service import apply_manual_corpus_bootstrap
from structural_tree_app.services.local_assist_orchestrator import LocalAssistOrchestrator
from structural_tree_app.domain.local_assist_contract import LocalAssistQuery
from structural_tree_app.workbench.app import create_app


def _minimal_project(*, allowed: list[str] | None = None, primary_fam: str = "AISC") -> Project:
    return Project(
        name="t",
        description="",
        language="es",
        unit_system="SI",
        active_code_context=ActiveCodeContext(
            primary_standard_family=primary_fam,
            allowed_document_ids=list(allowed or []),
        ),
        ingested_document_ids=[],
    )


def _minimal_doc(
    doc_id: str,
    *,
    approval: DocumentApprovalStatus = DocumentApprovalStatus.PENDING,
    nc: NormativeClassification = NormativeClassification.UNKNOWN,
    fam: str | None = None,
):
    from structural_tree_app.domain.models import Document
    from structural_tree_app.domain.enums import AuthorityLevel

    return Document(
        title="t",
        author="",
        edition="",
        version_label="1",
        publication_year=None,
        document_type="corpus",
        authority_level=AuthorityLevel.PRIMARY,
        topics=[],
        language="es",
        file_path="x",
        content_hash="0" * 64,
        id=doc_id,
        approval_status=approval,
        normative_classification=nc,
        standard_family=fam,
    )


def test_readiness_blocked_missing_approval() -> None:
    p = _minimal_project(allowed=["d1"])
    doc = _minimal_doc("d1", approval=DocumentApprovalStatus.PENDING, nc=NormativeClassification.PRIMARY_STANDARD, fam="AISC")
    r = evaluate_document_readiness(
        document=doc,
        project=p,
        governance_record=None,
        projection=None,
        governance_index=None,
    )
    assert r.readiness_label == BLOCKED_MISSING_APPROVAL
    assert not r.normative_eligible
    assert not r.supporting_eligible


def test_readiness_normative_eligible_legacy() -> None:
    p = _minimal_project(allowed=["d1"])
    doc = _minimal_doc(
        "d1",
        approval=DocumentApprovalStatus.APPROVED,
        nc=NormativeClassification.PRIMARY_STANDARD,
        fam="AISC",
    )
    r = evaluate_document_readiness(
        document=doc,
        project=p,
        governance_record=None,
        projection=None,
        governance_index=None,
    )
    assert r.readiness_label == READY_FOR_NORMATIVE_RETRIEVAL
    assert r.normative_eligible
    assert r.supporting_eligible


def test_readiness_missing_primary_classification() -> None:
    p = _minimal_project(allowed=["d1"])
    doc = _minimal_doc(
        "d1",
        approval=DocumentApprovalStatus.APPROVED,
        nc=NormativeClassification.SUPPORTING_DOCUMENT,
        fam="AISC",
    )
    r = evaluate_document_readiness(
        document=doc,
        project=p,
        governance_record=None,
        projection=None,
        governance_index=None,
    )
    assert r.readiness_label == BLOCKED_MISSING_PRIMARY_CLASSIFICATION
    assert not r.normative_eligible
    assert r.supporting_eligible
    assert BLOCKED_MISSING_PRIMARY_CLASSIFICATION in r.block_codes


def test_readiness_family_mismatch() -> None:
    p = _minimal_project(allowed=["d1"], primary_fam="AISC")
    doc = _minimal_doc(
        "d1",
        approval=DocumentApprovalStatus.APPROVED,
        nc=NormativeClassification.PRIMARY_STANDARD,
        fam="Eurocode",
    )
    r = evaluate_document_readiness(
        document=doc,
        project=p,
        governance_record=None,
        projection=None,
        governance_index=None,
        match_project_primary_standard_family=True,
    )
    assert r.readiness_label == BLOCKED_STANDARD_FAMILY_MISMATCH
    assert BLOCKED_STANDARD_FAMILY_MISMATCH in r.block_codes


def test_readiness_not_in_legacy_allowed() -> None:
    p = _minimal_project(allowed=[])
    doc = _minimal_doc(
        "d1",
        approval=DocumentApprovalStatus.APPROVED,
        nc=NormativeClassification.PRIMARY_STANDARD,
        fam="AISC",
    )
    r = evaluate_document_readiness(
        document=doc,
        project=p,
        governance_record=None,
        projection=None,
        governance_index=None,
    )
    assert BLOCKED_NOT_IN_LEGACY_ALLOWED in r.block_codes
    assert r.readiness_label == BLOCKED_NOT_IN_LEGACY_ALLOWED


def test_readiness_explicit_projection_membership() -> None:
    pid = "proj_test"
    rec = DocumentGovernanceRecord(
        document_id="d1",
        pipeline_stage=GovernancePipelineStage.INGESTED,
        disposition=DocumentGovernanceDisposition.ACTIVE,
    )
    gidx = DocumentGovernanceIndex(
        project_id=pid,
        by_document_id={"d1": rec},
    )
    proj = ActiveKnowledgeProjection(
        project_id=pid,
        retrieval_binding=GovernanceRetrievalBinding.EXPLICIT_PROJECTION,
        authoritative_document_ids=("d1",),
    )
    p = _minimal_project(allowed=[])
    doc = _minimal_doc(
        "d1",
        approval=DocumentApprovalStatus.APPROVED,
        nc=NormativeClassification.PRIMARY_STANDARD,
        fam="AISC",
    )
    r = evaluate_document_readiness(
        document=doc,
        project=p,
        governance_record=rec,
        projection=proj,
        governance_index=gidx,
    )
    assert r.normative_eligible
    assert r.readiness_label == READY_FOR_NORMATIVE_RETRIEVAL
    assert r.in_effective_authoritative_projection


def test_readiness_explicit_not_in_projection() -> None:
    rec_d1 = DocumentGovernanceRecord(
        document_id="d1",
        pipeline_stage=GovernancePipelineStage.INGESTED,
        disposition=DocumentGovernanceDisposition.ACTIVE,
    )
    rec_other = DocumentGovernanceRecord(
        document_id="other",
        pipeline_stage=GovernancePipelineStage.INGESTED,
        disposition=DocumentGovernanceDisposition.ACTIVE,
    )
    gidx = DocumentGovernanceIndex(
        project_id="p",
        by_document_id={"d1": rec_d1, "other": rec_other},
    )
    proj = ActiveKnowledgeProjection(
        project_id="p",
        retrieval_binding=GovernanceRetrievalBinding.EXPLICIT_PROJECTION,
        authoritative_document_ids=("other",),
    )
    p = _minimal_project()
    doc = _minimal_doc(
        "d1",
        approval=DocumentApprovalStatus.APPROVED,
        nc=NormativeClassification.PRIMARY_STANDARD,
        fam="AISC",
    )
    r = evaluate_document_readiness(
        document=doc,
        project=p,
        governance_record=rec_d1,
        projection=proj,
        governance_index=gidx,
    )
    assert not r.normative_eligible
    assert BLOCKED_NOT_IN_AUTHORITATIVE_PROJECTION in r.block_codes


def test_evidence_hint_governance_refusal() -> None:
    html = readiness_hint_html_for_evidence(
        answer_status="insufficient_evidence",
        citation_authority_requested="normative_active_primary",
        refusal_codes=("GOVERNANCE_EXPLICIT_PROJECTION_UNAVAILABLE",),
        project_id="proj_x",
    )
    assert "corpus" in html
    assert "proj_x" in html


def test_evidence_hint_insufficient_only() -> None:
    html = readiness_hint_html_for_evidence(
        answer_status="insufficient_evidence",
        citation_authority_requested="normative_active_primary",
        refusal_codes=("INSUFFICIENT_CORPUS_EVIDENCE",),
        project_id="proj_x",
    )
    assert "readiness" in html.lower()


@pytest.fixture
def client(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    monkeypatch.setenv("STRUCTURAL_TREE_WORKSPACE", str(ws))
    return TestClient(create_app())


def _session_project(client: TestClient) -> str:
    r = client.post(
        "/workbench/project/create",
        data={
            "name": "R",
            "description": "",
            "language": "es",
            "unit_system": "SI",
            "primary_standard_family": "AISC",
        },
        follow_redirects=False,
    )
    assert r.status_code == 303
    hub = client.get("/workbench")
    m = re.search(r"<code>(proj_[a-z0-9]+)</code>", hub.text)
    assert m
    return m.group(1)


def test_e2e_detail_shows_readiness_labels(client: TestClient, tmp_path) -> None:
    pid = _session_project(client)
    fpath = tmp_path / "e2e.txt"
    fpath.write_text("unique_e2e_readiness_token steel beam\n", encoding="utf-8")
    with open(fpath, "rb") as fh:
        client.post("/workbench/project/corpus/upload", files={"files": ("e2e.txt", fh, "text/plain")})

    from structural_tree_app.services.project_service import ProjectService

    ps = ProjectService(tmp_path / "ws")
    doc_id = ps.load_project(pid).ingested_document_ids[0]

    page = client.get(f"/workbench/project/corpus/document/{doc_id}")
    assert page.status_code == 200
    assert "Retrieval readiness" in page.text
    assert "blocked_missing_approval" in page.text or BLOCKED_MISSING_APPROVAL in page.text

    client.post(f"/workbench/project/corpus/document/{doc_id}/approve")
    client.post(
        f"/workbench/project/corpus/document/{doc_id}/readiness-metadata",
        data={"normative_classification": "primary_standard", "standard_family": "AISC"},
    )
    apply_manual_corpus_bootstrap(
        ps.governance_store(), pid, doc_id, "authoritative_active", actor="test", rationale="e2e"
    )
    client.post("/workbench/project/corpus/projection/sync-legacy-allowed")

    detail = client.get(f"/workbench/project/corpus/document/{doc_id}")
    assert detail.status_code == 200
    assert READY_FOR_NORMATIVE_RETRIEVAL in detail.text

    q = LocalAssistQuery(
        project_id=pid,
        retrieval_query_text="unique_e2e_readiness_token",
        citation_authority="normative_active_primary",
        retrieval_limit=10,
    )
    out = LocalAssistOrchestrator(ps).run(q)
    assert out.answer_status == "evidence_passages_assembled"
    assert out.citations

    ev = client.post(
        "/workbench/project/evidence/query",
        data={
            "retrieval_query_text": "unique_e2e_readiness_token",
            "citation_authority": "normative_active_primary",
            "retrieval_limit": "10",
            "match_project_primary_standard_family": "1",
        },
    )
    assert ev.status_code == 200
    assert "unique_e2e_readiness_token" in ev.text or "evidence_passages_assembled" in ev.text


def test_evidence_panel_shows_readiness_hint_when_insufficient(client: TestClient, tmp_path) -> None:
    pid = _session_project(client)
    fpath = tmp_path / "empty.txt"
    fpath.write_text("no matching query terms xyzabc12345\n", encoding="utf-8")
    with open(fpath, "rb") as fh:
        client.post("/workbench/project/corpus/upload", files={"files": ("empty.txt", fh, "text/plain")})

    r = client.post(
        "/workbench/project/evidence/query",
        data={
            "retrieval_query_text": "completely_unlikely_token_zzzz_99999",
            "citation_authority": "normative_active_primary",
            "retrieval_limit": "5",
            "match_project_primary_standard_family": "1",
        },
    )
    assert r.status_code == 200
    assert "readiness-hint" in r.text


def test_unknown_document_redirects(client: TestClient) -> None:
    _session_project(client)
    r = client.get("/workbench/project/corpus/document/doc_nope_nope", follow_redirects=False)
    assert r.status_code == 303
