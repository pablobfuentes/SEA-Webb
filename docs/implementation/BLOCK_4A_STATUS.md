# Block 4A — Status tracker

Single source of truth for Block 4A (minimum validation workbench) in `structural_tree_app_foundation`.  
Planning: `docs/09_block_4a_implementation_plan.md` · Acceptance: `docs/10_block_4a_acceptance_snapshot.md`

**Dependency:** **Block 3 is frozen** as the backend/domain baseline (`docs/implementation/BLOCK_3_STATUS.md`, `docs/08_block_3_validation_report.md`). Block 4A adds UI only; backend changes only for justified bugfixes.

| Milestone | Status | Notes |
|-----------|--------|-------|
| 4A-M1 — Baseline + UI boundary | Pending | — |
| 4A-M2 — App shell + stack | **Complete** | FastAPI + Jinja2; `structural_tree_app.workbench`; `/health`, `/`→`/workbench`, workspace env; tests: `tests/test_workbench_m2.py` |
| 4A-M3 — Project / simple-span workflow (M3) | **Complete** | Session pointer `project_id`; create/open/close; `GET|POST /workbench/project/workflow`; `SimpleSpanSteelWorkflowService.setup_initial_workflow`; snapshot via `workflow_summary`; tests: `tests/test_workbench_m3.py` |
| 4A-M4 — Workflow input + M3/M4 trigger | Pending | — |
| 4A-M5 — Branches, alternatives, characterization | Pending | — |
| 4A-M6 — Materialize + M5 panels | Pending | — |
| 4A-M7 — M6 comparison + revision replay + E2E | Pending | — |

**Last updated:** Block 4A M3 (project hub + simple-span workflow setup UI).
