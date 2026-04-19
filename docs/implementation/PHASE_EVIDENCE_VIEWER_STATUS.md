# Phase — Evidence UX: original source viewer (status)

**Date:** 2026-04-19  
**Scope:** Harden citation opening toward **original governed files** (especially PDF page context) without OCR, full annotation, or chat/governance redesign.

## Delivered

| Area | Detail |
|------|--------|
| **Routes** | `GET /workbench/project/evidence/fragment/{document_id}/{fragment_id}` → `evidence_source_view.html` with `build_evidence_source_view_context`. `GET /workbench/project/evidence/source/{document_id}/file` → `FileResponse` when `verify_document_file_bytes` passes; else `404`. |
| **Ingest** | After successful text extraction, source bytes copied to `documents/{doc_id}/original{ext}` so corpus temp paths do not break file serving. |
| **PDF** | Iframe to verified file URL + `#page=N` when `page_start` known; range spans labeled **page_range**; unknown page opens page 1 with explicit copy. |
| **Text** | Side-by-side iframe + fragment; no page mapping (honest). |
| **Honesty** | No coordinate highlight; excerpt panel = exact `DocumentFragment.text`; location precision string surfaced in UI. |
| **Links** | Chat / evidence / canvas still use `/evidence/fragment/...`; label **Open citation source view**. |

## Explicitly out of scope (unchanged)

- OCR, full PDF annotation editor, multi-document viewer app, speculative coordinate mapping.

## Tests

`tests/test_evidence_original_source_viewer.py` (+ `tests/fixtures/sample_text.pdf`).

## Tensions / follow-ups

- **Duplicate skip:** documents ingested before durable copy may still reference ephemeral paths until re-ingest.
- **Browser PDF:** inline embed may ignore `#page=`; **new-tab link** is primary; see `evidence_pdf_pages.py` for 1-based physical page = `#page=` convention.
- **Region highlight:** remains deferred; UI states excerpt is the authoritative fragment text.
