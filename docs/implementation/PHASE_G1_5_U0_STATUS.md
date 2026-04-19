# Phase G1.5 / U0 — Corpus bootstrap workbench — Status

**Scope:** Thin workbench surface to upload documents, inspect ingestion/governance state, apply **explicit** manual corpus bootstrap (authoritative / supporting / pending review), update active knowledge projection binding, and optionally sync legacy `allowed_document_ids` — **no** auto-approval, **no** full governance dashboard, **no** chat shell changes.

**Depends on:** G0–G4, U1 (orchestrator + evidence routes). **Out of scope:** OCR implementation, conflict dashboard, approval workflows, polished UI.

## Delivered

| Area | Notes |
|------|--------|
| Service | `services/corpus_bootstrap_service.py` — `apply_manual_corpus_bootstrap`, `set_projection_retrieval_binding`, `sync_legacy_allowed_documents_from_authoritative`; append-only `DISPOSITION_CHANGED` + `PROJECTION_UPDATED` events. |
| Workbench | `workbench/corpus_pages.py` — routes wired in `workbench/app.py`; templates `corpus_bootstrap.html`, `corpus_document.html`; hub link in `workbench_hub.html`. |
| Tests | `tests/test_workbench_corpus_bootstrap.py` — upload, duplicate, unsupported, ocr_deferred, list/detail, bootstrap actions, projection binding + legacy sync, orchestrator after explicit projection, bad project session, service error path. |

## Product rules

- Upload/ingest does **not** activate authoritative corpus; disposition stays `pending_review` until explicit bootstrap (or G3 proposal).
- UI distinguishes ingestion statuses: `ingested`, `duplicate_skipped`, `unsupported_document_for_ingestion`, `ocr_deferred`.
- Retrieval binding switch to `explicit_projection` is **explicit**; legacy sync is a separate explicit action (audited).

**Last updated:** 2026-04-18 (G1.5 / U0 implementation complete).
