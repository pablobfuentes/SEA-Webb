"""Run the workbench: ``python -m structural_tree_app.workbench``."""

from __future__ import annotations

import os

import uvicorn


def main() -> None:
    host = os.environ.get("WORKBENCH_HOST", "127.0.0.1")
    port = int(os.environ.get("WORKBENCH_PORT", "8000"))
    uvicorn.run(
        "structural_tree_app.workbench.app:app",
        host=host,
        port=port,
        reload=os.environ.get("WORKBENCH_RELOAD", "").lower() in ("1", "true", "yes"),
    )


if __name__ == "__main__":
    main()
