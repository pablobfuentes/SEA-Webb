# Phase U5 — Visual case canvas (reasoning-bridge surface)

**Status:** Implemented (2026-04-19)

## Scope

- **Route:** `GET /workbench/project/canvas?q=…` — case-scoped board; calls `ReasoningBridgeService.analyze(ReasoningBridgeRequest(...))` with the same retrieval-oriented defaults as R2B tests (normative primary, deterministic context on).
- **Empty state:** `GET` without `q` (or blank `q`) shows a GET form to load the board; no bridge run.
- **View model:** `workbench/u5_canvas_view.py` — `u5_canvas_board_from_result` maps `ReasoningBridgeResult` to plain dicts for Jinja (tier CSS classes, fragment URLs, scope classes). **No** duplicated interpretation logic.
- **Template:** `workbench/templates/canvas_u5.html` — lanes/cards for interpretation, process steps, formula/check candidates (supported vs recognized vs gap), deterministic execution steps (explicitly “not normative evidence”), gaps, flat anchor list; U4 logic/audit partial included for cross-surface audit path.
- **Navigation:** Chat (U2) and evidence (U1) include `u5_canvas_href` (query-prefilled when `form_query` non-empty); project hub links to canvas.

## Boundaries

- Governed fragments remain authority; bridge disclaimer rendered on the canvas.
- Derived anchors labeled `(derived)` vs `(retrieval)`; formula rows carry `non_authoritative` when set by R2B.
- Deferred original-source page UX unchanged — fragment links preserve the path toward full document viewing (`docs/implementation/DEFERRED_EVIDENCE_UX.md`).

## Tests

- `tests/test_workbench_u5.py`

## Not in scope (U6+)

- Symbolic math renderer, CAD/BIM, general whiteboard, automatic diagram generation from arbitrary problems, retrieval/governance/reasoning-bridge redesign.
