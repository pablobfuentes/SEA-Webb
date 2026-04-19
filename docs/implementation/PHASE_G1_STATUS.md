# Phase G1 — Ingestion-linked governance pipeline (ingested → analyzed → classified) — Status

**Scope:** Explicit persisted `DocumentGovernanceRecord` updates tied to successful document ingestion; optional deterministic promotion to **classified**; append-only pipeline events; **no** retrieval binding changes, **no** conflict/supersession, **no** UI.

**Depends on:** Phase G0 (`docs/implementation/PHASE_G0_STATUS.md`). **Next:** G2+ per `docs/14_detailed_revised_execution_order_with_governed_knowledge.md`.

## Delivered

| Area | Notes |
|------|--------|
| Domain | `DocumentAnalysisSnapshot`, `DocumentClassificationSnapshot`; `DocumentGovernanceRecord.analysis` / `.classification` (`domain/governance_models.py`). |
| Codecs | Nested snapshot dicts with sorted keys (`domain/governance_codec.py`). |
| Schemas | `document_governance_record.schema.json`, `document_governance_index.schema.json` — `schema_version` **g0.1** \| **g1.1**; optional `analysis` / `classification` on records. |
| Pipeline | `services/governance_document_pipeline.py` — `apply_governance_after_successful_ingestion`, `classification_complete_for_g1`, `classification_snapshot_from_document`, `promote_document_to_classified`. |
| Store | `GovernanceStore.append_governance_events`; baseline empty index uses **g1.1** for new projects. |
| Ingestion | `DocumentIngestionService` calls G1 pipeline after persist + ingested registration (`document_service.py`). |
| Tests | `tests/test_governance_g1.py` — ingest records, classified vs analyzed, explicit promote, validation failure, backward compat, retrieval regression, determinism. |

## Classification rules (G1, deterministic)

- **Incomplete** (stays **analyzed** terminal stage): `normative_classification == unknown`, or `primary_standard` without non-empty `standard_family`.
- **Complete** (terminal **classified**): otherwise, including non-primary normative classes with explicit enum value.

Ingestion does **not** change `DocumentGovernanceDisposition` (remains `pending_review`).

## Backward compatibility

Projects with no prior governance files: first successful ingest initializes G0 baseline (same as explicit `initialize_governance_baseline`) then writes the document index and events.

Older index files without `analysis`/`classification` keys still load via optional fields.

## Non-goals (explicit)

Retrieval / `LocalAssistOrchestrator` behavior unchanged. No active projection switching.

**Last updated:** 2026-04-18 (G1 implementation complete).
