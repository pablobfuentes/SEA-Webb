"""Phase U4 — logic & audit panel on chat / evidence (read-only deterministic artifacts)."""

from __future__ import annotations

import re

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from structural_tree_app.domain.enums import NormativeClassification, SourceType
from structural_tree_app.domain.models import Assumption, Calculation, Check
from structural_tree_app.services.document_service import DocumentIngestionService
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.services.simple_span_m5_service import METHOD_LABEL as M5_METHOD_LABEL
from structural_tree_app.services.tree_workspace import TreeWorkspace
from structural_tree_app.workbench.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("STRUCTURAL_TREE_WORKSPACE", str(tmp_path / "ws"))
    return TestClient(create_app())


def _session(client: TestClient) -> str:
    client.post(
        "/workbench/project/create",
        data={
            "name": "U4T",
            "description": "",
            "language": "es",
            "unit_system": "SI",
            "primary_standard_family": "AISC",
        },
        follow_redirects=False,
    )
    hub = client.get("/workbench")
    m = re.search(r"<code>(proj_[a-z0-9]+)</code>", hub.text)
    assert m
    return m.group(1)


def test_u4_empty_state_chat_and_evidence(client: TestClient) -> None:
    _session(client)
    r = client.get("/workbench/project/chat")
    assert r.status_code == 200
    assert 'id="u4-logic-audit"' in r.text
    assert "No logic artifacts recorded yet" in r.text
    e = client.get("/workbench/project/evidence")
    assert e.status_code == 200
    assert "No logic artifacts recorded yet" in e.text


def test_u4_chat_requires_project(client: TestClient) -> None:
    r = client.get("/workbench/project/chat", follow_redirects=False)
    assert r.status_code == 303


def test_u4_renders_calculation_check_assumption(client: TestClient, tmp_path) -> None:
    pid = _session(client)
    ps = ProjectService(tmp_path / "ws")
    tw = TreeWorkspace(ps, ps.load_project(pid))
    b, root = tw.create_root_problem("P", "D")
    ref_id = "ref_aabbccddeeff"
    from structural_tree_app.domain.models import Reference

    tw.store.save_reference(
        Reference(
            id=ref_id,
            project_id=pid,
            document_id="doc_x",
            fragment_id="frag_y",
            usage_type="evidence_link",
            citation_short="[stub]",
            citation_long="",
            quoted_context="",
        )
    )
    calc = Calculation(
        id="calc_aabbccddeeff",
        project_id=pid,
        node_id=root.id,
        objective="U4 test objective",
        method_label="block3_u4_test_stub",
        formula_text="(persisted only)",
        inputs={"a": 1},
        substitutions={"a": "1"},
        result={"ok": True},
        reference_ids=[ref_id],
        status="draft",
        created_at="2026-04-18T00:00:00+00:00",
        updated_at="2026-04-18T00:00:00+00:00",
    )
    tw.store.save_calculation(calc)
    chk = Check(
        id="chk_aabbccddeeff",
        project_id=pid,
        node_id=root.id,
        calculation_id=calc.id,
        check_type="u4_placeholder",
        demand={"v": 1.0},
        capacity={"v": 2.0},
        utilization_ratio=0.5,
        status="ok",
        message="preliminary check message for U4",
        reference_ids=[],
    )
    tw.store.save_check(chk)
    asm = Assumption(
        project_id=pid,
        node_id=root.id,
        label="u4_span_m",
        value=6.0,
        unit="m",
        source_type=SourceType.USER_CONFIRMED,
        rationale="U4 test assumption",
    )
    ps.save_assumptions(pid, [asm])

    r = client.get("/workbench/project/chat")
    assert r.status_code == 200
    assert "calc_aabbccddeeff" in r.text
    assert "block3_u4_test_stub" in r.text
    assert "chk_aabbccddeeff" in r.text
    assert "u4_placeholder" in r.text
    assert "u4_span_m" in r.text
    assert "preliminary check message for U4" in r.text
    assert 'class="u4-det-badge"' in r.text
    assert "No logic artifacts recorded yet" not in r.text


def test_u4_m5_preliminary_badge_and_disclaimer(client: TestClient, tmp_path) -> None:
    pid = _session(client)
    ps = ProjectService(tmp_path / "ws")
    tw = TreeWorkspace(ps, ps.load_project(pid))
    _b, root = tw.create_root_problem("P", "D")
    calc = Calculation(
        id="calc_deadbeef0001",
        project_id=pid,
        node_id=root.id,
        objective="M5 slice",
        method_label=M5_METHOD_LABEL,
        formula_text="m5",
        inputs={},
        substitutions={},
        result={"version": M5_METHOD_LABEL},
        status="draft",
        created_at="2026-04-18T00:00:00+00:00",
        updated_at="2026-04-18T00:00:00+00:00",
    )
    tw.store.save_calculation(calc)
    r = client.get("/workbench/project/evidence")
    assert r.status_code == 200
    assert "preliminary M5" in r.text
    assert M5_METHOD_LABEL in r.text
    assert "not code-compliant" in r.text.lower() or "not final" in r.text.lower()


def test_u4_deterministic_rows_not_citation_badges(client: TestClient, tmp_path) -> None:
    """U4 deterministic rows use u4-det-badge; do not reuse normative citation badge.auth."""
    pid = _session(client)
    ps = ProjectService(tmp_path / "ws")
    tw = TreeWorkspace(ps, ps.load_project(pid))
    _b, root = tw.create_root_problem("P", "D")
    calc = Calculation(
        id="calc_deadbeef0002",
        project_id=pid,
        node_id=root.id,
        objective="x",
        method_label="x",
        formula_text="x",
        inputs={},
        substitutions={},
        result={},
        status="draft",
        created_at="2026-04-18T00:00:00+00:00",
        updated_at="2026-04-18T00:00:00+00:00",
    )
    tw.store.save_calculation(calc)
    r = client.get("/workbench/project/chat")
    assert 'class="u4-det-badge"' in r.text
    # Citation authority badges only appear inside assist response; no assist => no badge.auth in page... 
    # Actually chat page may not have badge.auth without assist. Assert u4 block has no "badge auth" in u4-calc-row
    assert "u4-calc-row" in r.text
    idx = r.text.find("u4-calc-row")
    chunk = r.text[idx : idx + 800]
    assert "badge auth" not in chunk


def test_u4_stable_with_retrieval_response(client: TestClient, tmp_path) -> None:
    """Assist citations + U4 audit both present; deterministic audit separate from citations list."""
    pid = _session(client)
    ps = ProjectService(tmp_path / "ws")
    tw = TreeWorkspace(ps, ps.load_project(pid))
    _b, root = tw.create_root_problem("P", "D")
    calc = Calculation(
        id="calc_deadbeef0003",
        project_id=pid,
        node_id=root.id,
        objective="coexist",
        method_label="coexist_m",
        formula_text="f",
        inputs={},
        substitutions={},
        result={},
        status="draft",
        created_at="2026-04-18T00:00:00+00:00",
        updated_at="2026-04-18T00:00:00+00:00",
    )
    tw.store.save_calculation(calc)

    src = tmp_path / "u4doc.txt"
    src.write_text("Steel flexure token_u4_stable_xyz.", encoding="utf-8")
    ing = DocumentIngestionService(ps, pid)
    ir = ing.ingest_local_file(
        src,
        title="Ref",
        normative_classification=NormativeClassification.PRIMARY_STANDARD,
        standard_family="AISC",
    )
    assert ir.document
    ing.approve_document(ir.document.id)
    ing.activate_for_normative_corpus(ir.document.id)

    r = client.post(
        "/workbench/project/chat/query",
        data={
            "retrieval_query_text": "token_u4_stable_xyz",
            "citation_authority": "normative_active_primary",
            "retrieval_limit": "5",
        },
    )
    assert r.status_code == 200
    assert 'aria-label="Assist response"' in r.text
    assert "Citations" in r.text
    assert "calc_deadbeef0003" in r.text
    assert 'class="u4-det-badge"' in r.text
    assert 'id="u4-logic-audit"' in r.text
