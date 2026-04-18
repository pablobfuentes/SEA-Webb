# Block 3 — Validation report (M7)

**Date:** 2026-04-18  
**Scope:** End-to-end acceptance of the **Block 3 vertical slice** (simple-span steel primary member: workflow, characterization, working branch, M5 preliminary deterministics, M6 comparison enrichment, revision replay).  
**Planning references:** `docs/06_block_3_implementation_plan.md`, `docs/07_block_3_acceptance_snapshot.md`.

---

## 1. End-to-end scenario validated

**Automated test:** `tests/test_block3_vertical_flow.py` — `test_block3_m7_vertical_e2e_simple_span_castellated_m5_m6_revision_replay`

**Narrative (single coherent vertical flow):**

1. **Simple-span workflow setup (M3):** New project; `SimpleSpanSteelWorkflowService.setup_initial_workflow` with `SimpleSpanWorkflowInput` (15 m span, `include_optional_rolled_beam=True` → four catalog alternatives).
2. **Alternative characterization (M4):** Alternatives already carry `characterization_items` from `apply_simple_span_m4_characterization`; test asserts **workflow_heuristic** plus **either retrieval_backed or not_yet_evidenced** (corpus may be empty — structured miss is explicit).
3. **Working-branch materialization:** `TreeWorkspace.materialize_working_branch_for_alternative` for the **castellated** catalog alternative (`catalog_key == "castellated"`).
4. **M5 deterministic preliminary calculation/checks:** `run_simple_span_m5_preliminary` on the materialized branch — one `Calculation` with `method_label == m5_simple_span_preliminary_v1`, two `Check` rows with `calculation_id` pointing at that calculation.
5. **M6 comparison enrichment:** `BranchComparisonService.for_live` compares **main trunk branch** vs **working branch**; working branch row includes `m5_preliminary`, `m5_checks_via_calculation_id`, and `comparison_field_sources` marking deterministic vs other field origins; `citation_trace_authority` remains `internal_trace_only`.
6. **Revision snapshot replay:** `ProjectService.create_revision`, then `BranchComparisonService.for_revision_snapshot` with the same branch id list; comparison rows match live (except `generated_at`), and `load_revision_bundle` contains the same calculation/check ids.

---

## 2. Preliminary vs authoritative output (explicit)

| Artifact / channel | Ready as **internal engineering workflow** output | Ready for **authoritative, evidence-backed** user output | **Internal / preliminary only** (not upgraded) |
|--------------------|-----------------------------------------------------|------------------------------------------------------------|-----------------------------------------------|
| Tree structure, branches, alternatives, M4 `characterization_items` | Yes — persisted, integrity-checked | **Only** items with **retrieval_backed** provenance and valid persisted `Reference` / citation path via `DocumentRetrievalService` | `workflow_heuristic`, `manual_placeholder`, `not_yet_evidenced` (explicitly labeled) |
| `BranchComparisonResult` qualitative columns, tags, M6 metrics | Yes — deterministic given stored tree | Not as normative citations: comparison notes state trade-off review, not code excerpts | `citation_traces` / `reference_ids` in comparison: **document_trace_pending** until Reference resolution product exists |
| M5 `Calculation` / `Check` (method_label slice) | Yes — reproducible, persisted, linked to node | **No** — disclaimer in result: preliminary workflow signal, not design adequacy; empty `reference_ids` on calc/check | Utilization-style fields are **indicators** for workflow sorting, not code-compliant resistance checks |
| `method_label` identification of M5 slice | Yes — stable string `m5_simple_span_preliminary_v1` | N/A | Registry / namespace hardening for methods is **deferred** (see §5) |

---

## 3. Check discovery model (calculation_id)

- **Current behavior:** M6 includes checks in `m5_checks_via_calculation_id` by loading persisted `Check` rows whose `calculation_id` is one of the M5 calculation ids for that branch (see `branch_comparison.py`: filter checks against `m5_calc_ids`).
- **Acceptance for Block 3:** The **full vertical flow is reconstructible and testable**: `Calculation.id` and `Check.calculation_id` are stable in live and revision tree stores; the E2E test asserts revision bundle still loads the same calc/check ids and that snapshot comparison matches live row content for M5 fields.
- **Deferred:** First-class node→check indexing or UI-oriented check listing beyond scan-by-store (optional optimization).

---

## 4. Method identification (`method_label`)

- **Block 3:** The preliminary deterministic slice is identified by **`method_label`** on `Calculation` (`m5_simple_span_preliminary_v1`). This is sufficient for filtering M5 rows in comparison and refusing duplicate M5 runs.
- **Deferred (explicit):** Central **method registry**, namespacing, versioning policy across workflows, and collision avoidance — not solved in Block 3; future milestone should replace or augment string labels without breaking persisted rows.

---

## 5. Intentionally deferred after Block 3

- Full code-compliant member design, all limit states, connection design suite.
- UI / canvas / chat consumers of the same APIs.
- **Reference resolution** for comparison `citation_traces` as user-facing citations.
- OCR, BIM/CAD, exportable formal engineering report product.
- Hardened method registry beyond `method_label` string.
- Direct node-linked check discovery APIs (optional); current scan + `calculation_id` model retained.

---

## 6. Test evidence

| Check | Result |
|-------|--------|
| M7 E2E | `tests/test_block3_vertical_flow.py` — **1 passed** |
| Full suite | `python -m pytest tests/ -q` — **67 passed** (includes Block 2 + Block 3 unit/integration tests) |

---

## 7. Block 3 functional completeness

Against `docs/06_block_3_implementation_plan.md` §H and `docs/07_block_3_acceptance_snapshot.md`:

- **Vertical E2E** — satisfied by M7 test.
- **Calculations/checks in revision snapshots** — satisfied (bundle + snapshot comparison assertions).
- **Normative vs non-normative paths** — M4 demonstrates both retrieval-backed (when corpus hits) and explicit non-evidenced placeholder; E2E asserts provenance set includes workflow heuristic and retrieval or not_yet_evidenced.
- **No regression** — full pytest green.

**Conclusion:** For the **agreed Block 3 foundation scope** (single vertical workflow slice with explicit non-authority boundaries), Block 3 can be treated as **functionally complete**. Further work moves to product/UI, authoritative reporting, and solver depth **outside** this milestone.

---

## Document control

- Supersedes informal “planned only” notes in `07_block_3_acceptance_snapshot.md` for test naming — see test file for exact symbol names.
- Changelog: `docs/CHANGELOG.md` [Unreleased] Block 3 M7 entry.
