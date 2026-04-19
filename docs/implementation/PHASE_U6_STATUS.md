# Phase U6 — Secondary tree/workflow integration

**Status:** Implemented (2026-04-19)

## Intent

Expose existing Block 3 / 4A **simple-span workflow** (branches, materialization, M5, M6 comparison, revisions) as a **secondary trace surface**, reachable from chat, evidence, and canvas without recentering the product on the tree.

## Delivered

- **Partials:** `u6_secondary_to_workflow.html` (entry strip from primary pages), `u6_primary_surfaces_nav.html` (return strip on workflow/corpus).
- **Primary pages:** Chat, evidence, canvas include the secondary strip and label workflow link “(secondary)”.
- **Workflow:** `simple_span_workflow.html` — block heading notes “secondary trace”; body opens with explicit **Secondary surface** paragraph + primary-surfaces nav.
- **Hub:** Session block lists **Primary surfaces** (chat, evidence, canvas) before **Secondary — trace & workflow** (workflow, corpus).
- **Corpus:** Primary-surfaces nav + one-line note that ingestion is not primary Q&A.

## Context handoff

- **Project/session:** Unchanged — all links rely on existing session `project_id` (no new query-string protocol).
- **Canvas query:** Not passed to workflow (out of scope for thin U6); users return via primary nav.

## Not done (later)

- Multi-pane shell, tree as home, session “last query” bridging to workflow.
