"""Block 4A M4 — alternatives inspection: suggestions, characterization, provenance display."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from fastapi.testclient import TestClient

from structural_tree_app.domain.characterization_provenance import (
    PROVENANCE_MANUAL_PLACEHOLDER,
    PROVENANCE_NOT_YET_EVIDENCED,
    PROVENANCE_WORKFLOW_HEURISTIC,
)
from structural_tree_app.workbench.app import create_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    ws = tmp_path / "ws"
    monkeypatch.setenv("STRUCTURAL_TREE_WORKSPACE", str(ws))
    return TestClient(create_app())


def _setup_workflow(client: TestClient) -> None:
    client.post(
        "/workbench/project/create",
        data={"name": "M4", "description": "", "language": "es", "unit_system": "SI", "primary_standard_family": "AISC"},
        follow_redirects=True,
    )
    client.post(
        "/workbench/project/workflow",
        data={
            "span_m": "10",
            "support_condition": "simple_span",
            "member_role": "primary_steel_member",
            "include_optional_rolled_beam": "on",
        },
        follow_redirects=True,
    )


def test_m4_page_shows_suggestion_sections_and_provenance_legend(client: TestClient) -> None:
    _setup_workflow(client)
    page = client.get("/workbench/project/workflow")
    assert page.status_code == 200
    text = page.text
    assert "Characterization items (M4)" in text or "M4" in text
    assert "Authority" in text and "provenance" in text.lower()
    assert "Suggested alternatives" in text
    assert "Eligible alternatives" in text or "not in top" in text
    assert "All alternatives" in text
    assert "suggestion_provenance" in text
    assert "Characterization items" in text


def test_m4_characterization_provenance_strings_from_backend(client: TestClient) -> None:
    """Empty corpus: expect workflow heuristic + manual placeholder + not_yet_evidenced rows (retrieval-backed only if corpus hit)."""
    _setup_workflow(client)
    page = client.get("/workbench/project/workflow")
    assert page.status_code == 200
    body = page.text
    assert PROVENANCE_WORKFLOW_HEURISTIC in body
    assert PROVENANCE_MANUAL_PLACEHOLDER in body
    assert PROVENANCE_NOT_YET_EVIDENCED in body


def test_m4_suggested_alternatives_have_rank_and_score_columns(client: TestClient) -> None:
    _setup_workflow(client)
    page = client.get("/workbench/project/workflow")
    assert page.status_code == 200
    assert "suggestion_rank" in page.text or "rank" in page.text
    assert "suggestion_score" in page.text or "score" in page.text
