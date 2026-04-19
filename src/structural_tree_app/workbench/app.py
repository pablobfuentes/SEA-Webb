"""FastAPI application factory for the Block 4A validation workbench."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse, RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from structural_tree_app.workbench.config import ENV_WORKSPACE, get_session_secret, get_workspace_path
from structural_tree_app.workbench.corpus_pages import router as corpus_router
from structural_tree_app.workbench.pages import router as workbench_router


def create_app() -> FastAPI:
    app = FastAPI(
        title="Structural Tree — validation workbench",
        description="Block 4A: thin UI over structural_tree_app services (not production UI).",
        version="0.1.0",
    )
    app.add_middleware(
        SessionMiddleware,
        secret_key=get_session_secret(),
        session_cookie="workbench_session",
        max_age=14 * 24 * 3600,
        same_site="lax",
    )
    app.include_router(workbench_router)
    app.include_router(corpus_router)

    @app.get("/health", tags=["meta"])
    def health() -> JSONResponse:
        return JSONResponse(
            {
                "status": "ok",
                "service": "structural_tree_app.workbench",
                "workspace_path": str(get_workspace_path()),
                "workspace_env": ENV_WORKSPACE,
            }
        )

    @app.get("/", tags=["meta"])
    def root() -> RedirectResponse:
        return RedirectResponse(url="/workbench", status_code=307)

    return app


# Uvicorn: ``uvicorn structural_tree_app.workbench.app:app``
app = create_app()
