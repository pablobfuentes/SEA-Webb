# Phase R2B — Reasoning / formula-selection bridge (status)

**Scope:** Backend/domain only — auditable bridge over governed retrieval + G5 derived knowledge + deterministic tree hooks. **No** U5, **no** `LocalAssistOrchestrator` changes, **no** new solvers.

## Delivered

- **Contract:** `domain/reasoning_bridge_contract.py` — `ReasoningBridgeRequest` / `ReasoningBridgeResult` with explicit `authority_note` on anchors, `non_authoritative` on formula candidates, `SupportedExecutionStep` separated from citations.
- **Codec:** `domain/reasoning_bridge_codec.py` — deterministic serialization for U5.
- **Service:** `services/reasoning_bridge_service.py` — `ReasoningBridgeService.analyze(req)`:
  - Calls `DocumentRetrievalService.search` with the same parameters shape as assist (citation mode, limits, filters).
  - Loads optional G5 bundle via `DerivedKnowledgeService.try_load_bundle`.
  - Scans live `TreeStore` calculations when `include_deterministic_context` is true (M5 vs other method labels).
  - **Keyword map only** for vertical slice (`simple_span_steel_vertical_slice` when span/beam/flexure + steel/AISC/simple/load tokens co-occur).
- **Schema:** `schemas/reasoning_bridge_result.schema.json` + `validate_reasoning_bridge_result_payload`.

## Boundaries

- Retrieval remains the evidence gate; bridge adds interpretation rows, not merged design conclusions.
- Derived artifacts: labeled; missing bundle emits a gap, not an error.
- Deterministic steps: notes state engine-only / non-citation.

## References

- Tests: `tests/test_reasoning_bridge_r2b.py`.
- Changelog: `docs/CHANGELOG.md` (R2B entry).
