"""Repository-root resolution for loading JSON schemas and assets."""

from __future__ import annotations

from pathlib import Path


def repository_root() -> Path:
    """Root of `structural_tree_app_foundation` (contains `schemas/`, `src/`)."""
    # src/structural_tree_app/paths.py -> parents[2] == repo root
    return Path(__file__).resolve().parents[2]


def schemas_dir() -> Path:
    return repository_root() / "schemas"
