"""Phase U1 — evidence panel routes, authority labels, fragment source link, governance refusal visibility."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from structural_tree_app.domain.enums import NormativeClassification
from structural_tree_app.domain.governance_enums import GovernanceRetrievalBinding
from structural_tree_app.domain.governance_models import ActiveKnowledgeProjection
from structural_tree_app.domain.models import utc_now
from structural_tree_app.services.document_service import DocumentIngestionService
from structural_tree_app.workbench.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    monkeypatch.setenv("STRUCTURAL_TREE_WORKSPACE", str(ws))
    return TestClient(create_app())


def _session_project(client: TestClient) -> str:
    r = client.post(
        "/workbench/project/create",
        data={"name": "U1", "description": "", "language": "es", "unit_system": "SI", "primary_standard_family": "AISC"},
        follow_redirects=False,
    )
    assert r.status_code == 303
    hub = client.get("/workbench")
    assert hub.status_code == 200
    # Session cookie set — extract project id from page
    import re

    m = re.search(r"<code>(proj_[a-z0-9]+)</code>", hub.text)
    assert m, hub.text[:500]
    return m.group(1)


def test_u1_evidence_panel_requires_project(client: TestClient) -> None:
    r = client.get("/workbench/project/evidence", follow_redirects=False)
    assert r.status_code == 303
    assert r.headers["location"].startswith("/workbench")


def test_u1_evidence_panel_renders_with_session(client: TestClient) -> None:
    _session_project(client)
    r = client.get("/workbench/project/evidence")
    assert r.status_code == 200
    assert "Evidence panel" in r.text
    assert "LocalAssistOrchestrator" in r.text
    assert "retrieval_query_text" in r.text


def test_u1_post_assist_shows_citations_and_legacy_binding(client: TestClient, tmp_path) -> None:
    _session_project(client)
    ps_path = tmp_path / "ws"
    # Resolve project id from last hub response
    hub = client.get("/workbench")
    import re

    m = re.search(r"<code>(proj_[a-z0-9]+)</code>", hub.text)
    assert m
    pid = m.group(1)
    from structural_tree_app.services.project_service import ProjectService

    ps = ProjectService(ps_path)
    src = tmp_path / "corp.txt"
    src.write_text("Steel beam flexure design provisions AISC unique_u1_token.", encoding="utf-8")
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(
        src,
        title="Steel ref",
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="AISC",
    )
    assert ir.document
    ing.approve_document(ir.document.id)
    ing.activate_for_normative_corpus(ir.document.id)

    r = client.post(
        "/workbench/project/evidence/query",
        data={
            "retrieval_query_text": "flexure unique_u1_token",
            "citation_authority": "normative_active_primary",
            "retrieval_limit": "5",
            "include_project_assumptions": "1",
            "match_project_primary_standard_family": "1",
        },
    )
    assert r.status_code == 200
    assert "evidence_passages_assembled" in r.text
    assert "legacy_allowed_documents" in r.text or "Normative retrieval" in r.text
    assert "Open source fragment" in r.text
    assert "/workbench/project/evidence/fragment/" in r.text


def test_u1_fragment_route_shows_text(client: TestClient, tmp_path) -> None:
    _session_project(client)
    hub = client.get("/workbench")
    import re

    m = re.search(r"<code>(proj_[a-z0-9]+)</code>", hub.text)
    pid = m.group(1)
    from structural_tree_app.services.project_service import ProjectService

    ps = ProjectService(tmp_path / "ws")
    src = tmp_path / "frag.txt"
    src.write_text("Fragment body for u1 route test.", encoding="utf-8")
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(src, title="Frag doc", normative_classification=NormativeClassification.PRIMARY_STANDARD)
    assert ir.document
    doc_id = ir.document.id
    frags = ing.load_fragments(doc_id)
    assert frags
    fid = frags[0].id

    page = client.get(f"/workbench/project/evidence/fragment/{doc_id}/{fid}")
    assert page.status_code == 200
    assert "Fragment body for u1 route test." in page.text
    assert doc_id in page.text


def test_u1_explicit_projection_shown_in_html(client: TestClient, tmp_path) -> None:
    _session_project(client)
    hub = client.get("/workbench")
    import re

    pid = re.search(r"<code>(proj_[a-z0-9]+)</code>", hub.text).group(1)
    from structural_tree_app.services.project_service import ProjectService

    ps = ProjectService(tmp_path / "ws")
    src = tmp_path / "exp.txt"
    src.write_text("Explicit projection unique exp_u1.", encoding="utf-8")
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(
        src,
        title="E",
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="AISC",
    )
    assert ir.document
    did = ir.document.id
    ing.approve_document(did)
    ing.activate_for_normative_corpus(did)
    gs = ps.governance_store()
    cur = gs.try_load_active_knowledge_projection(pid)
    assert cur
    gs.save_active_knowledge_projection(
        ActiveKnowledgeProjection(
            project_id=pid,
            schema_version=cur.schema_version,
            updated_at=utc_now(),
            retrieval_binding=GovernanceRetrievalBinding.EXPLICIT_PROJECTION,
            authoritative_document_ids=(did,),
            supporting_document_ids=cur.supporting_document_ids,
            excluded_from_authoritative_document_ids=cur.excluded_from_authoritative_document_ids,
            notes=cur.notes,
        )
    )

    r = client.post(
        "/workbench/project/evidence/query",
        data={
            "retrieval_query_text": "exp_u1",
            "citation_authority": "normative_active_primary",
            "retrieval_limit": "5",
        },
    )
    assert r.status_code == 200
    assert "explicit_projection" in r.text
    assert "explicit active knowledge projection" in r.text.lower() or "Explicit" in r.text


def test_u1_governance_refusal_visible(client: TestClient, tmp_path) -> None:
    _session_project(client)
    hub = client.get("/workbench")
    import re

    pid = re.search(r"<code>(proj_[a-z0-9]+)</code>", hub.text).group(1)
    from structural_tree_app.domain.governance_models import DocumentGovernanceIndex, DocumentGovernanceRecord
    from structural_tree_app.domain.governance_enums import DocumentGovernanceDisposition
    from structural_tree_app.services.project_service import ProjectService

    ps = ProjectService(tmp_path / "ws")
    src = tmp_path / "gov.txt"
    src.write_text("Conflict doc text.", encoding="utf-8")
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(
        src,
        title="G",
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="AISC",
    )
    did = ir.document.id
    ing.approve_document(did)
    ing.activate_for_normative_corpus(did)
    gs = ps.governance_store()
    idx = gs.try_load_document_governance_index(pid)
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
            project_id=pid,
            schema_version=idx.schema_version,
            updated_at=utc_now(),
            by_document_id={**idx.by_document_id, did: bumped},
        )
    )
    cur = gs.try_load_active_knowledge_projection(pid)
    assert cur
    gs.save_active_knowledge_projection(
        ActiveKnowledgeProjection(
            project_id=pid,
            schema_version=cur.schema_version,
            updated_at=utc_now(),
            retrieval_binding=GovernanceRetrievalBinding.EXPLICIT_PROJECTION,
            authoritative_document_ids=(did,),
            supporting_document_ids=cur.supporting_document_ids,
            excluded_from_authoritative_document_ids=cur.excluded_from_authoritative_document_ids,
            notes=cur.notes,
        )
    )

    r = client.post(
        "/workbench/project/evidence/query",
        data={"retrieval_query_text": "Conflict", "citation_authority": "normative_active_primary"},
    )
    assert r.status_code == 200
    assert "GOVERNANCE_CONFLICT_BLOCKS_NORMATIVE" in r.text
    assert "conflicting_unresolved" in r.text.lower() or "Refusal" in r.text


def test_u1_deterministic_hooks_section_not_citations(client: TestClient, tmp_path) -> None:
    _session_project(client)
    hub = client.get("/workbench")
    import re

    pid = re.search(r"<code>(proj_[a-z0-9]+)</code>", hub.text).group(1)
    from structural_tree_app.domain.models import Calculation
    from structural_tree_app.services.project_service import ProjectService
    from structural_tree_app.services.simple_span_m5_service import METHOD_LABEL as M5_METHOD_LABEL
    from structural_tree_app.storage.tree_store import TreeStore

    ps = ProjectService(tmp_path / "ws")
    store = TreeStore.for_live_project(ps.repository, pid)
    store.ensure_layout()
    store.save_calculation(
        Calculation(
            project_id=pid,
            node_id="n-u1",
            objective="x",
            method_label=M5_METHOD_LABEL,
            formula_text="n/a",
            inputs={},
            substitutions={},
            result={},
        )
    )

    r = client.post(
        "/workbench/project/evidence/query",
        data={
            "retrieval_query_text": "nomatchzzz999",
            "include_deterministic_hooks": "1",
        },
    )
    assert r.status_code == 200
    assert "Deterministic hooks" in r.text
    assert "not document evidence" in r.text.lower()
    assert "preliminary_deterministic_m5" in r.text.lower() or "preliminary" in r.text.lower()


def test_u1_bad_fragment_ids(client: TestClient) -> None:
    _session_project(client)
    r = client.get("/workbench/project/evidence/fragment/doc_bad/frag_bad")
    assert r.status_code == 200
    assert "not found" in r.text.lower() or "Fragment not found" in r.text
