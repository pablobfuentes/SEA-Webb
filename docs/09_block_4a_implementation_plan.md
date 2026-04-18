# Block 4A — Implementation plan (planning phase)

**Status:** Planning only — **no frontend code in this step**.  
**Date:** 2026-04-18  
**Depends on:** **Block 3 frozen baseline** — `docs/implementation/BLOCK_3_STATUS.md`, `docs/08_block_3_validation_report.md` (M1–M7 complete; backend/domain changes only for justified bugfixes). Block 2 remains infrastructure baseline — `docs/implementation/BLOCK_2_STATUS.md`.

**Execution order:** Block 4A does **not** reorder or replace Block 2/3; it adds a **thin frontend layer** on top of existing services.

---

## A. Executive summary

**What Block 4A is**  
The **first frontend minimum validation workbench**: a local, intentionally modest UI that drives the **already implemented Block 3 vertical flow** (and underlying Block 2 primitives) so that product behavior can be exercised **end-to-end through real interactions**, not only via pytest.

**Why it is the correct next step after Block 3**  
Block 3 proved the **domain story** in code (`SimpleSpanSteelWorkflowService`, M4 characterization, materialized branches, M5 preliminary deterministics, M6 comparison, revision replay). Without a thin UI, validation remains **developer-only** (imports, tests, ad-hoc scripts). Block 4A closes the gap between **correct backend contracts** and **observable, interactive validation** — without claiming a finished product surface.

**What capability it unlocks**  
- Human-in-the-loop verification that the **tree remains primary**, alternatives and branches are understandable, and **authority boundaries** are visible.  
- Early detection of **friction or missing affordances** in the existing model (documented explicitly; **no silent redesign** of Block 3).  
- A foundation for later “real” UI work that can **reuse the same service calls** and provenance rules.

---

## B. Frontend scope definition

### B.1 Actor

- **Primary:** engineer or developer **validating** the product behavior (same persona as Block 3 tests, but through UI).  
- **System:** local process hosting the workbench + existing `structural_tree_app` Python services + on-disk `workspace/{project_id}/`.

### B.2 Primary workflows (minimum)

1. Create or open a project (fixed workspace root configurable; see §N).  
2. Run **simple-span steel workflow** setup (`SimpleSpanSteelWorkflowService.setup_initial_workflow`) with `SimpleSpanWorkflowInput` fields exposed as form inputs.  
3. Inspect **root problem node** and **decision node** (ids, titles, parent links as persisted).  
4. List **all eligible alternatives** with **top-3 suggestion** flags (`suggested`, `suggestion_rank`, `suggestion_provenance`) visibly distinct from “eligible but not suggested.”  
5. Inspect **characterization_items** per alternative with **provenance class** per item (retrieval_backed, workflow_heuristic, manual_placeholder, not_yet_evidenced).  
6. **Select** an alternative and **materialize working branch** (`TreeWorkspace.materialize_working_branch_for_alternative`).  
7. **Run M5** preliminary on that branch (`run_simple_span_m5_preliminary`) once; surface refusal if duplicate or invalid.  
8. Display **Calculation** and **Check** records (from `TreeStore`) with **explicit preliminary disclaimers** (copy from backend `result` / labels; UI does not soften wording).  
9. Run **M6** comparison (`BranchComparisonService`) for user-selected branch ids (minimum: trunk + one materialized branch); show `comparison_field_sources`, `citation_trace_authority`, `notes`.  
10. **Create revision** (`create_revision`); **switch context** to replay **revision snapshot** (`for_revision_snapshot` / `load_revision_bundle`) for comparison or read-only tree state.  

### B.3 Minimum screens / panels / views

A single **workbench shell** with **named panels** (layout can be one scroll page or tabs — implementation detail):

| Panel | Purpose |
|-------|---------|
| **Project / workspace** | Create project, list open project id, show workspace path, reload from disk |
| **Workflow input** | Bind to `SimpleSpanWorkflowInput` (schema-aligned); submit “Setup workflow” |
| **Tree / branches** | List branches with state; select branch for detail; optional link to node list |
| **Node / decision / alternative detail** | Show selected node; for decision, list `alternative_ids`; open alternative detail |
| **Alternatives & suggestions** | Table: title, `catalog_key`, `suggested`, rank, score, provenance |
| **Characterization & provenance** | Render `characterization_items` with provenance badge per row |
| **M5 run** | Button “Run M5 preliminary” on selected materialized branch; show calc/check ids |
| **Calculation / Check detail** | Read-only JSON or structured fields + disclaimer banner |
| **M6 comparison** | Branch multi-select → `compare_branches` → `to_dict()` pretty view with field-source legend |
| **Revision / replay** | List `version_ids` / revisions; “View as snapshot” toggles read-only snapshot mode for comparison |

### B.4 Expected interactions

- Form submits map **directly** to existing service methods — no parallel domain state beyond session selection (project id, selected branch id, selected revision id).  
- **No** LLM in the default path.  
- **No** reclassification of backend enums/strings for “prettier” display without showing raw value alongside (transparency).

### B.5 Expected outputs

- On-disk persistence unchanged (same files as CLI/tests).  
- User-visible labels for **authority tier** (see §G) — always derived from backend fields, not invented in the UI layer.

### B.6 Success criteria

- A reviewer can complete the **13 user capabilities** listed in the Block 4A product brief (user message) without importing Python manually.  
- Provenance and preliminary vs authoritative rules are **visually distinct** and match `docs/08_block_3_validation_report.md`.  
- One automated test path exists for the **HTTP/API shell** (if FastAPI) or documented manual script for pure-Streamlit alternative.

### B.7 Failure / refusal behavior

- Surface backend errors **verbatim** where safe (e.g. `SimpleSpanSteelWorkflowError`, `SimpleSpanM5Error`, `BranchComparisonError`, `ProjectPersistenceError`).  
- Do not catch-and-replace with generic “Something went wrong” without developer expandable detail (stack or message in a collapsible **debug** strip).  
- If the UI needs data not exposed today (e.g. list all branch ids without scanning store), add a **narrow read-only helper** in backend — listed in §I as a support item, not a redesign.

---

## C. Scope in / scope out

### C.1 In scope (Block 4A)

- Local validation workbench **one vertical flow** (Block 3 simple-span path).  
- Read/write via existing **`ProjectService`**, **`TreeWorkspace`**, **`SimpleSpanSteelWorkflowService`**, **`run_simple_span_m5_preliminary`**, **`BranchComparisonService`**, revision APIs.  
- Optional **minimal** document ingest + retrieval demo panel **only if** it fits Milestone timebox — otherwise defer (retrieval-backed characterization can still appear when corpus exists from tests).  
- Explicit **legend** and **badges** for provenance and preliminary signals.  
- Automated tests for thin API layer where applicable.

### C.2 Out of scope (Block 4A)

- Production UI/UX, design system, branding, animation.  
- Full canvas / graph editor, drag-drop tree editing.  
- Chat, agents, NL design assistant.  
- Generic workflow builder for all future flows.  
- Full PDF viewer, OCR, BIM/CAD.  
- Report PDF/export suite.  
- Multi-user, auth, cloud sync.  
- **Changing** Block 3 semantics, catalog definitions, or M5 formulas except **bugfixes** with ADR/changelog.  
- Replacing `method_label` with a registry (deferred per Block 3).

---

## D. Frontend architecture proposal (minimum viable)

### D.1 Recommendation

**Primary recommendation: thin local web server (FastAPI) + server-rendered HTML templates (Jinja2)**, with optional **HTMX** for partial updates only where it reduces complexity.

**Rationale (fits current repo)**

| Criterion | Fit |
|-----------|-----|
| **Local usage** | Single `uvicorn` (or `python -m`) process; developer runs one command. |
| **Speed** | No separate npm SPA mandatory; templates + forms are fast to wire. |
| **Transparency** | Each user action maps to a **named route**; easy to log and grep. |
| **Expose backend cleanly** | Route handlers call existing services directly — same as tests. |
| **Testability** | `httpx` / Starlette `TestClient` for integration tests without a browser. |

**Alternatives (documented tradeoffs)**

- **Streamlit:** fastest panels, but **implicit rerun model** can obscure control flow; session state can duplicate domain if mishandled. Acceptable only if team prioritizes speed over route transparency — requires strict discipline (thin wrapper functions only).  
- **NiceGUI / Reflex:** Python-native; add dependency weight; still need clear separation from domain.  

**Not recommended for 4A:** full React/Vue SPA (heavy toolchain vs “minimum validation workbench”).

### D.2 Process model

- **Single Python package area** e.g. `src/structural_tree_app/workbench/` or top-level `workbench/` — **TBD in M2** — containing only HTTP/UI glue.  
- **Workspace root:** configurable env var `STRUCTURAL_TREE_WORKSPACE` defaulting to `./workspace` under cwd (align with README examples).  
- **No** new persistence format; all state remains JSON on disk per Block 2/3.

### D.3 Backend “support” items (only if needed)

Prefer **read-only list methods** on existing stores/services over new entities:

- e.g. `TreeStore.list_branch_ids()` already exists — use it.  
- If UI needs “all nodes for branch,” use existing load patterns from `TreeWorkspace` / `TreeStore` as in tests.  
- **New backend code** only when a read path is genuinely missing — small PR, single purpose, tested.

---

## E. Minimum views/panels

Consolidated list (refinement of §B.3):

1. **Workbench chrome** — title, workspace path, project id, environment warning (“validation workbench — not production”).  
2. **Project** — create / load project id.  
3. **Simple-span workflow** — inputs + “Setup” + result summary (`SimpleSpanWorkflowResult` fields).  
4. **Branch explorer** — table of branches: id, title, state, `origin_alternative_id`.  
5. **Alternative inspector** — per alternative: catalog_key, suggestion metadata, full `characterization_items` table with provenance column.  
6. **Materialize** — pick alternative → call materialize → show new branch id.  
7. **M5 panel** — select materialized branch → Run → show calc id + check ids + link to detail.  
8. **Calc / Check detail** — JSON from codecs (`calculation_to_dict`, `check_to_dict`) with preliminary banner.  
9. **M6 comparison** — multi-select branches → compare → render `BranchComparisonResult` + legend for `comparison_field_sources` and `citation_trace_authority`.  
10. **Revision** — list revisions, create revision, **snapshot mode** toggle loading `BranchComparisonService.for_revision_snapshot` or read-only bundle.

---

## F. Interaction model (happy path)

```text
Start app → set/confirm workspace → Create project
→ Enter SimpleSpanWorkflowInput → Setup workflow (M3+M4)
→ Inspect decision + alternatives (see suggestions + characterization)
→ Choose alternative → Materialize working branch
→ Run M5 preliminary → Inspect Calculation + Checks (preliminary)
→ Select branches (e.g. trunk + working) → Run M6 comparison
→ Create revision → Switch to snapshot context → Re-run comparison / inspect frozen tree
```

**Sad paths:** duplicate workflow setup refused; M5 duplicate refused; comparison with &lt;2 branches refused — **show backend message**.

---

## G. Authority and provenance presentation rules (mandatory)

The UI **must not** merge categories. Use **parallel display**: human label + **raw backend string** in monospace or tooltip.

| Category | Backend source | UI rule |
|----------|----------------|--------|
| **Authoritative document-backed** | `characterization_items[].provenance == retrieval_backed` + `reference_id` / persisted `Reference` | Badge “Retrieval-backed”; show `reference_id`; short excerpt only if loaded via existing store/retrieval — **do not fabricate** excerpt if not loaded |
| **Preliminary deterministic (M5)** | `Calculation`/`Check` with `method_label`, `result.authority`, check messages | Banner: “Preliminary workflow signal — not structural adequacy”; show `method_label` |
| **Workflow heuristics** | `workflow_heuristic`, suggestion metadata on `Alternative` | Badge “Workflow heuristic / not design adequacy”; show `suggestion_provenance` |
| **Manual placeholders** | `manual_placeholder` | Badge “Manual / placeholder” |
| **Not yet evidenced** | `not_yet_evidenced` | Badge “No corpus passage (structured)” |
| **Internal trace-only (comparison)** | `citation_trace_authority == internal_trace_only`, `DocumentCitationTrace` | Banner: “Internal ids only — not a citation”; never present as normative proof |

**M6 `comparison_field_sources`:** render a small **legend** mapping keys (`m5_deterministic_preliminary`, `branch_tree_derived`, …) to short explanations copied from backend doc strings / Block 3 report.

---

## H. Milestones (ordered)

| ID | Name | Objectives | Dependencies | Target areas | Test intent | Rollback | Risks |
|----|------|------------|--------------|--------------|-------------|----------|-------|
| **M1** | Baseline freeze + UI boundary | Confirm Block 3 API surface; list integration points; add Block 4A docs only | Block 3 complete | `docs/`, trackers | Doc review | Revert doc commit | Scope creep |
| **M2** | App shell + dependency choice | Add minimal web deps (`fastapi`, `uvicorn`, `jinja2` — exact pins in `pyproject`); stub app boots; `/health` | M1 | `pyproject.toml`, `src/.../workbench/` or `workbench/` | Import + health route test | Remove package | Dependency bloat |
| **M3** | Project + workspace wiring | Create/open project; display project id; workspace path from env | M2 | workbench routes, thin config | TestClient: create project | Revert routes | Path confusion on Windows |
| **M4** | Workflow input + M3/M4 trigger | Form for `SimpleSpanWorkflowInput`; call `setup_initial_workflow`; show result ids | M3 | same | Integration test against `tmp_path` workspace | Revert | Schema drift vs `simple_span_workflow_input.schema.json` |
| **M5** | Branches + alternatives + characterization views | List branches/alternatives; render characterization table with provenance | M4 | templates | Snapshot or assert HTML contains provenance strings | Revert | XSS — escape user-facing text |
| **M6** | Materialize + M5 run + calc/check panel | Buttons call `materialize_working_branch_for_alternative`, `run_simple_span_m5_preliminary`; detail views | M5 | same | TestClient flow matches `test_block3_vertical_flow` | Revert | Double-post M5 |
| **M7** | M6 comparison + revision replay UI | Branch multi-select comparison; `create_revision`; snapshot mode | M6 | same | E2E API test mirroring `tests/test_block3_vertical_flow.py` | Revert | Revision id confusion |

**Note:** Milestone numbers **4A-M1…M7** are independent from Block 3 M-numbers; cross-references always say “Block 4A M*”.

---

## I. Exact files to create or modify (by milestone)

**Likely new (implementation phase — not created in planning step)**

| Area | Files |
|------|--------|
| Workbench app | `src/structural_tree_app/workbench/__init__.py`, `app.py`, `routes/*.py`, `templates/*.html`, `static/` (minimal CSS) |
| Config | `pyproject.toml` — optional `[project.optional-dependencies] workbench = [...]` |
| Entry | `README.md` — “Run workbench” section; optional `Makefile` target |
| Tests | `tests/test_workbench_*.py` — `TestClient` flows |

**Existing (call only — avoid edits unless support helper)**

| Area | Files |
|------|--------|
| Services | `services/project_service.py`, `tree_workspace.py`, `simple_span_steel_workflow.py`, `simple_span_m5_service.py`, `branch_comparison.py` |
| Domain/codec | `domain/tree_codec.py` for safe JSON display |

**Docs**

| File | Role |
|------|------|
| `docs/09_block_4a_implementation_plan.md` | This plan |
| `docs/10_block_4a_acceptance_snapshot.md` | Acceptance + manual checklist |
| `docs/implementation/BLOCK_4A_STATUS.md` | Tracker (create at M1 implementation) |
| `docs/CHANGELOG.md` | Each milestone entry |

---

## J. Traceability matrix

| Block 4A capability | Milestone | Primary implementation | Test intent | Acceptance signal |
|---------------------|-----------|------------------------|-------------|---------------------|
| Open/create project | 4A-M3 | workbench routes + `ProjectService` | TestClient creates project | Project id visible; files on disk |
| Simple-span workflow setup | 4A-M4 | form → `setup_initial_workflow` | Integration test | `SimpleSpanWorkflowResult` fields shown |
| View root + decision + alternatives | 4A-M5 | templates + store loads | HTML/assert JSON | Matches persisted ids |
| Top-3 vs eligible distinction | 4A-M5 | table columns | assert `suggested` column | Same semantics as Block 3 |
| Characterization provenance | 4A-M5 | per-item badge | string present | No blended categories |
| Materialize branch | 4A-M6 | POST → `materialize_*` | test | `origin_alternative_id` set |
| M5 run | 4A-M6 | POST → `run_simple_span_m5_preliminary` | test | Calc+checks listed |
| M6 comparison | 4A-M7 | POST → `compare_branches` | test | `citation_trace_authority` visible |
| Revision + replay | 4A-M7 | `create_revision` + snapshot compare | test | Matches Block 3 M7 behavior |
| Authority UI rules | 4A-M5–M7 | templates | manual + automated string checks | Banners present |

---

## K. Testing strategy (Block 4A)

1. **Backend unchanged** — existing `pytest tests/` remains green after each milestone.  
2. **Workbench API tests** — `httpx.AsyncClient` or Starlette `TestClient` with `tmp_path` workspace; no live browser required for CI.  
3. **Authority strings** — assert response body contains mandatory disclaimer substrings (“Preliminary”, “internal_trace_only”, etc.) per view.  
4. **Optional:** Playwright later (not required to close 4A).  
5. **Manual validation script** — `docs/10_block_4a_acceptance_snapshot.md` checklist (5–10 minutes).

---

## L. Acceptance criteria (Block 4A complete)

1. Documented capabilities (§B.2 / product brief **1–13**) are **demonstrable** through the workbench.  
2. Provenance and authority rules (§G) are **visible** and consistent with `docs/08_block_3_validation_report.md`.  
3. Automated tests cover **core happy path** at least equivalent to `test_block3_vertical_flow` **via workbench API** (4A-M7).  
4. No change to Block 3 contracts except **documented bugfixes**.  
5. `docs/10_block_4a_acceptance_snapshot.md` updated with actual commands and test names.  
6. `docs/CHANGELOG.md` records Block 4A closure.

---

## M. Deferred items (explicit)

- Full design system, accessibility certification, i18n.  
- Canvas / interactive graph.  
- Full document viewer and fragment navigation.  
- General workflow authoring UI.  
- Mobile layout.  
- Electron packaging (optional future).  
- Replacing FastAPI with SPA if product later requires — 4A does not block that migration if service boundaries stay thin.

---

## N. Blocking questions (minimum)

1. **Workspace root:** Confirm default (`./workspace` relative to process cwd vs user home). Affects README and env documentation only — **not** a code architecture blocker.  
2. **Optional:** Confirm **FastAPI + Jinja** as the chosen stack at **4A-M2 kickoff**; if rejected, substitute Streamlit with explicit session-state rules in ADR supplement.

**No other blockers** identified at planning time — Block 3 exposes sufficient services for the workbench.

---

## Document control

- **Block 3** remains frozen; this plan **consumes** it, does not alter execution order of Blocks 2/3.  
- Next update: implementation kickoff — add `docs/implementation/BLOCK_4A_STATUS.md` and changelog entries per milestone.
