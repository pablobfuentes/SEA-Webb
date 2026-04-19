# Phase G0 — Governance foundations — Status

**Scope:** Data model, JSON schemas, deterministic codecs, persisted files under `{project_id}/governance/`, validation on load/save, and `GovernanceStore` API. **No** retrieval wiring, **no** supersession algorithms, **no** UI.

**Execution order:** See `docs/14_detailed_revised_execution_order_with_governed_knowledge.md` (G0 → G1+).

## Delivered

| Area | Notes |
|------|--------|
| Domain enums | `GovernancePipelineStage`, `DocumentGovernanceDisposition`, `GovernanceEventType`, `GovernanceRetrievalBinding` (`domain/governance_enums.py`). |
| Models | `ActiveKnowledgeProjection`, `DocumentGovernanceRecord`, `DocumentGovernanceIndex`, `GovernanceEvent`, `GovernanceEventLog` (`domain/governance_models.py`). |
| Codecs | Deterministic key ordering for JSON-friendly dicts (`domain/governance_codec.py`). |
| Schemas | `schemas/active_knowledge_projection.schema.json`, `document_governance_record.schema.json`, `document_governance_index.schema.json`, `governance_event.schema.json`, `governance_event_log.schema.json` (event log uses `$defs` for events — no cross-file `$ref`). |
| Validation | `validate_*_payload` helpers in `validation/json_schema.py`. |
| Persistence | `GovernanceStore` — load/save optional files; `initialize_governance_baseline()` writes legacy-binding baseline + empty index + one `baseline_initialized` event (`services/governance_store.py`). |
| Project layout | `ProjectService._ensure_layout` creates `governance/`; `ProjectService.governance_store()` accessor. |
| Tests | `tests/test_governance_g0.py` — round-trips, determinism, validation failures, backward compatibility (no files), partial-state guard, baseline idempotency. |

## Non-goals (explicit)

- Changing `DocumentRetrievalService` / `LocalAssistOrchestrator` / `allowed_document_ids` behavior (deferred to G4+ wiring).
- Governance dashboard, approval UI, re-index jobs, chat/evidence surfaces.

## Backward compatibility

Projects without `governance/*` files behave as before: `try_load_*` returns `None`; core project/tree/document flows unchanged until callers opt into `initialize_governance_baseline` or manual file writes.

**Last updated:** 2026-04-18 (G0 implementation complete).
