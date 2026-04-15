# Block 3 — Implementation plan (planning phase)

**Status:** Block 3 **M2** implemented (tree persistence for `Calculation`, `Check`, `Reference`). **M3+** not started — workflow generation, retrieval-backed pros/cons, and deterministic engine remain future milestones.  
**Date:** 2026-04-12  
**Depends on:** Block 2 closed — see `docs/05_block_2_validation_report.md`, `docs/implementation/BLOCK_2_STATUS.md` (frozen baseline). **M2+ progress:** `docs/implementation/BLOCK_3_STATUS.md`.

---

## A. Executive summary

**What Block 3 is**  
Block 3 defines and implements the **first vertical engineering slice**: an end-to-end, testable workflow for **selecting and developing alternatives for a primary steel member in a simple-span problem**, using the existing local-first core (project, tree, documents, retrieval, comparison, revisions).

**Why it is the correct next step after Block 2**  
Block 2 proved **infrastructure**: persistence, tree lifecycle, normative retrieval with `CitationPayload`, branch comparison v1 (live + revision snapshot), and clear separation between **authoritative retrieval** and **internal comparison traces** (`internal_trace_only`). The product vision (`docs/00_product_definition.md`, `docs/03_mvp_scope.md`) requires a **guided tree** plus **evidence** plus **deterministic calculation** — none of that is exercised as a single user-meaningful engineering story until Block 3 wires those pieces into one narrow workflow.

**What engineering capability it will unlock**  
A user (or test harness) can: define a simple-span steel problem with explicit assumptions and normative context; **open comparable branches** (structural alternatives); attach **pros/cons with explicit provenance** (authoritative citations vs manual vs non-authoritative placeholders); **compare** branches with enriched technical criteria; **select** one branch; run **preliminary deterministic checks** on that path; and **re-run or audit** the same flow from **live state** or from a **revision snapshot** — without claiming full member design, full UI, or a general-purpose solver.

---

## B. Use case definition

### B.1 Actor

- **Primary:** structural engineer or advanced student using the local core (API/services), later a UI consumer of the same contracts.
- **System:** `structural_tree_app` services + on-disk project layout under `workspace/{project_id}/`.

### B.2 Inputs

| Input | Description |
|-------|-------------|
| **Problem framing** | Simple span; span length; support/knee assumptions as stated in product (simple span between columns). |
| **Loading intent** | Qualitative and/or quantified design actions for the first slice (e.g. uniform load magnitude **or** explicit “TBD” with assumption records — exact load combination depth is bounded by Block 3 scope). |
| **Constraints** | Deflection limits, depth/headroom, fabrication/erection constraints — captured as **assumptions** and/or **comparison_tags** where already supported. |
| **Normative context** | `ActiveCodeContext` (e.g. primary standard family); corpus documents ingested, approved, and activated per Block 2 rules. |

### B.3 Expected outputs

1. **Tree structure:** root problem node; **initial decision** with alternatives representing the first-level structural options (see §C).  
2. **Branches:** one branch per explored alternative path; **discard / reopen / clone** behavior unchanged from Block 2 semantics.  
3. **Evidence:** where required, **retrieval-backed** text for normative or design-method claims (`DocumentRetrievalService` + `CitationPayload`); structured **insufficient_evidence** when the corpus cannot support a claim.  
4. **Comparison:** `BranchComparisonService` (or successor) producing **deterministic** rows; **technical criteria** extended in a controlled way (see milestones).  
5. **Deterministic artifacts:** persisted **Calculation** and **Check** records linked to nodes, with inputs/substitutions/results suitable for audit.  
6. **Revision compatibility:** workflow runnable on **live** project state; **reconstructible** from `revisions/{revision_id}/` snapshots (tree + assumptions at minimum; calculations/checks must live under revision tree copy once persisted).

### B.4 Success criteria

- At least **one automated end-to-end test** exercises: project → problem + alternatives → corpus + retrieval where applicable → comparison → select branch → assumptions + deterministic calculation/check → `create_revision` → repeat comparison or calculation **from revision snapshot** (exact assertions defined in `docs/07_block_3_acceptance_snapshot.md`).  
- No authoritative design claim is produced **only** from LLM (LLM not required for Block 3 core tests).  
- Pros/cons that are not corpus-backed are **explicitly labeled** in model or export (provenance enum / parallel structure — see §G).  
- Block 2 boundaries **preserved**: retrieval remains authority gate; comparison `citation_traces` remain non-authoritative unless separately promoted.

### B.5 Failure / refusal conditions

- Retrieval returns **insufficient_evidence** for a query that was **required** to support a normative assertion → workflow must surface structured refusal or force user to add corpus / relax claim class (no silent invention).  
- Missing assumptions for a deterministic check → check status **blocked** / **inputs_missing**, not a numeric “pass”.  
- Schema-invalid persistence → rejected at save with clear error (consistent with Block 2).

---

## C. Scope in / scope out

### C.1 In scope (Block 3)

- **One vertical workflow** “simple span → primary steel member alternatives → compare → select → preliminary deterministic checks.”  
- **Branch set (initial decision)** aligned with `docs/03_mvp_scope.md`, represented explicitly in planning and tests:  
  - **Truss / celosía**  
  - **Castellated / cellular beam / viga alveolar**  
  - **Tapered / variable-inertia beam** (documented as such in tree titles/descriptions)  
  - **Optional** conventional rolled or built-up beam **only** as a clearly bounded optional alternative if justified by the same workflow API (not a parallel product path).  
- **Provenance for qualitative claims:** authoritative (retrieval-linked), manual, explicit placeholder, or explicitly non-authoritative.  
- **Deterministic calculation slice:** narrow, reproducible formulas (e.g. simple flexure / deflection **indicators**, geometric ratios, first-pass utilization **framework** with explicit assumptions) — **not** full code-compliant design for all limit states.  
- **Checks:** at least one **Check** record tied to a **Calculation** and node, with demand/capacity or utilization fields populated per schema intent.  
- **Assumptions** as first-class inputs to the calculation path.  
- **Branch comparison** enriched with **technical criteria** that are either computed from tree/assumptions or explicitly tagged as manual/placeholder.  
- **Persistence** for calculations/checks (and references if needed) under the project tree with revision snapshots including them.  
- **Documentation + tests** per `docs/TEST_STRATEGY.md` principles.

### C.2 Out of scope (Block 3)

- Full **graphical UI** / canvas / chat (may consume APIs later).  
- **OCR** and non-text PDF pipelines.  
- **BIM/CAD** import/export.  
- **Global optimization** (member sizing search across discrete catalogs).  
- **General-purpose FEA** or 3D solver architecture.  
- **Connection design** beyond a possible single illustrative placeholder node **if** explicitly marked non-authoritative.  
- **All load cases / combinations** for production design.  
- **LLM** as authority for any numeric result or pass/fail.  
- Resolving **Reference** store for full `reference_id` → document/fragment for comparison traces (may remain deferred; user-facing citations still via retrieval).  
- **Automated golden diff** for every export (optional stretch; not required to close Block 3).

---

## D. Milestones (ordered)

Milestones are **sequential**; later milestones may add files listed earlier when discovery requires it. Names map to the suggested themes in the Block 3 brief; reordered only where repo reality requires (persistence before heavy workflow logic).

| ID | Name | Objectives | Dependencies | Primary target areas | Test intent | Rollback | Risks |
|----|------|------------|--------------|----------------------|-------------|----------|-------|
| **M1** | Freeze Block 2 baseline & Block 3 boundary | Lock Block 2 as dependency; finalize §B–C for implementation; no code churn on Block 2 paths without ADR | Block 2 closed | `docs/`, `docs/implementation/BLOCK_2_STATUS.md` | Doc consistency review | Revert doc commit | Scope creep from “one slice” |
| **M2** | Domain & persistence for engineering artifacts | Persist `Calculation` / `Check` (and optionally `Reference`) under `tree/`; extend `TreeStore`, codecs, JSON Schema; `TreeWorkspace` or dedicated service methods to attach calcs to nodes | M1 | `domain/tree_codec.py`, `domain/models.py`, `storage/tree_store.py`, `schemas/*.schema.json`, `validation/json_schema.py` | Unit tests: save/load round-trip, schema rejection | Delete new dirs / revert codecs | Migration of existing projects empty dirs |
| **M3** | Workflow API: simple-span problem & branch generation | Service module(s) that create root problem + **first decision** with **four** (or five with optional) alternatives; seed titles/descriptions; optional `comparison_tags`; integrate with branch activate/discard | M2 | `services/` (e.g. `simple_span_workflow.py` or `workflows/simple_span_steel.py`), `main.py` optional thin demo | Unit test: workflow creates expected branch/node/decision counts | Remove service module | Hard-coding copy in code — mitigate via data file or registry dict **in one module** |
| **M4** | Evidence-backed branch characterization | For each alternative, attach pros/cons with **provenance**; wire retrieval queries where normative support exists; store citation fragment ids on alternatives or parallel structure; **never** mix internal traces with user citations | M3, Block 2 retrieval | `services/retrieval_service.py` (helpers only), domain/alternative extensions, `schemas/alternative.schema.json` | Tests: mock corpus → retrieval-linked pros; manual pros flagged | Revert schema extension with migration note | Overstating authority — mitigate with enums and tests |
| **M5** | Deterministic preliminary calculation slice | Pure functions + persisted `Calculation` for one selected branch path (e.g. **M_max** from w,L simple cases, or deflection indicator); inputs from assumptions; **Check** with utilization | M2–M4 | `services/` deterministic module (e.g. `deterministic/simple_span_steel.py`), `TreeStore` calc paths | Unit tests for numeric reproducibility; integration test creates calc/check | Remove calc files | Formula errors — peer review + bounded inputs |
| **M6** | Branch comparison enriched | Extend `BranchComparisonService` rows or metrics for Block 3 technical criteria (e.g. calc count, check status, provenance summary) without breaking determinism; `metric_provenance` values extended | M2–M5 | `services/branch_comparison.py`, docs | Compare before/after `to_dict()` stability | Feature flag or version field on result | Breaking JSON consumers — bump documented shape |
| **M7** | Revision-safe E2E validation | Single test file: full vertical flow + revision replay; update `docs/TEST_STRATEGY.md` pointer; optional short report mirroring `docs/05_block_2_validation_report.md` | M1–M6 | `tests/test_block3_vertical_flow.py` (name TBD), `docs/` | CI green | Revert test + doc | Flaky FS — use `tmp_path` |

---

## E. Exact files to create or modify (by milestone)

> Paths relative to `structural_tree_app_foundation/`. **Create** = new in Block 3; **Modify** = expected edits.

| Milestone | `src/` | `schemas/` | `tests/` | `docs/` |
|-----------|--------|------------|----------|---------|
| **M1** | — | — | — | **Create** `06_block_3_implementation_plan.md`, `07_block_3_acceptance_snapshot.md`; **Update** `CHANGELOG.md`; **Update** `implementation/BLOCK_2_STATUS.md` (baseline note) |
| **M2** | **Modify** `storage/tree_store.py`; **Modify** `domain/tree_codec.py`; **Modify** `validation/json_schema.py`; **Modify** `domain/models.py` only if persistence requires small fields; **Create** optional `domain/calculation_codec.py` / `check_codec.py` | **Create** `check.schema.json` if missing; **Modify** `calculation.schema.json` if load/save gaps; ensure alignment with `models.py` | **Create** `test_calculation_persistence.py` or extend persistence tests | **Update** `02_master_data_model.md` only if entities change materially (optional erratum) |
| **M3** | **Create** `services/simple_span_workflow.py` (or `services/workflows/simple_span_steel.py`) | — | **Create** `test_simple_span_workflow.py` | — |
| **M4** | **Modify** `domain/models.py` (`Alternative` provenance fields) or parallel **Create** `domain/alternative_characterization.py`; **Modify** `services/tree_workspace.py` or workflow service | **Modify** `alternative.schema.json` (additionalProperties / new optional blocks) | **Create** `test_alternative_provenance.py` | — |
| **M5** | **Create** `deterministic/simple_span_steel.py` (under `services/` or `domain/` — pick one package style consistent with repo) | — | **Create** `test_deterministic_simple_span.py` | — |
| **M6** | **Modify** `services/branch_comparison.py` | — | **Modify** `test_branch_comparison.py` + new cases | — |
| **M7** | — | — | **Create** `test_block3_vertical_flow.py` | **Create** `docs/08_block_3_validation_report.md` (at M7 — placeholder name) or update `TEST_STRATEGY.md` §2–3 |

**README / root:** optional pointer to Block 3 plan in a later doc pass (not required for M1 minimum).

---

## F. Traceability matrix (one page)

| Block 3 capability | Milestone | Primary files | Test intent | Acceptance signal |
|--------------------|-----------|---------------|-------------|-------------------|
| Simple-span problem + initial alternatives | M3 | `services/simple_span_workflow.py`, `TreeWorkspace` | Workflow creates N branches / decision / alternatives | Assert tree IDs and titles; branch states |
| Assumptions driving inputs | M3–M5 | `assumptions.json` + `TreeWorkspace` / project service | Assumptions filtered in comparison and passed to calc | E2E assumptions present in snapshot |
| Authoritative document retrieval | M4 | `retrieval_service.py`, workflow | Retrieval returns `CitationPayload` or `insufficient_evidence` | No fake citations; structured miss |
| Pros/cons provenance | M4 | `Alternative` + schema + workflow | Unit tests for enum/manual/retrieval-linked | Serialized JSON shows provenance |
| Deterministic calculation | M5 | `deterministic/simple_span_steel.py`, `TreeStore` calcs | Numeric unit tests | Same inputs → same outputs |
| Checks | M5 | `Check` + `TreeStore` | Check status reflects pass/blocked | Utilization bounded / message |
| Branch comparison (technical) | M6 | `branch_comparison.py` | Deterministic `to_dict()` | New metrics with provenance |
| Discarded branch preservation | M3+ | existing `TreeWorkspace` | E2E discard + compare | Comparison includes discarded |
| Revision-safe replay | M7 | `ProjectService`, `TreeStore.for_revision_snapshot` | E2E live vs revision | Snapshot matches live for fixed inputs |
| Internal vs authoritative citations | M4–M7 | comparison + docs | Compare traces still `internal_trace_only` | Assert authority fields unchanged |

---

## G. Deterministic vs non-deterministic boundary

| Function / artifact | Classification | Notes |
|---------------------|----------------|-------|
| JSON read/write, schema validation | **Deterministic** | Same bytes → same outcome. |
| Branch ordering in comparison | **Deterministic** | Sorted branch ids (existing behavior). |
| `TreeWorkspace` state transitions | **Deterministic** | Subject to valid transitions. |
| **Preliminary steel formulas** (e.g. \(M = wL^2/8\), simple deflection indicators) | **Deterministic** | Implemented in pure Python; versioned `method_label` / `formula_text`. |
| **Unit conversion** (if added) | **Deterministic** | Must be explicit per project `unit_system`. |
| **DocumentRetrievalService.search** | **Retrieval/evidence-based** | Authoritative for citations; not deterministic across corpora — deterministic **given fixed workspace fixture**. |
| **Pros/cons** tied to retrieval hits | **Retrieval/evidence-based** | Authoritative only when linked to `CitationPayload` / fragment ids. |
| **Pros/cons** entered as engineering judgment | **Manually tagged** | `provenance = manual` or equivalent. |
| **Pros/cons** “TBD” / pedagogy | **Placeholder** | Non-authoritative; cannot justify code checks alone. |
| **LLM-generated copy** (if ever wired) | **Future LLM-assisted, not authoritative** | Must not write to `Calculation.result` or `Check.status` without human explicit action — **out of Block 3 default path**. |
| **BranchComparisonRow** qualitative strings from tree | **Derived from persisted tree** (existing) + optional manual tags | Same as Block 2 — not normative authority. |
| **`citation_traces` in comparison** | **Internal / ids_only** | Remains non-authoritative until Reference resolution product exists. |

---

## H. Acceptance criteria (Block 3 complete)

1. **Vertical E2E test** passes: simple-span workflow, retrieval fixture, comparison, selection, deterministic calc+check, revision snapshot replay — documented in `docs/07_block_3_acceptance_snapshot.md`.  
2. **Calculations and checks** persist under project tree and appear in revision snapshots.  
3. **At least one** normative-backed and one explicitly **non-normative** qualitative claim path are demonstrable in tests.  
4. **No regression** to Block 2 suite: `python -m pytest tests/ -q` green (test count will increase).  
5. **Documentation:** implementation plan (this file), acceptance snapshot, CHANGELOG entry, TEST_STRATEGY updated for Block 3 E2E.  
6. **Architecture alignment:** tree remains primary domain object; solver math not embedded in retrieval; comparison citation authority rules unchanged.

---

## I. Deferred items (explicit)

- Full member design engine, all limit states, lateral-torsional buckling completeness, connection design suite.  
- **UI** / canvas / chat.  
- **OCR** / scanned PDFs.  
- **Reference** resolution service for comparison traces.  
- Multi-revision diff UI and golden file regression **product** workflow.  
- LLM-assisted explanation layer with guardrails.  
- Cost estimation, fabrication quotes, optimization.

---

## J. Blocking questions (minimum)

1. **Units:** Confirm whether Block 3 calculations use **SI-only** for the first slice or dual support — affects assumption schema and test fixtures.  
2. **Optional rolled/built-up branch:** Confirm **four** required alternatives vs **five** in the first decision — affects workflow API and E2E assertions.  

If unresolved, defaults: **SI**, **four alternatives** (optional fifth behind explicit API flag).

---

## Document control

- **Vision guardrails:** Preserved from product/architecture docs; no drift without ADR.  
- **Next step after approval:** implementation in milestone order M2 → M7, with M1 documentation already delivered in planning phase.
