# Block 2 — Implementation plan

**Status:** Planning artifact (Block 2).  
**Scope:** This document defines *what* to build and in *what order* for Block 2. It does not replace `docs/00–03`, `docs/adr/ADR-001-local-first-architecture.md`, or `docs/02_master_data_model.md`.

---

## 1. Vision guardrails (non-negotiable)

| Principle | Implication for Block 2 |
|-----------|-------------------------|
| **Tree-first** | The decision/calculation tree (`Branch`, `Node`, related entities) is the primary domain object. Persistence, ingestion, retrieval, and comparison serve the tree—not the reverse. |
| **Document-first & citation-first** | No technical claim is authoritative without traceable document evidence. Retrieval returns **citation payloads**, not “answers” that imply certainty without evidence. |
| **Deterministic calculation vs LLM** | Solver/calculation logic stays in deterministic code paths. Any future LLM layer may propose or explain; it must not replace audited calculations or fabricate citations. |
| **Discarded branches** | Branches in `discarded` (and related) states remain **persisted, recoverable, and comparable**; discard is not delete. |
| **Normativa activa** | `ActiveCodeContext` / project standard family defines a **hard filter** for retrieval and design-facing behavior: inactive or out-of-scope standards must not be mixed silently into authoritative results. |

---

## 2. Execution order — mapping to `cursor_prompts/`

Implement Block 2 **strictly in this sequence**. Each prompt is a milestone boundary; complete and stop per prompt before starting the next.

| Order | Prompt file | Milestone name |
|-------|-------------|----------------|
| 1 | `cursor_prompts/02_repo_workflow_and_governance_prompt.txt` | Repository workflow & governance |
| 2 | `cursor_prompts/03_project_persistence_prompt.txt` | Project persistence & versioning |
| 3 | `cursor_prompts/04_tree_expansion_and_state_prompt.txt` | Tree expansion, branch state, node lifecycle |
| 4 | `cursor_prompts/05_document_ingestion_prompt.txt` | Local document ingestion |
| 5 | `cursor_prompts/06_document_retrieval_and_citation_prompt.txt` | Local retrieval & authoritative citations |
| 6 | `cursor_prompts/07_branch_comparison_v1_prompt.txt` | Branch comparison v1 |
| 7 | `cursor_prompts/08_validation_and_integration_prompt.txt` | Validation & integration pass |

**Dependency chain:** 02 → 03 → 04 → (05 ∥ preparatory) → 05 complete → 06 → 07 → 08.  
*Note:* 05 must complete before 06; 04 should not depend on ingestion (per prompt non-goals).

---

## 3. Traceability matrix — MVP capability → milestone → files → test intent

MVP capabilities are drawn from `docs/03_mvp_scope.md`. This matrix ties them to Block 2 milestones and concrete touchpoints.  
**Legend:** **M1** = prompt 02 … **M7** = prompt 08.

| MVP capability (from `docs/03_mvp_scope.md`) | Milestone | Primary files / locations (create or modify) | Test intent |
|---------------------------------------------|-----------|-----------------------------------------------|-------------|
| **Proyecto:** crear proyecto local | M2 | `src/structural_tree_app/services/project_service.py`, `src/structural_tree_app/storage/json_repository.py`, `schemas/project.schema.json`, workspace layout under e.g. `workspace/{project_id}/` | Create/load/save round-trip; bad payload rejected; revision list consistent |
| **Proyecto:** definir normativa activa | M2, M5 | `domain/models.py` (`ActiveCodeContext`), persistence for project + revisions, M5 retrieval filters | Persist/load `active_code_context`; retrieval respects standard family filter |
| **Proyecto:** definir unidades e idioma | M2 | `Project` fields in `domain/models.py`, `schemas/project.schema.json`, persisted `project.json` | Round-trip preserves `unit_system`, `language` |
| **Proyecto:** asociar documentos autorizados | M2, M4 | `authorized_document_ids` on project; `documents/` in workspace; `services/document_service.py` | Project lists doc IDs; ingestion registers docs into project boundary |
| **Árbol:** crear nodo raíz, generar alternativas, activar rama, conservar descartadas, reactivar, clonar | M3 | `services/tree_service.py`, `domain/enums.py`, `domain/models.py`, `schemas/node.schema.json`, persistence `tree/` | State transitions valid; discard ≠ delete; reopen/clone round-trip; subtree integrity |
| **Documentos:** registrar corpus y fragmentos con metadatos de cita | M4 | `document_service.py`, chunk/fragment store under `documents/`, align with `Document` / `DocumentFragment` | Ingest deterministically; text-extractable PDFs only; chunks have stable IDs; non-extractable PDF returns structured status (see M4 spec) |
| **Documentos:** abrir referencia desde nodo o cálculo | M5 | Retrieval service module (e.g. `services/retrieval_service.py` or extend `document_service.py`), `Reference` linkage from nodes/calculaciones | Retrieval returns citation payload; insufficient-evidence path structured |
| **Cálculo:** hipótesis, variables, cálculos deterministas, comprobaciones | M3 (partial), later blocks | `domain/models.py` (`Calculation`, `Check`, `Assumption`), **no LLM** in calculation path | Calculations persist; optional: unit tests for pure deterministic helpers when introduced |
| **Comparación:** comparar ramas por criterios homogéneos | M6 | `services/` comparison module (e.g. `branch_comparison_service.py`), `domain/models.py` (`Branch`) | Compare ≥2 branches; stable serializable output; discarded branches included |
| **Salida:** historial de cambios del árbol | M2, M3 | `VersionRecord`, revision snapshots, tree persistence | Revision history lists changes; rollback via loading prior revision |
| **Governance / auditability** | M1 | `docs/implementation/BLOCK_2_STATUS.md`, `CONTRIBUTING.md`, `.gitignore`, optional `pyproject.toml` / Makefile | Repo imports cleanly; documented commands work |
| **End-to-end Block 2 coherence** | M7 | `docs/05_block_2_validation_report.md` (created in M7 per prompt 08), tests under `tests/` | Single scripted flow: project → tree → ingest → retrieve → compare |

---

## 4. Milestone specifications

### M1 — Repository workflow & governance (`cursor_prompts/02_...`)

**Objectives:** Predictable dev workflow, minimal audit trail, no feature logic.

| Item | Detail |
|------|--------|
| **Create** | `docs/implementation/` (if missing), `docs/implementation/BLOCK_2_STATUS.md`, `CONTRIBUTING.md`; root `.gitignore`; optional `pyproject.toml`, optional `Makefile` or task runner **only if** commands are real and tested |
| **Modify** | `README.md` — Block 2 execution flow |
| **Dependencies** | None |
| **Rollback** | Revert docs/config commits; no persisted user data yet |
| **Risks** | Tooling churn — keep minimal per prompt |

**Test intent:** `python -c` import of package; any Makefile/task targets executed once successfully; record in `docs/CHANGELOG.md`.

---

### M2 — Project persistence & versioning (`cursor_prompts/03_...`)

**Objectives:** Controlled on-disk project layout; revision identity separate from project identity; save/load/save-as-revision.

| Item | Detail |
|------|--------|
| **Suggested layout** (align with prompt 03) | `workspace/{project_id}/project.json`, `revisions/`, `tree/`, `documents/`, `exports/` |
| **Create / modify** | `storage/json_repository.py` (or successor), `services/project_service.py`, new revision model if not present, `schemas/project.schema.json`, optional JSON Schema for revision metadata |
| **Dependencies** | M1 complete |
| **Rollback** | Copy `workspace/` before migration; versioned `revisions/` allow loading prior snapshot |
| **Risks** | Schema drift vs `domain/models.py` — validate at boundaries |

**Test intent:** create/load/save/revision; example migration from `examples/example_project.json`; corrupt input fails safe; round-trip field preservation.

---

### M3 — Tree expansion & branch state (`cursor_prompts/04_...`)

**Objectives:** Tree as persisted domain object; full branch lifecycle; discarded branches retained.

| Item | Detail |
|------|--------|
| **Modify / create** | `services/tree_service.py`, persistence under `tree/`, `domain/enums.py` / `models.py` as needed, `schemas/node.schema.json` |
| **Operations (target)** | `create_root_problem`, add child/decision options, activate/discard/reopen/clone branch, subtree read, list paths — per prompt 04 |
| **Dependencies** | M2 |
| **Rollback** | Reload project revision from M2; avoid destructive deletes of branch records |
| **Risks** | Invalid state transitions — centralize transition rules |

**Test intent:** branch discard/reopen/clone; subtree integrity; persistence round-trip; invalid transitions rejected.

---

### M4 — Local document ingestion (`cursor_prompts/05_...`)

**Objectives:** User-approved local documents only; chunked units with citation-oriented metadata; modular pipeline (import → normalize → segment → persist).

**Block 2 policy — no OCR:** OCR is **out of scope** for Block 2. Ingestion supports **text-extractable PDFs** (and plain text sources as defined in implementation). If a PDF has no extractable text layer, return a **structured failure status** (e.g. `unsupported_document_for_ingestion` or `ocr_deferred`) and **do not** silently ingest empty content. OCR may be evaluated in a **later block** if needed.

| Item | Detail |
|------|--------|
| **Create / modify** | `services/document_service.py`, storage under `documents/`, chunk/fragment representation (align with `Document` / `DocumentFragment` in `docs/02_master_data_model.md`) |
| **Dependencies** | M2 (project boundary); not blocked by M3 for basic ingest if prompt allows — **prefer** M3 complete so nodes can reference docs later |
| **Rollback** | Remove document artifacts from `documents/`; re-import; project `authorized_document_ids` consistency checks |
| **Risks** | Scanned/image-only PDFs will fail until a future OCR milestone — explicit status codes avoid false confidence |

**Test intent:** ingest ≥1 text-extractable PDF or text file; metadata + chunks persisted; duplicate policy deterministic; chunk IDs stable where specified; **non-text-extractable PDF** yields structured status, not silent empty ingest.

---

### M5 — Local retrieval & citations (`cursor_prompts/06_...`)

**Objectives:** Search only approved ingested corpus; **normativa activa** hard filter; citation payloads; structured “no evidence” response.

| Item | Detail |
|------|--------|
| **Create / modify** | New retrieval module; wire to chunks; `ActiveCodeContext` filters; no LLM |
| **Dependencies** | M4 |
| **Rollback** | Disable retrieval feature flag (if any); corpus files unchanged |
| **Risks** | Accidentally searching outside `allowed_document_ids` / inactive standards — enforce in service layer |

**Test intent:** lexical search hits; filter by standard family / `document_id`; citation object fields complete; insufficient-evidence path explicit.

---

### M6 — Branch comparison v1 (`cursor_prompts/07_...`)

**Objectives:** Domain-level comparison object; read-only; discarded branches allowed.

| Item | Detail |
|------|--------|
| **Create / modify** | e.g. `services/branch_comparison_service.py`; use tree + optional calculation/citation counts |
| **Dependencies** | M3; M5 helps for citation counts |
| **Rollback** | N/A (read-only service) |
| **Risks** | Placeholder metrics — document which fields are stubbed vs real |

**Test intent:** compare ≥2 branches; output JSON-serializable and stable; missing metrics safe defaults.

---

### M7 — Validation & integration (`cursor_prompts/08_...`)

**Objectives:** End-to-end coherence; documented validation; no Block 3 / UI scope creep.

| Item | Detail |
|------|--------|
| **Create** | `docs/05_block_2_validation_report.md` |
| **Modify** | `README.md`, `docs/implementation/BLOCK_2_STATUS.md`, `docs/CHANGELOG.md`, `docs/FAIL_LOG.md` as needed, integration tests |
| **Dependencies** | M1–M6 |
| **Rollback** | Document issues; contained fixes only per prompt 08 |

**Test intent:** integrated scenario covering persistence, tree, ingest, retrieve, compare; gaps listed in validation report.

---

## 5. Cross-cutting: schemas & validation

- Validate JSON at **save/load** boundaries against `schemas/*.schema.json` where entities map cleanly; extend schemas if `domain/models.py` gains required fields — **keep schemas and dataclasses in sync** (`docs/02_master_data_model.md` is source of meaning).
- `VersionRecord` and revision folders are the backbone for **recoverability** and audit.

---

## 6. Open questions (blockers only)

*None.* OCR scope for Block 2 is decided: **no OCR**; see M4 policy above.

---

## 7. Assumptions

| Assumption | Status | Notes |
|------------|--------|------|
| **A1** | **Approved** | Single workspace root for all projects (e.g. `./workspace`), not multi-root until specified. |
| **A2** | **Approved** | M5: **lexical** retrieval is mandatory; **semantic** retrieval remains deferred/optional. |
| **A3** | Active | External monorepo or root `Webb/` conventions (VMP, etc.) are **out of scope** for Block 2 implementation unless already reflected inside `structural_tree_app_foundation/`. |

---

## 8. What to execute next (after this plan is accepted)

1. Run **`cursor_prompts/02_repo_workflow_and_governance_prompt.txt`** (M1).  
2. Then **03** → **04** → **05** → **06** → **07** → **08** in order, updating `docs/implementation/BLOCK_2_STATUS.md` and `docs/CHANGELOG.md` per each prompt’s stop criteria.

---

*End of Block 2 implementation plan document.*
