# Phase G4 — Retrieval + orchestration aligned with governed active knowledge projection

**Status:** Implemented (2026-04-18).

## Scope delivered

| Area | Implementation |
|------|----------------|
| Retrieval | `RetrievalResponse` extended with `normative_retrieval_source`, `governance_warnings`, `governance_normative_block`; `DocumentRetrievalService.search` branches on `active_knowledge_projection.retrieval_binding`. |
| Binding modes | **`legacy_allowed_documents`** (default): normative gate = `active_code_context.allowed_document_ids` (unchanged). **`explicit_projection`**: normative gate = effective authoritative ids from projection, validated against `document_governance_index`; legacy allow-list not used for normative. |
| Refusal | Missing index, empty authoritative set after validation, or `conflicting_unresolved` on any authoritative row → `insufficient_evidence` with explicit messages + `governance_normative_block` kind. |
| Orchestrator | `LocalAssistOrchestrator` forwards `governance_warnings`; refusal codes `GOVERNANCE_CONFLICT_BLOCKS_NORMATIVE` / `GOVERNANCE_EXPLICIT_PROJECTION_UNAVAILABLE` vs generic corpus refusal. |
| Tests | `tests/test_governance_g4.py`. |

## Product rules preserved

- No silent switch: explicit opt-in via `retrieval_binding: explicit_projection` in `active_knowledge_projection.json`.
- `approved_ingested` remains a distinct, non-normative-authoritative path (not narrowed by explicit authoritative lists).
- Supporting corpus behavior stays labeled via citation mode + warnings on successful explicit normative retrieval.

## Out of scope (U1+)

Evidence/chat UI, governance dashboard, advanced re-index, full conflict-resolution UX, LLM runtime.
