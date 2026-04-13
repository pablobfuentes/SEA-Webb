# Persistence hardening — explicit tracking

Cross-cutting requirements for the local JSON workspace. Status is updated as capabilities land.

| Requirement | Status | Implementation notes |
|-------------|--------|----------------------|
| **1. Revision immutability (write-once)** | Enforced | `ProjectService._write_revision_snapshot` raises if `revisions/{revision_id}/meta.json` already exists. Reusing a revision id fails with `ProjectPersistenceError`. Checksum/manifest deferred (see `docs/TEST_STRATEGY.md` §7). |
| **2. Tree referential integrity** | Partial | `validate_tree_integrity(store, project)` reports errors (broken parent/child, missing branch/node/decision/alt refs) and warnings (orphan nodes, reverse-link mismatches). Call after load/save or in tests; not yet wired to every automatic save. |
| **3. Revision isolation** | Enforced | `load_revision_bundle(project_id, revision_id)` returns `RevisionBundle`: `project` and `assumptions` from revision snapshots only; `tree_store` is `TreeStore.for_revision_snapshot(...)` pointing at `revisions/{id}/tree`, not live `tree/`. |

Tests: `tests/test_persistence_hardening.py`, `tests/test_tree_workspace.py` (integrity), `tests/test_document_ingestion.py`.
