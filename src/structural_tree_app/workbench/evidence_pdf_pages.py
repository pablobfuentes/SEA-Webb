"""PDF physical page indexing for the evidence source viewer.

**Storage (unchanged):** ``DocumentFragment.page_start`` / ``page_end`` are **1-based
physical page indices** — the first page of the PDF file is **1**. This matches
``enumerate(PdfReader.pages, start=1)`` in ``document_service._extract_pages_raw``.

**Viewer URL fragment:** PDF Open Parameters (commonly implemented in Chromium,
Firefox PDF.js, Adobe) use ``#page=n`` with **n ≥ 1** for the first page of the
file. We pass **the same** integer as the stored physical page (no off-by-one
conversion). The jump target for a range is the **first** physical page of the
range (``page_start``).

**Limitation:** Printed “folio” numbers on a drawing may differ from physical
order; we only have physical index from text extraction.
"""

from __future__ import annotations


def pdf_url_fragment_page_open_params(physical_page_1based: int) -> str:
    """Return the ``#page=`` fragment for viewers that follow PDF Open Parameters (1-based)."""
    if physical_page_1based < 1:
        raise ValueError("physical_page_1based must be >= 1")
    return f"#page={physical_page_1based}"
