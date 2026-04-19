"""Unit tests for PDF page URL helpers (evidence viewer)."""

from __future__ import annotations

import pytest

from structural_tree_app.workbench.evidence_pdf_pages import pdf_url_fragment_page_open_params


def test_open_params_first_page_is_one() -> None:
    assert pdf_url_fragment_page_open_params(1) == "#page=1"


def test_open_params_rejects_zero() -> None:
    with pytest.raises(ValueError):
        pdf_url_fragment_page_open_params(0)
