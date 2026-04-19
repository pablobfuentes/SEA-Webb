# Phase R1 — Status (local assist orchestration contract)

**Date:** 2026-04-18  
**Planning context:** `docs/11_product_rebaseline_local_ai_chat_first.md`, `docs/12_revised_execution_order_after_rebaseline.md`

## Outcome

**Complete.** Backend-only contract for chat-first local assist:

| Artifact | Location |
|----------|----------|
| Request / response models | `src/structural_tree_app/domain/local_assist_contract.py` |
| Orchestrator (retrieval-only + optional assumptions + optional deterministic hooks) | `src/structural_tree_app/services/local_assist_orchestrator.py` |
| Tests | `tests/test_local_assist_r1.py` |

## Rules enforced

- All document text enters only via `DocumentRetrievalService.search` (approved corpus gates unchanged).
- No LLM; `answer_text` is a bounded disclosure + hit count or refusal message.
- Citations carry explicit `authority_class` (`authoritative_normative_active_primary` vs `approved_supporting_corpus`).
- Deterministic `Calculation` pointers are separate (`DeterministicHookItem`), never promoted to citation authority; M5 preliminary labeled `preliminary_deterministic_m5`.
- Refusal codes for empty query, long query, missing project, insufficient retrieval hits.

## Next

**Roadmap:** Evidence UI and chat shells are in **`docs/14_detailed_revised_execution_order_with_governed_knowledge.md`** (**U1–U2**). **G0–G4** (governance + active corpus alignment) should progress **before** claiming normative evidence UX is complete; extend `LocalAssistOrchestrator` / retrieval to **active projection** at **G4** (see **`docs/13_document_governance_and_active_truth_rebaseline.md`**). Legacy label “R2” ≈ **U1** in doc 14.

**No** Block 4A-M7 resumption required for governance track.
