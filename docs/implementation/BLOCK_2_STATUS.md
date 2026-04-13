# Block 2 — Status tracker

Single source of truth for milestone completion inside `structural_tree_app_foundation`.  
Execution order: `cursor_prompts/02` → `03` → … → `08`.

| Milestone | Prompt | Status | Notes |
|-----------|--------|--------|-------|
| M1 — Repo workflow & governance | `cursor_prompts/02_repo_workflow_and_governance_prompt.txt` | **Complete** | `docs/implementation/`, `BLOCK_2_STATUS.md`, root `CONTRIBUTING.md`, `.gitignore`, `pyproject.toml`, `Makefile`, `README.md` Block 2 flow |
| M2 — Project persistence | `03_project_persistence_prompt.txt` | **Complete** | Workspace `{workspace}/{project_id}/`: `project.json`, `assumptions.json`, `revisions/`, `tree/`, `documents/`, `exports/`; atomic JSON writes; revision snapshots include `project_snapshot.json`, `assumptions_snapshot.json`, `tree/` copy; JSON Schema at boundaries |
| M3 — Tree expansion & branch state | `04_tree_expansion_and_state_prompt.txt` | **Complete** | `tree/branches|nodes|decisions|alternatives/*.json`; `TreeWorkspace` lifecycle (activate/discard/reopen/clone), subtree & paths; tests in `tests/test_tree_workspace.py` |
| M4 — Document ingestion | `05_document_ingestion_prompt.txt` | **Complete** | `DocumentIngestionService`, `documents/{doc_id}/document.json` + `fragments.json`; PDF via `pypdf` text layer; non-extractable PDF → `ocr_deferred`; persistence hardening: `PERSISTENCE_HARDENING.md`, `load_revision_bundle`, `validate_tree_integrity` |
| M5 — Retrieval & citations | `06_document_retrieval_and_citation_prompt.txt` | **Complete** | `DocumentRetrievalService` lexical search; `CitationPayload`; `insufficient_evidence`; filters; `tests/test_retrieval.py` |
| M6 — Branch comparison v1 | `07_branch_comparison_v1_prompt.txt` | **Complete** | `BranchComparisonService` (`services/branch_comparison.py`); structured `BranchComparisonResult` + JSON `to_dict()`; tests `tests/test_branch_comparison.py`; see CHANGELOG M6 report (criteria storage, quantitative/qualitative, discarded branches, citation traces) |
| M7 — Validation & integration | `08_validation_and_integration_prompt.txt` | **Complete** | `docs/05_block_2_validation_report.md`; integrated test `tests/test_block2_integration.py`; README walkthrough; CHANGELOG M7 |

**Last updated:** M7 completion (validation & integration — Block 2 closed in this repo).

**See also:** `docs/implementation/PERSISTENCE_HARDENING.md` (revision immutability, tree integrity, revision isolation).
