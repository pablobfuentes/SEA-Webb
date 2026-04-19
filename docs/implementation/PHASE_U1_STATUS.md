# Phase U1 — Evidence panel + source-link surface (chat-first trust layer)

**Status:** Implemented (2026-04-18).

## Scope delivered

| Area | Implementation |
|------|----------------|
| Contract | `LocalAssistResponse.normative_retrieval_binding` (`n_a` \| `legacy_allowed_documents` \| `explicit_projection`) populated from retrieval (G4) for UI provenance. |
| Routes | `GET /workbench/project/evidence` — form + optional `err` query; `POST /workbench/project/evidence/query` — runs `LocalAssistOrchestrator`; `GET /workbench/project/evidence/fragment/{document_id}/{fragment_id}` — full fragment text + metadata (read-only). |
| Templates | `evidence_panel.html`, `evidence_source_view.html` (citation source: original file + fragment); hub link to evidence panel. |
| View helpers | `workbench/u1_evidence_display.py` — provenance headline, citation badges, governance refusal styling helper (labels only). |

## Product rules

- No retrieval logic in templates; orchestrator + `DocumentRetrievalService` remain the only corpus path.
- Authority lanes visually separated: normative (legacy vs explicit projection), approved ingested, assumptions, deterministic hooks, refusals (including governance blocks).
- Source navigation: fragment route shows exact persisted fragment text (not IDs alone).

## Out of scope (U2+)

Full chat thread, conversational memory UI, local LLM runtime, governance dashboard, polished design system.
