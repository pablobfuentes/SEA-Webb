# Failure log (structural_tree_app_foundation)

Record failures during Block 2 **execution** (implementation milestones). Each entry should include: date, symptom, root cause, reproduction steps, fix or deferral, and link to changelog if applicable.

Planning-only steps that produce no runtime code may have no entries.

---

## Template

| Field | Description |
|-------|-------------|
| **Date** | ISO date |
| **Milestone** | e.g. M3 — tree expansion |
| **Failure** | What broke or failed |
| **Root cause** | Why it happened |
| **Reproduction** | Numbered steps |
| **Fix attempt** | What was tried |
| **Status** | open / fixed / deferred |

---

## Entries

### 2026-04-14 — M6 comparison fields missing for M5

| Field | Description |
|-------|-------------|
| **Date** | 2026-04-14 |
| **Milestone** | M6 — Branch comparison enriched |
| **Failure** | New tests expected M5-aware fields (`m5_preliminary`, `m5_checks_via_calculation_id`, `comparison_field_sources`) on `BranchComparisonRow`, but service returned rows without these attributes. |
| **Root cause** | Comparison model/service had not yet been extended for M6; tests were added first (TDD red) and correctly failed with `AttributeError`. |
| **Reproduction** | 1) `python -m pytest tests/test_branch_comparison.py -q` 2) Observe failures in `test_m6_m5_signals_and_sources_are_explicit` and `test_m6_discarded_and_non_selected_branches_still_comparable`. |
| **Fix attempt** | Extend branch comparison schema and row construction to include explicit M5 preliminary payload + check discovery path and field-source classification. |
| **Status** | fixed |
