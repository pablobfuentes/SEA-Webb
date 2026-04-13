# Contributing — structural_tree_app_foundation

Local-first Python core; no cloud services required for development.

## Block 2 execution order

Implement milestones **in sequence** using the Cursor prompts under `cursor_prompts/`:

1. `02_repo_workflow_and_governance_prompt.txt` — governance (no feature logic)
2. `03_project_persistence_prompt.txt`
3. `04_tree_expansion_and_state_prompt.txt`
4. `05_document_ingestion_prompt.txt`
5. `06_document_retrieval_and_citation_prompt.txt`
6. `07_branch_comparison_v1_prompt.txt`
7. `08_validation_and_integration_prompt.txt`

Stop after each prompt as specified. Track progress in `docs/implementation/BLOCK_2_STATUS.md`.

Authoritative planning: `docs/04_block_2_implementation_plan.md`, `docs/TEST_STRATEGY.md`.

## Engineering rules

- **Tree-first:** the decision/calculation tree is the primary domain object.
- **Document-first / citation-first:** retrieval and outputs must support traceable citations; no fabricated authority.
- **Deterministic calculations** stay separate from any future LLM layer.
- **Normativa activa** per project is a hard filter for retrieval (see `ActiveCodeContext`).
- **Block 2 ingestion:** text-extractable PDFs only; **no OCR** — non-extractable PDFs must return a structured status (`unsupported_document_for_ingestion` / `ocr_deferred`), not silent empty content.

## Logs (foundation repo only)

- Record notable changes in `docs/CHANGELOG.md`.
- Record failures and fixes during implementation in `docs/FAIL_LOG.md`.
- Do not mirror these to parent monorepo `workflow/` logs unless explicitly requested.

## Commits

- Prefer conventional commits: `feat:`, `fix:`, `docs:`, `chore:`.
- Keep commits scoped to one milestone or logical change.

## Local checks

From repository root:

```bash
set PYTHONPATH=src   # Windows CMD
# export PYTHONPATH=src   # Unix

python -c "import structural_tree_app; print('ok')"
```

Or with Make (Git Bash / Unix):

```bash
make import-check
```

After `pip install -e .`, imports work without `PYTHONPATH`.

## Tests

- When `tests/` exists: `python -m pytest` from repo root (`pyproject.toml` configures `pythonpath = src`).
- Follow `docs/TEST_STRATEGY.md`.
