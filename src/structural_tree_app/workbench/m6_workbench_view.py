"""Block 4A M6 — read-only view helpers for branch comparison (no domain logic)."""

from __future__ import annotations

from typing import Any

# Mirrors ``ComparisonFieldSource`` / plan §G — labels for template legend only.
COMPARISON_FIELD_SOURCE_LEGEND: tuple[tuple[str, str], ...] = (
    ("m5_deterministic_preliminary", "M5 preliminary deterministic workflow signal — not design adequacy."),
    ("branch_tree_derived", "Derived from persisted branch / tree rows (read-only)."),
    ("manual_placeholder", "Manual tag / placeholder — not authoritative."),
    ("document_trace_pending", "Reference ids present; full citation authority requires retrieval pipeline."),
)

METRIC_PROVENANCE_LEGEND: tuple[tuple[str, str], ...] = (
    ("computed", "Counted or derived by comparison service from stored rows."),
    ("derived_from_tree", "Read from tree node / branch records."),
    ("manual_tag", "Parsed from branch comparison_tags convention."),
    ("document_trace_pending", "Citation-adjacent; not normative until retrieval."),
    ("deterministic_preliminary", "M5 preliminary deterministic slice."),
)


def comparison_bundle_matches_view(
    bundle: dict[str, Any] | None,
    *,
    project_id: str,
    revision_id: str | None,
) -> bool:
    """Whether session-stored comparison may be shown for this page (live vs revision)."""
    if not bundle or not isinstance(bundle, dict):
        return False
    if bundle.get("project_id") != project_id:
        return False
    got = bundle.get("revision_id")
    if got is None and revision_id is None:
        return True
    return got == revision_id


def pick_comparison_dict_for_template(
    bundle: dict[str, Any] | None,
    *,
    project_id: str,
    revision_id: str | None,
) -> dict[str, Any] | None:
    if not comparison_bundle_matches_view(bundle, project_id=project_id, revision_id=revision_id):
        return None
    raw = bundle.get("result")
    return raw if isinstance(raw, dict) else None
