# Deferred evidence-viewing UX (not U3)

**Status:** Partially addressed (2026-04-19) — see `docs/implementation/PHASE_EVIDENCE_VIEWER_STATUS.md`. **Still deferred:** coordinate-level PDF region highlight, in-page text search, OCR, full annotation product.

## Requirement

When the user opens a citation or source reference from local assist results, the **target experience** should eventually show the **original source page or file view** (for example the **original PDF at the relevant page**) rather than **only** extracted plain text.

Preferably, the viewer should **highlight the most relevant referenced section** aligned with the citation (when technically honest).

## Implemented baseline (evidence viewer hardening)

`GET /workbench/project/evidence/fragment/{document_id}/{fragment_id}` renders **`evidence_source_view.html`**: original PDF/text **when hash-verified**, side-by-side with the **exact** stored fragment text; explicit precision labels; `GET /workbench/project/evidence/source/{document_id}/file` serves bytes for embedding.

## Former interim note (superseded for routing)

Previously this URL showed fragment text only; the route is unchanged but the template now prioritizes **original source context** where possible.

## Product constraint

Governed retrieval and citation **identifiers** remain authoritative; any future PDF/page viewer must **not** replace or silently override refusal, governance blocks, or citation slots.
