"""Workbench configuration — workspace root only; no domain state."""

from __future__ import annotations

import os
from pathlib import Path

ENV_WORKSPACE = "STRUCTURAL_TREE_WORKSPACE"
ENV_SESSION_SECRET = "WORKBENCH_SESSION_SECRET"
DEFAULT_WORKSPACE = "workspace"


def get_workspace_path() -> Path:
    """
    Resolved absolute path to the JSON workspace root (same contract as ProjectService).

    Override with STRUCTURAL_TREE_WORKSPACE (relative or absolute). Defaults to ``workspace``
    under the current working directory when the process started.
    """
    raw = os.environ.get(ENV_WORKSPACE, DEFAULT_WORKSPACE).strip()
    return Path(raw).expanduser().resolve()


def get_templates_dir() -> Path:
    """Directory containing Jinja2 templates for the workbench."""
    return Path(__file__).resolve().parent / "templates"


def get_session_secret() -> str:
    """Secret for signed cookies; override in non-dev environments."""
    return os.environ.get(ENV_SESSION_SECRET, "dev-insecure-workbench-session-secret")
