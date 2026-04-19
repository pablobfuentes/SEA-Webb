# Phase — Integrated case flow hardening

**Status:** Implemented (2026-04-19)

## Intent

Improve **continuity** across chat, evidence, logic/audit (via evidence + chat), canvas, workflow (secondary), and corpus so one **project/case** session feels coherent—without changing retrieval, governance authority, or adding a new major surface.

## Delivered

- **Session + URL handoff:** `SESSION_LAST_ASSIST_QUERY_KEY` stores the last successful assist query; GET on chat, evidence, and canvas can prefill via `?q=` (explicit URL wins over session). POST assist runs sync session from explicit `q` when present.
- **Helpers:** `workbench/case_flow_handoff.py` — `surface_href`, `build_case_nav`, `store_last_assist_query`, `resolve_prefill_query`, `sync_session_query_from_explicit_url`, `invalidate_session_project`, `bind_new_session_project` (new project / open / close clears or resets handoff safely).
- **Navigation:** Shared partial `partials/case_flow_primary_nav.html` (hub, chat, evidence, canvas, corpus, workflow) appends `?q=` when the current assist query is non-empty; short disclaimer that links carry the **same typed query** for continuity—not a new interpretation.
- **Templates:** Primary surfaces and workflow/corpus/evidence source view use the shared nav; workflow return links preserve `q` when set. Canvas empty state prefills `query_text` from session/`q`.
- **Corpus:** List page includes `case_nav` for return continuity.

## Explicit non-goals (this phase)

- Long-term conversation memory, agent architecture, new calculation engines, governance dashboard expansion, or redesign of retrieval/projection.

## Tests

- `tests/test_integrated_case_flow.py` — POST→GET session prefill; `?q=` override; workflow chat link includes query; new project clears stale query; no-session 303 on primary surfaces; unit checks on `surface_href` / `build_case_nav`.
- `tests/test_workbench_u6.py` — updated assertions for `case-flow-primary-nav` (replaces legacy `u6-primary-nav` class on workflow/corpus).

## Residual tensions

- **Workflow canvas query:** U6 still does not auto-run the tree from canvas query; continuity is **link + session query** only, not deep workflow integration.
- **Dual source of truth:** Users can still type a different query on each surface; session stores the **last successful** assist submission only.
