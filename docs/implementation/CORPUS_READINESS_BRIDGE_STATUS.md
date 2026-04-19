# Corpus readiness / approval bridge — status

**Date:** 2026-04-18  
**Scope:** Close the gap between ingest, governance disposition, and **normative** evidence retrieval, without U2, broad governance UI, or retrieval redesign.

## Delivered

- **`services/corpus_readiness.py`** — Deterministic readiness labels (`ready_for_normative_retrieval`, `ready_for_supporting_retrieval_only`, `blocked_*`) aligned with `DocumentRetrievalService` gates and G4 projection blocks (missing index, empty authoritative, authoritative conflict).
- **Corpus UI** — List column **Readiness label**; document detail **Retrieval readiness** block with checklist (approval, classification, `standard_family` vs `active_code_context.primary_standard_family`, binding mode, legacy vs explicit membership, governance index, project-level block when applicable).
- **Actions** — `POST .../approve` (calls `DocumentIngestionService.approve_document`); `POST .../readiness-metadata` (updates `normative_classification`, `standard_family`).
- **Evidence panel** — `u1_readiness_hint_html` + template snippet after refusals for normative mode (link to corpus; governance vs “no passages” copy).
- **Tests** — `tests/test_corpus_readiness_bridge.py` (unit + workbench HTTP).

## Compliance

- Upload/ingest ≠ authoritative activation (unchanged).
- Readiness UI does not claim normative authority unless `evaluate_document_readiness` reports `ready_for_normative_retrieval`.
- Retrieval remains the authority gate; readiness explains gaps.

## Next (out of scope here)

- U2, full governance dashboard, bulk corpus admin, chat shell, OCR, broad retrieval redesign.
