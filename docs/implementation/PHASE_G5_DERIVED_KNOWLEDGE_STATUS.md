# Phase G5 — Derived knowledge layer (status)

**Label:** G5 (derived knowledge; optional “R2C” naming in planning docs).  
**Scope:** Backend/domain/persistence only — **no** U5 reasoning bridge, **no** retrieval/orchestrator wiring by default.

## Delivered

- **Persistence:** `{project_id}/derived_knowledge/bundle.json` (JSON Schema `derived_knowledge_bundle.schema.json`).
- **Service:** `DerivedKnowledgeService.regenerate(project_id)` — deterministic artifacts, SHA-256 `source_fingerprint`, monotonic `bundle_version` when fingerprint changes, no-op when fingerprint unchanged (loads existing bundle).
- **Artifacts (non-authoritative):** document digests, topic digests, navigation hints, formula/check registry (recognition + optional `deterministic_m5_hook` when M5 label appears in fragment text), governance signals for conflicting/superseded dispositions.
- **Linkage:** each digest/registry row uses `SourceAnchorRef` (`document_id`, `fragment_id`, document + fragment content hashes, governance disposition + normative classification where known).

## Not in this phase

- Consumption by chat, retrieval, or local model (explicitly deferred).
- LLM-based summarization (generation mode is `deterministic_v1` only).

## References

- `docs/CHANGELOG.md` — G5 entry.
- Tests: `tests/test_derived_knowledge_g5.py`.
