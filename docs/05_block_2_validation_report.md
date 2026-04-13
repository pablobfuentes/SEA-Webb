# Block 2 — Validation & integration report (M7)

**Date:** 2026-04-12  
**Scope:** `cursor_prompts/08_validation_and_integration_prompt.txt`  
**Codebase:** `structural_tree_app_foundation`

This report confirms that Block 2 milestones **M2–M6** compose into a coherent local-first pipeline and documents what is **production-ready for authoritative user-facing claims** versus **internal / engineering integrity** only.

---

## 1. End-to-end scenario validated

**Automated:** `tests/test_block2_integration.py::test_end_to_end_project_tree_ingest_retrieve_compare`

The following sequence is exercised against a temporary workspace:

1. **Project:** `ProjectService.create_project` → persisted `project.json`, initial revision.
2. **Tree:** `TreeWorkspace` — two root problems (branches) with criterion child nodes.
3. **Ingestion:** `DocumentIngestionService.ingest_local_file` (text source) → `documents/{id}/` + fragments.
4. **Corpus policy:** `approve_document` → `activate_for_normative_corpus` so documents enter the normative pool for retrieval.
5. **Retrieval:** `DocumentRetrievalService.search(..., citation_authority="normative_active_primary")` — structured hits with citation-oriented payloads (hashes / fragment identity as implemented in M5).
6. **Revision:** `create_revision` captures a frozen snapshot (`revisions/{rev}/project_snapshot.json`, `assumptions_snapshot.json`, `tree/`).
7. **Comparison (live):** `BranchComparisonService.for_live` → `compare_branches([branch_a, branch_b])`.
8. **Comparison (revision snapshot):** `BranchComparisonService.for_revision_snapshot(ps, project_id, revision_id)` → same branch ids; asserts row counts and branch id ordering align with live for this fixture.

**Additional coverage:** `test_comparison_json_deterministic_ordering` — branch input order does not change sorted `compared_branch_ids` or row order.

**Full suite:** `python -m pytest tests/ -q` — **34 passed** (as of this report).

---

## 2. M7 reporting (explicit)

### (a) What end-to-end scenario was validated?

From **project creation** through **ingestion**, **retrieval**, and **branch comparison** (live and against a **revision snapshot**), as summarized in §1. No separate GUI; validation is via services + filesystem artifacts under `workspace/`.

### (b) Internal integrity vs user-facing authoritative output

| Area | Validated for | Authoritative for end-user / design claims? |
|------|----------------|---------------------------------------------|
| **Project / revisions / tree persistence** | Load/save, revision snapshots, tree files | Yes for **structural project state** (what is stored). |
| **Document ingestion** | Chunks, metadata, policy gates | Yes for **catalog + fragment identity** in corpus; normative activation is explicit. |
| **Retrieval (`DocumentRetrievalService`)** | `CitationPayload` / hit shape, filters, `insufficient_evidence` | **Yes** — this is the **normative path** for evidence-backed explanations per M5/M6 product rules. |
| **Branch comparison — metrics** | Counts, subtree stats, qualitative lists from tree + assumptions | **Engineering comparison v1** — authoritative **as structured metrics from persisted tree**, with `metric_provenance` (e.g. `computed`, `derived_from_tree`). |
| **Branch comparison — `citation_traces`** | Reference ids echoed with `resolution_status="ids_only"` | **No** — **not** full authoritative citations. `citation_trace_authority` remains **`internal_trace_only`** until Reference resolution and product rules elevate it. Use **retrieval** citations for user-facing authority. |
| **Comparison JSON** | `to_dict()` with sorted provenance keys; deterministic branch/row ordering | Internal + export stability; not a substitute for retrieval citations. |

### (c) What remains intentionally deferred after Block 2

- **UI / visualization** of tree or comparison (explicitly out of scope for Block 2).
- **Conflict handling** across multiple active normative sources (called out in CHANGELOG M6).
- **Retrieval ranking thresholds** and richer deterministic tie-breaking (M6 backlog).
- **OCR** and non-text-layer PDF paths (structured `ocr_deferred` / deferred work).
- **Full Reference store** resolving `reference_id` → `document_id` / `fragment_id` for comparison traces (today: `ids_only` is acceptable for internal comparison v1 only).
- **Broader reproducibility product UX:** revision snapshots **exist** and comparison can run on `for_revision_snapshot`; a dedicated “compare at commit” workflow, diff UI, or **automated regression of comparison vs labeled golden snapshots** is a **follow-up** (tracked as important for reproducible branch comparison from a frozen project state).

---

## 3. Non-blocking constraints (explicit)

### 3.1 Citation traces

- `citation_traces` with `resolution_status="ids_only"` is **acceptable for internal comparison v1**.
- It **must not** be treated as full authoritative citation output. The distinction is encoded as:
  - `BranchComparisonResult.citation_trace_authority == "internal_trace_only"` (current default).
  - Documentation on `DocumentCitationTrace` and `BranchComparisonRow.metric_provenance` (`document_trace_pending` for citation-adjacent fields).

**Authoritative citations** remain **`DocumentRetrievalService` + `CitationPayload`** (default `normative_active_primary`).

### 3.2 Reproducibility

- **Supported now:** `BranchComparisonService.for_revision_snapshot(ps, project_id, revision_id)` reads tree + assumptions from the **immutable revision bundle**, enabling comparison from a **frozen** state.
- **Follow-up:** workflow-level guarantees (e.g. pinning comparisons to revision in exports, CI golden files, or “compare two revisions”) if not already required by the next block.

### 3.3 Criterion provenance

- Where practical, **`metric_provenance`** maps metric names to:
  - `computed` | `derived_from_tree` | `manual_tag` | `document_trace_pending`
- Citation-related comparison fields use `document_trace_pending` until Reference resolution is complete.

### 3.4 Determinism

- Branch lists are **sorted** for comparison input.
- Rows and serialized outputs (including sorted keys in `metric_provenance` in `to_dict()`) are kept **deterministic** so validation and diffs remain stable.

---

## 4. Conclusion

Block 2 **M2–M7** objectives for the foundation repo are met: integrated tests and this report document coherent behavior, clear boundaries between **retrieval authority** and **comparison traces**, and explicit follow-ups for post–Block 2 work. **Block 3 / UI are not started here.**
