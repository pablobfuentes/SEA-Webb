# Changelog

All notable changes to the **structural_tree_app_foundation** repository are documented here.  
(Block 2 planning entries are foundation-only; they are not mirrored to the parent monorepo `workflow/` logs unless explicitly requested.)

## [Unreleased]

### M7 — Validation & integration (`cursor_prompts/08`)

**Rationale**

- Close Block 2 by proving M2–M6 work together: project/revision persistence, tree, ingestion, retrieval with citations, branch comparison (live + revision snapshot), deterministic ordering.

**M7 report (explicit)**

- **a) End-to-end scenario:** Documented in `docs/05_block_2_validation_report.md` — project → tree (two branches) → ingest → approve/activate → `normative_active_primary` retrieval → `create_revision` → `BranchComparisonService.for_live` and `for_revision_snapshot` (`tests/test_block2_integration.py`).
- **b) Internal vs authoritative:** Retrieval + `CitationPayload` remains the **authoritative** path for evidence-backed output. Branch comparison metrics/provenance are **engineering comparison v1**. `citation_traces` with `resolution_status="ids_only"` and `citation_trace_authority="internal_trace_only"` are **not** full authoritative citations (see validation report §2(b)).
- **c) Deferred after Block 2:** UI/visual tree; OCR; full Reference resolution for traces; richer retrieval tie-breaking; optional “compare two revisions” / golden regression workflows — listed in the validation report §2(c).

**Constraints (non-blocking, explicit in report)**

- Citation traces vs authoritative citations; reproducibility via revision snapshots + follow-ups; `metric_provenance`; deterministic ordering for branches, rows, and `to_dict()` serialization.

**Added**

- `tests/test_block2_integration.py` — integrated flow + deterministic ordering test.
- `docs/05_block_2_validation_report.md`.

**Changed**

- `README.md` — Block 2 completion note and realistic walkthrough.

**Verification**

- `python -m pytest tests/ -q` — 34 passed.

### M6 — Branch comparison v1 (`cursor_prompts/07`)

**Rationale**

- Compare two or more branches as structured decision alternatives without mutating branch state; support discarded branches side-by-side with active ones.

**Product rules (carry forward)**

- Any future answer or explanation layer must consume **only** `RetrievalResponse` + `CitationPayload` from `DocumentRetrievalService`, not raw corpus text.
- Design-authoritative paths keep default **normative_active_primary** unless explicitly overridden for audit/support views.

**M6 report (explicit)**

- **a) Criteria storage:** Metrics are read from persisted tree data under `tree/` (`Branch`, `Node`, `Decision`, `Alternative` via `TreeStore`) and from `assumptions.json` filtered by node ids belonging to each branch. Qualitative pros/cons are aggregated from `Alternative.pros` / `cons`. Optional engineering placeholders (`estimated_depth_or_height`, weight, fabrication, erection) are derived from `Branch.comparison_tags` when tags use the `key:value` convention (e.g. `depth:12m`, `weight:heavy`).
- **b) Quantitative vs qualitative:** *Quantitative* — `assumptions_count`, `calculations_count` (calculation-typed nodes plus `linked_calculation_ids`), `pending_checks_count`, `linked_reference_ids_count`, `max_subtree_depth`, `node_count`. *Qualitative* — `qualitative_advantages` / `qualitative_disadvantages`, `unresolved_blockers` (blocked node titles), and optional placeholder strings from tags.
- **c) Discarded branches:** Remain readable from `tree/branches/*.json`; comparison loads them like any branch and **does not** activate or reopen them, so they stay non-active for design while remaining comparable.
- **d) Document-derived references:** `reference_ids` lists node `linked_reference_ids`; each id is echoed in `citation_traces` as `DocumentCitationTrace` with `resolution_status: "ids_only"` until a dedicated Reference store resolves `document_id` / `fragment_id`.

**Future hardening (tracked, not in this milestone)**

- Conflict handling across multiple active authoritative document sources.
- Retrieval ranking thresholds and deterministic tie-breaking.

**Added**

- `BranchComparisonService`, `BranchComparisonResult`, `BranchComparisonRow`, `DocumentCitationTrace` in `services/branch_comparison.py`.
- `tests/test_branch_comparison.py`.

**Verification**

- `python -m pytest tests -q` — all tests pass.

### M5 — Document retrieval & citation (`cursor_prompts/06`)

**Rationale**

- Lexical retrieval over a filtered local corpus with explicit `CitationPayload` objects; structured `insufficient_evidence` when no qualifying passages exist (no LLM layer).

**Added**

- `DocumentRetrievalService` in `services/retrieval_service.py` — lexical scoring, filters (language, `document_ids`, topic, project primary `standard_family`), modes `normative_active_primary` vs `approved_ingested`.
- `tests/test_retrieval.py` — hits, filters, insufficient evidence, unknown classification excluded from normative mode.

**Verification**

- `python -m pytest tests -q` — all tests pass.

### M4b — Corpus authorization & classification (document-first)

**Changed**

- **Ingestion ≠ normative:** `ingested_document_ids` tracks catalog; `active_code_context.allowed_document_ids` is the normative/active pool and is **not** populated on ingest. `approve_document`, `activate_for_normative_corpus`, `document_corpus_policy` (`strict` vs `approve_also_activates`).
- **Normative classification:** `Document.normative_classification` (`unknown` | `primary_standard` | `supporting_document` | `reference_document`); `standard_family` is **not** defaulted from the project primary standard when omitted.
- **Fragments:** `fragment_content_hash`, `material_content_hash` (byte-identity), `ingestion_method`, snapshot approval/classification, PDF page range when extractable.
- **Project JSON migration:** `ingested_document_ids` / `document_corpus_policy` backfilled on load when missing.

### M4 — Local document ingestion (`cursor_prompts/05`)

**Rationale**

- Authoritative corpus registration with chunked fragments and citation-oriented metadata; offline, no cloud APIs.

**Added**

- `DocumentIngestionService` in `services/document_service.py` — pipeline import → normalize → segment → persist under `documents/{document_id}/`.
- `domain/document_codec.py`; JSON Schemas `document.schema.json`, `document_fragment.schema.json`.
- Stable fragment ids: `frag_` + SHA-256(`document_id|chunk_index|text`) prefix.
- Dependency: `pypdf` for text-layer PDF extraction.

**Persistence hardening (tracked)**

- Revision write-once guard; `RevisionBundle` + `load_revision_bundle` for snapshot-only tree/project/assumptions (`docs/implementation/PERSISTENCE_HARDENING.md`).
- `TreeStore` refactor: `relative_root` supports live `…/tree` vs revision `…/revisions/{id}/tree`.
- `domain/tree_integrity.py` — `validate_tree_integrity`.

**Verification**

- `python -m pytest tests -q` — all tests pass.

### M3 — Tree expansion & branch state (`cursor_prompts/04`)

**Rationale**

- Persist the decision tree under `tree/` (not embedded in `project.json`), with explicit branch lifecycle and auditable timestamps.

**Added**

- `src/structural_tree_app/domain/tree_codec.py` — JSON-safe branch/node/decision/alternative mapping.
- `src/structural_tree_app/domain/branch_transitions.py` — allowed branch state transitions.
- `src/structural_tree_app/storage/tree_store.py` — `TreeStore`, `copy_tree_directory` for revision snapshots.
- `src/structural_tree_app/services/tree_workspace.py` — persisted tree operations (root problem, children, decision options, activate/discard/reopen/clone, subtree, branch paths).
- Strict JSON Schemas: `branch.schema.json`, `node.schema.json`, `decision.schema.json`, `alternative.schema.json`; stricter `project.schema.json`, `revision.schema.json`, `assumption_record.schema.json`.

**Changed**

- `JsonRepository.write` — atomic write via temp file + `os.replace`.
- `ProjectService` — each revision stores `assumptions_snapshot.json` and a full copy of `tree/` under `revisions/{rev_id}/`; `load_revision_snapshot_assumptions`.
- `validation/json_schema.py` — validators for tree entities and assumptions list.

**Verification**

- `python -m pytest tests -q` — all tests pass (project + tree).

### M2 — Project persistence & versioning (`cursor_prompts/03`)

**Rationale**

- Reliable on-disk projects with revision history separate from project identity; prepare `tree/`, `documents/`, `exports/` for later milestones.

**Added**

- `src/structural_tree_app/paths.py` — repository root for schema loading.
- `src/structural_tree_app/validation/json_schema.py` — validate `project.json` and revision `meta.json` (Draft 2020-12).
- `src/structural_tree_app/domain/project_codec.py` — `project_to_dict` / `project_from_dict`; assumptions list helpers.
- `schemas/revision.schema.json` — revision metadata.
- `tests/test_project_persistence.py` — create/load/save, revisions, snapshots, invalid payload, `examples/example_project.json` mapping, assumptions.

**Changed**

- `Project.head_revision_id`; `RevisionMetadata` dataclass in `domain/models.py`.
- `schemas/project.schema.json` — optional `head_revision_id`.
- `ProjectService` — layout `workspace/{project_id}/`, `create_project`, `load_project`, `save_project`, `create_revision`, `list_revisions`, `load_revision_snapshot_project`, `load_assumptions` / `save_assumptions`.
- `JsonRepository.exists`.
- `main.py` — `save_project` after bootstrap tree mutation so `project.json` reflects `root_node_id` / `branch_ids`.
- `requirements.txt` / `pyproject.toml` — runtime dependency `jsonschema`.

**Verification**

- Superseded by full suite under M3; `tests/test_project_persistence.py` remains part of regression.

### M1 — Repository workflow & governance (`cursor_prompts/02`)

**Rationale**

- Establish predictable development workflow, minimal engineering artifacts, and auditable Block 2 progress without implementing persistence, ingestion, retrieval, or comparison logic.

**Added**

- `docs/implementation/BLOCK_2_STATUS.md` — milestone tracker (M1 complete).
- Root `CONTRIBUTING.md` — execution order of `cursor_prompts/02–08`, engineering rules (tree-first, document/citation-first, no OCR in Block 2 for ingestion), logging policy, local checks.
- Root `.gitignore` — Python, tooling caches, `workspace/`, virtualenvs.
- Root `pyproject.toml` — package metadata, `src` layout, optional `dev` extras (`pytest`), pytest `pythonpath`.
- Root `Makefile` — `import-check` target (`PYTHONPATH=src`).

**Changed**

- `README.md` — Block 2 execution table, pointers to plan/status/tests/contributing, development/local check notes.

**Verification**

- `python -c "import structural_tree_app; from structural_tree_app.main import bootstrap_example; print('ok')"` with `PYTHONPATH=src` (or `pip install -e .`) succeeds.
- `make import-check` succeeds where GNU Make is available.

### Planning — Block 2 implementation plan package

**Rationale**

- Execute the approved Block 2 **planning phase only**: implementation-ready roadmap, test strategy, and failure log scaffold aligned with `docs/00–03`, ADR-001, and the master data model.

**Added**

- `docs/04_block_2_implementation_plan.md` — Milestones M1–M7 mapped to `cursor_prompts/02–08`, traceability matrix (MVP → milestone → files → test intent), vision guardrails, rollback notes, and blocker-level open questions.
- `docs/TEST_STRATEGY.md` — Testing approach for Block 2 and beyond (local-first, deterministic vs LLM, citation completeness).
- `docs/FAIL_LOG.md` — Failure log template for Block 2 execution (no failures recorded for this planning-only step).
- `docs/CHANGELOG.md` — This file.

**Verification**

- Documentation reviewed for consistency with `docs/00_product_definition.md`, `docs/01_architecture_v1.md`, `docs/02_master_data_model.md`, `docs/03_mvp_scope.md`, and `docs/adr/ADR-001-local-first-architecture.md`.
- No application source code was modified as part of this planning-only deliverable.

### Documentation — Block 2 OCR policy & traceability (post-planning)

**Changed**

- `docs/04_block_2_implementation_plan.md` — **No OCR in Block 2**; M4 text-extractable PDFs only; structured statuses for non-extractable PDFs; A1/A2 approved; traceability row for corpus registration **M4 only**; **abrir referencia** remains **M5 only** (single row).
- `docs/TEST_STRATEGY.md` — M4 ingestion expectations aligned with no-OCR policy.
