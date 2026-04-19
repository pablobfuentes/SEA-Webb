# Phase U3 — Local AI integration layer (status)

**Status:** Complete (2026-04-18).

## Scope

- **Boundary:** `services/local_model_synthesis.py` — `LocalModelSynthesisPort`, `StubLocalModelSynthesizer` (deterministic, no network), `UnavailableLocalModelSynthesizer` (fallback tests).
- **Config:** `services/local_model_config.py` — `STRUCTURAL_LOCAL_MODEL_ENABLED`, `STRUCTURAL_LOCAL_MODEL_PROVIDER` (`stub` | `unavailable`).
- **Orchestrator:** `LocalAssistOrchestrator` accepts optional `runtime_config` and `synthesis_adapter` injection; after governed retrieval success, **optionally** replaces **only** `answer_text` when global enablement **and** `LocalAssistQuery.request_local_model_synthesis` are true. Citations, evidence slots, refusals, hooks, assumptions are unchanged.
- **Contract:** `LocalAssistQuery.request_local_model_synthesis`; `ResponseAuthoritySummary.local_model_synthesis_bounded` when synthesis applied.
- **Workbench:** Dedicated partial `u3_synthesis_control.html` — per-request checkbox `request_local_model_synthesis` is always shown on chat and evidence forms (disabled when server-side U3 is off; enabled when on). Handlers pass through to `LocalAssistQuery`.

## Deferred (not U3)

- Full local LLM runtime (Ollama, etc.) — adapter hook exists; default **stub** proves wiring.
- **Original PDF/page evidence viewer with highlight** — see `docs/implementation/DEFERRED_EVIDENCE_UX.md`.

## Tests

- `tests/test_local_assist_u3.py` — disabled path, stub path, refusal, governance block, authority classes, hooks vs citations, unavailable fallback, injection override, assumptions unchanged.
- `tests/test_workbench_u3.py` — control visibility, disabled vs enabled server states, POST passthrough, assist provenance/citations unchanged.

## References

- `services/local_assist_orchestrator.py`
- `domain/local_assist_contract.py`
- `workbench/pages.py`, `workbench/templates/chat_shell.html`, `evidence_panel.html`
