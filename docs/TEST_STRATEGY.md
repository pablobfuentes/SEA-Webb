# Test strategy — structural_tree_app_foundation

This document applies to **Block 2** and subsequent local-first core work. It aligns with `docs/04_block_2_implementation_plan.md`, `docs/03_mvp_scope.md`, and ADR-001.

---

## 1. Principles

| Principle | Testing implication |
|-----------|---------------------|
| **Tree-first** | Integration tests anchor on project + tree persistence, not on document or chat convenience APIs alone. |
| **Document-first / citation-first** | Assertions require **citation payloads** (document id, chunk/fragment id, excerpt fields) for any “evidence” result; “no evidence” must be a **structured** outcome, not an empty string. |
| **Deterministic vs LLM** | Unit tests cover calculation and pure domain logic **without** network or LLM. If a future LLM layer exists, it is mocked or behind interfaces not invoked in default CI paths for core contracts. |
| **Normativa activa** | Retrieval tests **must** include cases where inactive or non-allowed standards are excluded when the project context forbids them. |
| **Discarded branches** | Tests cover discard, reopen, and comparison including **discarded** branches. |

---

## 2. Test levels

### 2.1 Unit tests

- **Domain:** `domain/models.py`, enums, ID generation, invariants (where pure).
- **Services:** `project_service`, `tree_service`, `document_service`, retrieval/comparison services as added — with temporary directories or `tmp_path` fixtures.
- **Repository:** JSON read/write, schema validation failures, atomicity expectations (document best-effort; full transactional FS not assumed).

### 2.2 Integration tests

- **Document ingestion (M4):** Block 2 supports **text-extractable PDFs** only; **no OCR**. Tests must assert a **structured status** (e.g. `unsupported_document_for_ingestion` / `ocr_deferred`) when a PDF has no extractable text, never silent empty ingest.
- **Project lifecycle:** create → load → save → create revision → list revisions → load revision.
- **Tree lifecycle:** root → expand → discard branch → reopen → clone; persistence reload.
- **Ingestion:** register document → chunks persisted → deterministic duplicate handling.
- **Retrieval:** query corpus → filtered by `ActiveCodeContext` / `document_id` → citation shape validated.
- **Comparison:** ≥2 branches → stable JSON-serializable comparison object.

### 2.3 End-to-end (Block 2 closure)

Per `cursor_prompts/08_validation_and_integration_prompt.txt`: one scripted flow using repository artifacts (example project or fixture workspace) covering M2–M6 behaviors in sequence; results summarized in `docs/05_block_2_validation_report.md` (created at M7).

**Implemented:** `tests/test_block2_integration.py` — project → tree → ingest → approve/activate → retrieval → revision snapshot → branch comparison (live vs `for_revision_snapshot`) + deterministic branch ordering check.

---

## 3. Determinism & fixtures

- Prefer **fixed seeds** or static JSON fixtures under `examples/` or `tests/fixtures/`.
- PDF/text ingestion tests: commit **small** synthetic files (plain text or minimal PDF) to avoid flaky external binaries unless documented.
- OCR: **not** part of Block 2; a future block may introduce optional OCR tests and fixtures.

---

## 4. Visual / UI testing

- **Block 2 core:** no GUI requirement. “Rendered product” parity is deferred until a UI milestone; substitute **exported JSON / reports** and structured citation objects as evidence.
- When a desktop/UI layer lands: add visual regression or manual checklist per product owner; responsive breakpoints per `workflow/Prompt.md` for that layer only.

---

## 5. CI / local commands

- Target runner: `pytest` from repository root once `pyproject.toml` or test layout is added (see M1 governance prompt).
- Minimum bar before closing Block 2: all tests green locally (and in CI if configured in M1).

---

## 6. Failure handling

- Any test failure during implementation is logged in `docs/FAIL_LOG.md` with root cause and fix/deferral.
- Flaky tests: quarantine with issue reference; do not silently retry without documentation.

---

## 7. Persistence — remaining test debt (explicit backlog)

Implemented hardening tracks (revision write-once, revision bundle isolation, tree integrity helper) are summarized in `docs/implementation/PERSISTENCE_HARDENING.md`.

The following cases are **not yet** fully covered by automated tests and should be added or extended before treating persistence as “hardened”:

| Case | Intent |
|------|--------|
| Missing files | Load/save when `project.json`, `assumptions.json`, or a `tree/**/*.json` file is absent or renamed mid-operation. |
| Malformed JSON | Non-JSON or truncated files under project or revision paths raise `ProjectPersistenceError` with clear context. |
| Schema-invalid JSON | Payloads that parse as JSON but fail `additionalProperties` / required fields / enums are rejected at load and on save. |
| Revision immutability | Writing to `revisions/{id}/` after creation is either prevented or documented; snapshots are not silently overwritten without a new revision id. |
| Assumptions snapshot consistency | `assumptions_snapshot.json` in a revision matches the assumptions file at revision creation time (ordering/id set). |
| Duplicate IDs | Conflicting branch/node/decision/alternative ids are detected or rejected deterministically. |

*Aligned with Block 2 planning; update this file when tooling or scope changes.*
