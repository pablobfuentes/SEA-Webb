# Block 4A — Status tracker

Single source of truth for Block 4A (minimum validation workbench) in `structural_tree_app_foundation`.  
Planning: `docs/09_block_4a_implementation_plan.md` · Acceptance: `docs/10_block_4a_acceptance_snapshot.md`

**Product rebaseline (2026-04-18):** Primary product narrative is **chat-first local AI + mandatory evidence/citation and audit panels**; the **alternatives tree** is **secondary** (exploration/traceability). See **`docs/11_product_rebaseline_local_ai_chat_first.md`** and **`docs/12_revised_execution_order_after_rebaseline.md`**. Block 4A M1–M6 remain **valid** as a thin **validation / secondary exploration** UI — not the long-term main surface. **4A-M7 is strategically paused/demoted** until chat-first phases (doc 12: R1–R3+) are underway; optional small workbench fixes still allowed.

**Roadmap extension (2026-04-18):** **Document governance + active operational truth** is **mandatory** product architecture. See **`docs/13_document_governance_and_active_truth_rebaseline.md`** and phased execution **`docs/14_detailed_revised_execution_order_with_governed_knowledge.md`**. Workbench remains **secondary**; do not implement governance in the workbench shell—primary governance UI is **U-track** in doc 14.

**Dependency:** **Block 3 is frozen** as the backend/domain baseline (`docs/implementation/BLOCK_3_STATUS.md`, `docs/08_block_3_validation_report.md`). Block 4A adds UI only; backend changes only for justified bugfixes.

**Execution order (4A-M2 onward):** M2 app shell → **M3** project/session + simple-span workflow **setup** → **M4** alternatives inspection → **M5** materialize working branch + M5 preliminary run + persisted calc/check display → **M6** comparison + revision snapshot UI → ~~**M7** E2E / reporting polish~~ **on hold (rebaseline)** — see doc 12.

| Milestone | Status | Notes |
|-----------|--------|-------|
| 4A-M1 — Baseline + UI boundary | Pending | — |
| 4A-M2 — App shell + stack | **Complete** | FastAPI + Jinja2; `structural_tree_app.workbench`; `/health`, `/`→`/workbench`, workspace env; tests: `tests/test_workbench_m2.py` |
| 4A-M3 — Project + simple-span workflow setup | **Complete** | Session pointer `project_id`; create/open/close; `GET|POST /workbench/project/workflow`; `SimpleSpanSteelWorkflowService.setup_initial_workflow`; tests: `tests/test_workbench_m3.py` |
| 4A-M4 — Alternatives & characterization inspection | **Complete** | Rich snapshot (`workflow_summary`); suggested vs eligible sections; characterization rows + provenance legend; `provenance_display`; tests: `tests/test_workbench_m4.py` |
| 4A-M5 — Materialize + M5 preliminary UI | **Complete** | `POST .../materialize`, `POST .../m5-run`; `simple_span_workflow_input.json` persisted at M3 setup for M5 inputs; `m5_workbench_view`; duplicate M5 refused surfaced; tests: `tests/test_workbench_m5.py` |
| 4A-M6 — M6 comparison + revision snapshot UI | **Complete** | `POST .../compare`, `POST .../revision-create`; `?rev=` revision-backed view; `workbench_m6_last_comparison.json` (last result; avoids cookie size limits); tests: `tests/test_workbench_m6.py` |
| 4A-M7 — E2E workbench / acceptance hardening | **Paused / demoted** | Rebaseline: defer product-level polish until chat-first + evidence UI (see `docs/12_revised_execution_order_after_rebaseline.md`); dev fixes optional |

**Last updated:** Product rebaseline 2026-04-18 (docs 11–12); Block 4A M1–M6 complete; M7 on hold.
