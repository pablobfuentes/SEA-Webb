# Phase U4 — Logic / formulas / assumptions / checks panel (status)

**Status:** Complete (2026-04-19).

## Scope

- **Goal:** Auditable transparency for persisted deterministic and assumption artifacts, separate from governed document retrieval/citations.
- **Loader:** `workbench/u4_logic_audit.py` — `load_project_logic_audit_snapshot` reads `ProjectService.load_assumptions` and `TreeStore` calculations/checks (no solver logic).
- **UI:** `workbench/templates/partials/u4_logic_audit_panel.html` included at the bottom of `chat_shell.html` and `evidence_panel.html` after the assist block (when present).
- **Boundaries:** Copy states document evidence lives in the retrieval response; U4 lists tree/project persistence only. M5 preliminary rows tagged via `method_label ==` `simple_span_m5_service.METHOD_LABEL`. Disclaimer: preliminary signals are not code-compliant design, not final adequacy, not normative citations.
- **Navigation:** Link to `/workbench/project/workflow` for workflow/M5 materialization context.

## Deferred (not U4)

- Formula canvas, sketches, multi-step derivation UI (U5+).
- Governance dashboard, report export.
- New calculation engines or Block 3 storage redesign.

## Tests

- `tests/test_workbench_u4.py` — empty state, populated assumptions/calculations/checks, M5 badge + disclaimer, deterministic badges vs citation badges, coexistence with retrieval response, no session redirect.

## References

- `workbench/u4_logic_audit.py`, `workbench/m5_workbench_view.py` (display dict reuse)
- `workbench/pages.py` (`_u1_template_context` passes `u4_logic_audit`)
- `storage/tree_store.py`, `services/project_service.py` (assumptions)
