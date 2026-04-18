# Block 4A — Acceptance snapshot (planning)

**Purpose:** Define what “Block 4A complete” means for the **minimum validation workbench** frontend, aligned with `docs/09_block_4a_implementation_plan.md`.  
**Status:** Planning baseline — fill in exact commands, routes, and test names when implementation exists.  
**Depends on:** Block 3 frozen baseline — `docs/08_block_3_validation_report.md`, `docs/implementation/BLOCK_3_STATUS.md`.

---

## 1. Product outcome

After Block 4A, a user can run a **local validation workbench** that:

- Exercises the **Block 3 vertical flow** through **UI interactions** (not only pytest).  
- Makes the **decision tree, alternatives, branches, M5 artifacts, M6 comparison, and revision replay** observable.  
- Preserves **retrieval as authority gate**, **deterministic M5 separate from any LLM**, and **clear labeling** of preliminary vs authoritative content.

---

## 2. Technical acceptance checks

| # | Criterion | Verification |
|---|-------------|--------------|
| A | Workbench starts with **documented command** | README or `docs/09` §D |
| B | **13 capabilities** (product brief) demonstrable | Manual checklist §4 |
| C | **Provenance** visible per characterization item | Visual/badge + raw value |
| D | **M5** shown as **preliminary** (never as final adequacy) | Banner + `method_label` visible |
| E | **M6** shows `citation_trace_authority` and field sources | Legend or raw JSON panel |
| F | **Revision replay** observable | Snapshot comparison or read-only tree from revision |
| G | **Backend regression** | `python -m pytest tests/ -q` green (existing suite) |
| H | **New automated tests** for workbench | `tests/test_workbench_*.py` or equivalent — **TBD** |

---

## 3. Example manual checklist (to run after implementation)

**Preconditions:** Python 3.11+, dependencies installed including workbench extras.

1. Set workspace env var if non-default.  
2. Start workbench server (exact command **TBD**).  
3. Create a new project; note `project_id`.  
4. Enter simple-span inputs (include optional rolled if four alternatives desired); run workflow setup.  
5. Confirm root node id and decision id appear.  
6. Confirm four (or three) alternatives listed; top-3 suggestions marked.  
7. Open one alternative; confirm characterization items + provenance classes.  
8. Materialize working branch for **castellated** (or any) alternative; confirm new branch id.  
9. Run M5; confirm one Calculation and two Checks linked; disclaimers visible.  
10. Run M6 for trunk + working branch; confirm `internal_trace_only` messaging.  
11. Create revision.  
12. Switch to snapshot context; re-run comparison; confirm parity with expectations from `test_block3_vertical_flow.py`.

---

## 4. Explicit non-goals (must remain false at Block 4A close)

- [ ] Production-polished UI  
- [ ] Full graph/canvas editor  
- [ ] NL chat design assistant  
- [ ] Full report export  
- [ ] Block 3 semantic redesign  

---

## 5. Documentation deliverables at Block 4A close

- [ ] `docs/implementation/BLOCK_4A_STATUS.md` — milestone table complete  
- [ ] `docs/CHANGELOG.md` — Block 4A entry  
- [ ] `docs/TEST_STRATEGY.md` — workbench test section updated with real paths  
- [ ] `README.md` — run instructions for workbench  

---

## 6. Traceability to Block 3 E2E

The automated backend reference remains:

- `tests/test_block3_vertical_flow.py::test_block3_m7_vertical_e2e_simple_span_castellated_m5_m6_revision_replay`

Block 4A should provide a **human-repeatable** path that mirrors this narrative (workspace UI instead of code).

---

**Last updated:** 2026-04-18 (planning phase).
