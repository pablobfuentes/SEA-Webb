"""
Static presentation labels for ``characterization_items[].provenance`` values.

Keys are backend strings from ``domain.characterization_provenance`` — this module
does not reinterpret domain rules; it only maps known values to short UI copy.
Unknown values fall back to monospace raw display in templates.
"""

from __future__ import annotations

from structural_tree_app.domain.characterization_provenance import (
    PROVENANCE_MANUAL_PLACEHOLDER,
    PROVENANCE_NOT_YET_EVIDENCED,
    PROVENANCE_RETRIEVAL_BACKED,
    PROVENANCE_WORKFLOW_HEURISTIC,
)

# Short headings for validation workbench (not product copy).
PROVENANCE_HEADING: dict[str, str] = {
    PROVENANCE_RETRIEVAL_BACKED: "Retrieval-backed",
    PROVENANCE_WORKFLOW_HEURISTIC: "Workflow heuristic (not design adequacy)",
    PROVENANCE_MANUAL_PLACEHOLDER: "Manual / placeholder",
    PROVENANCE_NOT_YET_EVIDENCED: "Not yet evidenced (no corpus passage)",
}


def provenance_heading(raw: str) -> str:
    """Human heading for a known provenance string; otherwise return empty (caller shows raw)."""
    return PROVENANCE_HEADING.get(raw, "")
