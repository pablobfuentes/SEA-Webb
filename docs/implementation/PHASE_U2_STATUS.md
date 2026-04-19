# Phase U2 — Chat-first shell (status)

**Status:** Complete (2026-04-18).

## Scope

- Primary workbench surface: **`GET /workbench/project/chat`** — chat-first layout for the existing local assistant.
- Submission: **`POST /workbench/project/chat/query`** — thin handler; uses **`_local_assist_run` → `LocalAssistOrchestrator`** (same as U1 evidence panel).
- Shared Jinja context via **`_u1_template_context`**; response body uses **`partials/local_assist_result.html`** (answer, authority summary, provenance, warnings, refusals, citations with **`/workbench/project/evidence/fragment/{document_id}/{fragment_id}`** links, deterministic hooks, assumptions).
- Project hub lists **Assistant (U2)** before workflow/evidence/corpus.
- No local LLM runtime, no conversational memory, no U3+ features.

## Tests

- `tests/test_workbench_u2.py` — session gating, empty chat page, hub ordering, successful query, authority/citations structure, governance refusal, `badge auth` vs `badge sup`, fragment navigation from chat HTML, deleted `project.json` session recovery, stable empty page, deterministic hooks disclosure.

## References

- Orchestrator: `services/local_assist_orchestrator.py`
- Contract: `domain/local_assist_contract.py`
- Display helpers: `workbench/u1_evidence_display.py`
