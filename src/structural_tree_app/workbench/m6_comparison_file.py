"""Persist last M6 comparison JSON on disk (session cookies are too small for full result)."""

from __future__ import annotations

from typing import Any

from structural_tree_app.storage.json_repository import JsonRepository

REL_NAME = "workbench_m6_last_comparison.json"


def save_last_comparison(
    repository: JsonRepository,
    project_id: str,
    revision_id: str | None,
    result_dict: dict[str, Any],
) -> None:
    repository.write(
        f"{project_id}/{REL_NAME}",
        {"project_id": project_id, "revision_id": revision_id, "result": result_dict},
    )


def load_last_comparison_bundle(repository: JsonRepository, project_id: str) -> dict[str, Any] | None:
    rel = f"{project_id}/{REL_NAME}"
    if not repository.exists(rel):
        return None
    return repository.read(rel)
