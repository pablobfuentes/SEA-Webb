# Test strategy — structural_tree_app_foundation

This document applies to **Block 2** and subsequent local-first core work. It aligns with `docs/04_block_2_implementation_plan.md`, `docs/03_mvp_scope.md`, and ADR-001.

**Product rebaseline (2026-04-18):** Primary UX targets **chat + evidence-backed citations + logic/audit panels**; the tree is **secondary**. Existing tests that exercise **tree persistence, retrieval, and Block 3 vertical flow** remain **required** for regression. New work should add **citation/assertion tests** for chat/orchestration paths when implemented. See `docs/11_product_rebaseline_local_ai_chat_first.md`, `docs/12_revised_execution_order_after_rebaseline.md`.

**Phase R1 (2026-04-18):** `tests/test_local_assist_r1.py` covers `LocalAssistOrchestrator` — approved-corpus-only retrieval path, insufficient-evidence refusal, citation dict completeness, normative vs supporting authority classes, deterministic M5 hooks separate from citations, stable `local_assist_response_to_dict` serialization, project missing / empty query / overlong query, assumptions with non-citation authority note, proof orchestrator does not write workspace files.

**Phase G0 (2026-04-18):** `tests/test_governance_g0.py` — governance enums/codecs round-trip, deterministic serialization, `GovernanceStore` persistence for active knowledge projection, document governance index, governance event log, JSON Schema validation failures, backward compatibility when `governance/` is absent, partial-file guard, `initialize_governance_baseline` idempotency, `governance/` directory created with new projects. Does **not** assert retrieval/orchestrator behavior (deferred until G4+ wiring).

**Phase G1 (2026-04-18):** `tests/test_governance_g1.py` — governance records/events after ingest, analyzed vs classified terminal stages, explicit `promote_document_to_classified`, classification snapshot persistence + deterministic index JSON, schema validation errors on bad index, first ingest initializes governance baseline, **retrieval behavior unchanged** (`test_retrieval_behavior_unchanged_from_g1_ingest` mirrors normative corpus search).

**Phase G2 (2026-04-18):** `tests/test_governance_g2.py` — duplicate candidate (reingest same bytes), narrow deterministic cases for supersession / supporting / contradiction + overlap, assessment persistence + stable JSON, schema validation failure on bad file, projects without assessment files, first-document empty corpus, **retrieval unchanged** after G2 ingest (`test_retrieval_unchanged_after_g2_ingest`).

**Phase G3 (2026-04-18):** `tests/test_governance_g3.py` — duplicate proposal → approve updates excluded list + `g3.1` projection; contradiction proposal marks both documents **conflicting_unresolved**; stale index blocks approve; reject leaves projection lists unchanged; deterministic `truth_proposal_to_dict` JSON; missing proposal file returns `None`; **retrieval unchanged** after approval (`test_retrieval_unchanged_after_truth_proposal_approval`) when binding stays legacy (G3 default).

**Phase G4 (2026-04-18):** `tests/test_governance_g4.py` — explicit **`explicit_projection`** binding uses only governed authoritative ids for normative retrieval (not `allowed_document_ids`); legacy default unchanged; `conflicting_unresolved` / missing index / empty authoritative refusal; `approved_ingested` distinct from normative explicit path; `LocalAssistOrchestrator` refusal codes + warnings; stable governance warning lines.

**Phase U1 (2026-04-18):** `tests/test_workbench_u1.py` — workbench evidence panel (session project required), POST assist renders citations + provenance; legacy vs explicit projection visible in HTML; governance conflict refusal surfaced; fragment detail route returns full source text; deterministic hooks section distinguished from citations; missing session redirects to hub.

**Phase G1.5 / U0 (2026-04-18):** `tests/test_workbench_corpus_bootstrap.py` — corpus bootstrap page session gating; multipart upload → `ingested`; duplicate → `duplicate_skipped`; unsupported extension → `unsupported_document_for_ingestion`; blank PDF → `ocr_deferred`; document detail + manual bootstrap actions (authoritative / supporting / pending_review); projection binding + legacy allow-list sync; `LocalAssistOrchestrator` after explicit projection + approved primary standard doc; deleted project session handling; `CorpusBootstrapError` on missing governance record.

**Corpus readiness bridge (2026-04-18):** `tests/test_corpus_readiness_bridge.py` — `evaluate_document_readiness` unit cases (approval, primary classification, family mismatch, legacy allow-list, explicit projection membership / not-in-projection); evidence hint HTML for governance vs insufficient; HTTP detail shows readiness labels; E2E approve + metadata + bootstrap + sync → normative `LocalAssistOrchestrator` hit; evidence panel `readiness-hint` on insufficient query; unknown document redirects.

**Governance + active truth (beyond G0):** Remaining gaps include **audit log immutability** tests and richer disposition transition coverage — see `docs/13_document_governance_and_active_truth_rebaseline.md`, `docs/14_detailed_revised_execution_order_with_governed_knowledge.md`. Existing tree and retrieval tests remain regression anchors.

---

## 1. Principles

| Principle | Testing implication |
|-----------|---------------------|
| **Tree-first** | Integration tests anchor on project + tree persistence, not on document or chat convenience APIs alone. *(Rebaseline: tree remains **integration-critical**; **chat/citation-first** features need parallel tests when added.)* |
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

### 2.4 End-to-end (Block 3)

**Implemented (M7):** `tests/test_block3_vertical_flow.py` — single scenario: simple-span workflow (four alternatives with optional rolled) → M4 characterization (provenance) → materialized working branch for **castellated** → M5 preliminary **Calculation** / **Check** → M6 **BranchComparisonService** (live) → `create_revision` → comparison replay via `for_revision_snapshot` with equivalent M5 rows (excluding `generated_at`). Planning: `docs/06_block_3_implementation_plan.md`. Acceptance + boundaries: `docs/07_block_3_acceptance_snapshot.md`, `docs/08_block_3_validation_report.md`.

**M2 done:** persistence, codecs, schema validation, revision snapshot compatibility, and integrity checks for **Calculation** / **Check** / **Reference** are covered by `tests/test_tree_calculation_check_persistence.py`.

**M3.1 done:** catalog-driven simple-span workflow alternatives (eligibility + deterministic ranking + top-3 suggestion marking, all eligible persisted, branch-origin alternative integrity) are covered by `tests/test_simple_span_steel_workflow_m3.py` (still not M4–M7 characterization, calcs, or comparison enrichment).

**M5 done:** `tests/test_simple_span_m5_preliminary.py` — materialized branch → preliminary M5 run → Calculation + Checks + assumptions persisted and reloaded; revision bundle replay; stable `calculation_to_dict` / `check_to_dict` JSON ordering; rejects trunk-only branch and duplicate M5; unsupported `catalog_key`; characterization items unchanged; empty reference ids and explicit non-retrieval authority flags.

**M6 done:** `tests/test_branch_comparison.py` now covers explicit M5 comparison projection (`m5_preliminary`) and check discoverability via `calculation_id` (`m5_checks_via_calculation_id`), plus source classification (`comparison_field_sources`) separating deterministic preliminary signals from branch/tree-derived, manual-placeholder, and document-trace-pending fields. It also verifies discarded and non-selected branches remain comparable in the same output.

### 2.5 Block 4A — Minimum validation workbench

Block 4A adds a **thin local frontend** (see `docs/09_block_4a_implementation_plan.md`) to drive the **frozen Block 3** APIs through real interactions. **Not** the final product UI.

**M2 done:** FastAPI + Jinja2 shell — `tests/test_workbench_m2.py` (`/health`, `/workbench`, workspace env). Run: `python -m structural_tree_app.workbench` after `pip install -e ".[dev,workbench]"`.

**M3 done:** Project hub + simple-span workflow — `tests/test_workbench_m3.py` (session `project_id`, `POST` workflow → persisted snapshot). Same install extra; optional `WORKBENCH_SESSION_SECRET` for signed session cookies.

**M4 done:** Alternatives + characterization inspection — `tests/test_workbench_m4.py` (provenance constants, suggestion sections).

**M5 done (workbench):** `tests/test_workbench_m5.py` — `POST /workbench/project/workflow/materialize` + `POST .../m5-run` drive `TreeWorkspace.materialize_working_branch_for_alternative` and `run_simple_span_m5_preliminary`; duplicate M5 error surfaced; persisted calc/check HTML; `simple_span_workflow_input.json` required (written on M3 setup).

**M6 done (workbench):** `tests/test_workbench_m6.py` — `POST /workbench/project/workflow/compare` calls `BranchComparisonService` (live or `for_revision_snapshot` via hidden `context_revision_id`); `POST .../revision-create` + `?rev=` replay; last comparison persisted in `workbench_m6_last_comparison.json`; read-only proof (branch JSON unchanged); unknown revision query errors.

**Windows dev launcher (optional):** `run_workbench.bat` or `scripts/run_workbench.ps1` — requires a local `.venv` with `pip install -e ".[dev,workbench]"`; sets default `STRUCTURAL_TREE_WORKSPACE` to `<repo>/workspace` and can pass `-Reload` for uvicorn autoreload (`WORKBENCH_RELOAD=1`). Same automated tests (`test_workbench_m*.py`) and manual smoke: `GET /health`, `GET /workbench`.

**Planned validation (M3+)**

- HTTP/route-level tests (`TestClient`) for create project → simple-span workflow → materialize → M5 → M6 → revision replay, mirroring `tests/test_block3_vertical_flow.py` where possible.
- Assertions that response bodies include mandatory **authority / preliminary / internal-trace** labeling strings (see plan §G).
- Manual checklist: `docs/10_block_4a_acceptance_snapshot.md` §3.
- Tracker: `docs/implementation/BLOCK_4A_STATUS.md`.

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
