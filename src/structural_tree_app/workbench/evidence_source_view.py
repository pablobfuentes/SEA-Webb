"""Evidence source view — honest original-file context for citations (thin view-model helpers)."""

from __future__ import annotations

from pathlib import Path

from structural_tree_app.domain.models import Document, DocumentFragment
from structural_tree_app.services.document_service import verify_document_file_bytes
from structural_tree_app.workbench.evidence_pdf_pages import pdf_url_fragment_page_open_params


def build_evidence_source_view_context(doc: Document, frag: DocumentFragment) -> dict[str, object]:
    """
    Build template context for citation source viewing.

    Precision rules:
    - ``location_precision`` is ``exact_page`` | ``page_range`` | ``unknown_page`` for PDFs;
      text ingests have no page mapping (unknown).
    - Region highlight is never claimed: excerpt is always the stored fragment text (exact for audit).
    """
    ext = Path(doc.file_path or "").suffix.lower() if doc.file_path else ""
    file_ok = verify_document_file_bytes(doc)
    file_url = f"/workbench/project/evidence/source/{doc.id}/file" if file_ok else None

    # Stored page_start/page_end: 1-based physical page index (see document_service / evidence_pdf_pages).
    ps, pe = frag.page_start, frag.page_end
    if ext == ".pdf":
        if ps is not None and pe is not None and pe != ps:
            location_precision = "page_range"
            location_note = (
                f"Physical page range for this fragment: {ps}–{pe} (first page of file = 1). "
                f"Open/link targets page {ps} (start of range); text may span pages."
            )
        elif ps is not None:
            location_precision = "exact_page"
            location_note = (
                f"Fragment mapped to physical PDF page {ps} (first page of file = 1). "
                "Same value is used for the #page= viewer link."
            )
        else:
            location_precision = "unknown_page"
            location_note = (
                "Physical page index for this fragment is not recorded. "
                "Link opens at file page 1 for context; excerpt remains the authoritative cited text."
            )
    else:
        location_precision = "unknown_page"
        if ext in (".txt", ".text"):
            location_note = (
                "Plain-text ingest has no page mapping. Original file is shown beside the cited excerpt."
            )
        else:
            location_note = "No page mapping for this format."

    highlight_note = (
        "No PDF region / coordinate highlight: the excerpt below is the exact governed fragment text "
        "stored at ingest. The file panel provides original-document context only."
    )

    # Target page: 1-based physical — identical to storage, identical to PDF.js page arg.
    pdf_viewer_target_page_1based: int | None = None
    pdf_open_url: str | None = None    # direct file + #page= (new-tab fallback)
    pdf_viewer_url: str | None = None  # PDF.js viewer iframe src (primary embed)
    if file_ok and ext == ".pdf":
        pdf_viewer_target_page_1based = ps if ps is not None else 1
        if file_url is not None:
            pdf_open_url = file_url + pdf_url_fragment_page_open_params(pdf_viewer_target_page_1based)
            pdf_viewer_url = f"/workbench/project/evidence/source/{doc.id}/viewer?page={pdf_viewer_target_page_1based}"

    if file_ok and ext == ".pdf":
        mode = "pdf_side_by_side"
    elif file_ok and ext in (".txt", ".text"):
        mode = "text_side_by_side"
    else:
        mode = "fragment_only"

    return {
        "source_view_mode": mode,
        "file_url": file_url,
        "file_available": file_ok,
        "pdf_viewer_target_page_1based": pdf_viewer_target_page_1based,
        "pdf_open_url": pdf_open_url,
        "pdf_viewer_url": pdf_viewer_url,
        "page_start": ps,
        "page_end": pe,
        "location_precision": location_precision,
        "location_note": location_note,
        "highlight_note": highlight_note,
        "file_ext": ext or "(unknown)",
        "page_semantics_note": (
            "Page numbers are physical order in the PDF file (page 1 = first page). "
            "They are not guaranteed to match printed sheet numbers on the document."
        ),
    }
