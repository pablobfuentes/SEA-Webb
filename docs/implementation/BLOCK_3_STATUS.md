# Block 3 — Status tracker

Single source of truth for Block 3 milestones in `structural_tree_app_foundation`.  
Planning: `docs/06_block_3_implementation_plan.md` · Acceptance: `docs/07_block_3_acceptance_snapshot.md`

**Defaults (approved):** SI-only for the first deterministic slice · open option-space via deterministic catalog for this workflow family · top-3 alternatives are suggestion-only (`workflow_heuristic`) and all eligible alternatives remain persisted/selectable.

| Milestone | Status | Notes |
|-----------|--------|-------|
| M1 — Planning | **Complete** | `docs/06_block_3_implementation_plan.md`, `docs/07_block_3_acceptance_snapshot.md` |
| M2 — Calculation / Check / Reference tree persistence | **Complete** | `tree/calculations/`, `tree/checks/`, `tree/references/`; codecs + JSON Schema; `TreeStore` save/load; revision snapshots include full `tree/` copy; `validate_tree_integrity` extended; tests: `tests/test_tree_calculation_check_persistence.py` |
| M3 — Simple-span workflow & branch generation | **Complete (M3.1 corrected)** | Catalog-driven eligible alternatives + deterministic top-3 suggestion flags (all eligible persisted); `Branch.origin_alternative_id`; `Alternative` suggestion metadata; integrity checks + backward-compatible schemas/codecs; tests: `tests/test_simple_span_steel_workflow_m3.py` |
| M4 — Evidence-backed characterization | **Complete** | Structured `characterization_items` on `Alternative` with provenance (`retrieval_backed`, `workflow_heuristic`, `manual_placeholder`, `not_yet_evidenced`); `DocumentRetrievalService` wired for normative corpus; `apply_simple_span_m4_characterization` after M3 setup; `TreeWorkspace.materialize_working_branch_for_alternative`; clone + integrity + schema; tests: `tests/test_simple_span_m4_characterization.py` |
| M5 — Deterministic calculation slice | **Complete** | Narrow preliminary metrics + `preliminary_max_depth_fit` / `preliminary_fabrication_alignment` checks; `services/deterministic/simple_span_preliminary_m5.py` + `run_simple_span_m5_preliminary` (path root); explicit assumptions; no retrieval/LLM; tests: `tests/test_simple_span_m5_preliminary.py` |
| M6 — Branch comparison enrichment | **Complete** | `BranchComparisonRow` now carries explicit M5 preliminary slice projection + checks discovered via `calculation_id`; comparison field-source map separates `m5_deterministic_preliminary`, `branch_tree_derived`, `manual_placeholder`, `document_trace_pending`; discarded/non-selected branches still comparable; tests: `tests/test_branch_comparison.py` |
| M7 — E2E vertical flow validation | Pending | — |

**Last updated:** Block 3 M6 (comparison enriched with explicit preliminary M5 provenance boundaries and check-discovery path).
