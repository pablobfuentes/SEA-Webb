"""FastAPI dependencies — thin wiring to existing services (no domain logic)."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from structural_tree_app.services.project_service import ProjectService

from structural_tree_app.workbench.config import get_workspace_path

SESSION_PROJECT_KEY = "project_id"
# Last non-empty assist retrieval query for this session (same project). Used for cross-surface handoff.
SESSION_LAST_ASSIST_QUERY_KEY = "last_assist_query"


def get_project_service() -> ProjectService:
    """Workspace root matches ``ProjectService`` / on-disk layout."""
    return ProjectService(get_workspace_path())


def _session_project_id(request: Request) -> str | None:
    """Pointer only — must be validated by ``load_project`` before use."""
    raw = request.session.get(SESSION_PROJECT_KEY)
    return raw if isinstance(raw, str) and raw else None


ProjectServiceDep = Annotated[ProjectService, Depends(get_project_service)]
SessionProjectIdDep = Annotated[str | None, Depends(_session_project_id)]
