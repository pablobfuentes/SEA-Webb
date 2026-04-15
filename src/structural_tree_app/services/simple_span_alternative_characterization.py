from __future__ import annotations

from dataclasses import replace
from typing import Any, cast

from structural_tree_app.domain.alternative_characterization import AlternativeCharacterizationItem, Polarity
from structural_tree_app.domain.characterization_provenance import (
    PROVENANCE_MANUAL_PLACEHOLDER,
    PROVENANCE_NOT_YET_EVIDENCED,
    PROVENANCE_RETRIEVAL_BACKED,
    PROVENANCE_WORKFLOW_HEURISTIC,
)
from structural_tree_app.domain.models import Project, Reference
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.services.retrieval_service import CitationAuthority, DocumentRetrievalService
from structural_tree_app.services.tree_workspace import TreeWorkspace

# Deterministic lexical queries per catalog key (structured workflow only; not adequacy checks).
RETRIEVAL_QUERY_BY_CATALOG_KEY: dict[str, str] = {
    "truss": "truss triangulation steel span",
    "castellated": "castellated cellular beam openings",
    "tapered": "tapered variable inertia beam",
    "rolled": "rolled beam flexure steel",
}

# Narrow workflow-heuristic templates (v1). Not normative; not design adequacy.
_WORKFLOW_HEURISTIC_BY_KEY: dict[str, list[tuple[str, str]]] = {
    "truss": [
        (
            "pro",
            "Axial members can carry load efficiently over long spans (workflow heuristic v1; not a strength check).",
        ),
        (
            "con",
            "Connections and fabrication complexity are project-specific (workflow heuristic v1).",
        ),
    ],
    "castellated": [
        (
            "pro",
            "Web openings can reduce self-weight versus solid sections (workflow heuristic v1).",
        ),
        (
            "con",
            "Web-post and weld details require coordination (workflow heuristic v1).",
        ),
    ],
    "tapered": [
        (
            "pro",
            "Variable inertia can track bending demand qualitatively (workflow heuristic v1).",
        ),
        (
            "con",
            "Fabrication and plate work can add cost versus prismatic members (workflow heuristic v1).",
        ),
    ],
    "rolled": [
        (
            "pro",
            "Common rolled shapes are widely available and familiar to fabricators (workflow heuristic v1).",
        ),
        (
            "con",
            "Depth and weight may be less favorable than specialized systems for long spans (workflow heuristic v1).",
        ),
    ],
}

_MANUAL_PLACEHOLDER: dict[str, Any] = AlternativeCharacterizationItem(
    text="Additional project-specific pros/cons may be entered manually (placeholder; not evidence).",
    polarity="pro",
    provenance=PROVENANCE_MANUAL_PLACEHOLDER,
).to_dict()


def _workflow_items_for_key(catalog_key: str) -> list[dict[str, Any]]:
    pairs = _WORKFLOW_HEURISTIC_BY_KEY.get(catalog_key, [])
    out: list[dict[str, Any]] = []
    for polarity, text in pairs:
        out.append(
            AlternativeCharacterizationItem(
                text=text,
                polarity=cast(Polarity, polarity),
                provenance=PROVENANCE_WORKFLOW_HEURISTIC,
            ).to_dict()
        )
    return out


def _retrieval_item(
    project_id: str,
    ps: ProjectService,
    catalog_key: str,
    citation_authority: CitationAuthority,
) -> tuple[AlternativeCharacterizationItem | None, Reference | None]:
    q = RETRIEVAL_QUERY_BY_CATALOG_KEY.get(catalog_key)
    if not q:
        return None, None
    rsvc = DocumentRetrievalService(ps, project_id)
    resp = rsvc.search(q, citation_authority=citation_authority, limit=5)
    if resp.status != "ok" or not resp.hits:
        return None, None
    hit = resp.hits[0]
    ref = Reference(
        project_id=project_id,
        document_id=hit.document_id,
        fragment_id=hit.fragment_id,
        usage_type="alternative_characterization",
        citation_short=f"{hit.document_title} (chunk {hit.chunk_index})",
        citation_long=f"query={q!r}; authority={citation_authority}",
        quoted_context=hit.snippet,
    )
    item = AlternativeCharacterizationItem(
        text=f"Corpus excerpt (retrieval-backed; not a design conclusion): {hit.snippet[:280]}",
        polarity="pro",
        provenance=PROVENANCE_RETRIEVAL_BACKED,
        reference_id=ref.id,
        retrieval_query=q,
        citation_authority=citation_authority,
    )
    return item, ref


def _not_yet_evidenced_item(catalog_key: str, query: str | None) -> AlternativeCharacterizationItem:
    return AlternativeCharacterizationItem(
        text=(
            "No matching passage in the normative active primary corpus for the deterministic "
            f"retrieval query for {catalog_key!r} (not_yet_evidenced)."
        ),
        polarity="con",
        provenance=PROVENANCE_NOT_YET_EVIDENCED,
        retrieval_query=query,
        citation_authority="normative_active_primary",
    )


def build_characterization_payload_for_alternative(
    *,
    catalog_key: str,
    project_id: str,
    ps: ProjectService,
    citation_authority: CitationAuthority = "normative_active_primary",
) -> tuple[list[dict[str, Any]], list[Reference]]:
    """
    Build ordered, deterministic characterization items and any new Reference rows to persist.
    Retrieval uses the existing authority gate; insufficient evidence yields not_yet_evidenced.
    """
    items: list[dict[str, Any]] = []
    refs: list[Reference] = []

    items.extend(_workflow_items_for_key(catalog_key))
    items.append(dict(_MANUAL_PLACEHOLDER))

    q = RETRIEVAL_QUERY_BY_CATALOG_KEY.get(catalog_key)
    item, ref = _retrieval_item(project_id, ps, catalog_key, citation_authority)
    if item and ref:
        refs.append(ref)
        items.append(item.to_dict())
    else:
        items.append(_not_yet_evidenced_item(catalog_key, q).to_dict())

    return items, refs


def apply_simple_span_m4_characterization(
    tw: TreeWorkspace,
    decision_id: str,
    *,
    citation_authority: CitationAuthority = "normative_active_primary",
) -> None:
    """Persist M4 characterization for every alternative under the decision."""
    dec = tw.store.load_decision(decision_id)
    for aid in dec.alternative_ids:
        alt = tw.store.load_alternative(aid)
        key = alt.catalog_key
        if not key:
            continue
        items, refs = build_characterization_payload_for_alternative(
            catalog_key=key,
            project_id=tw.project.id,
            ps=tw.ps,
            citation_authority=citation_authority,
        )
        for ref in refs:
            tw.store.save_reference(ref)
        alt = replace(alt, characterization_items=items)
        tw.store.save_alternative(alt)
    tw.ps.save_project(tw.project)


def apply_m4_characterization_for_project(
    ps: ProjectService,
    project: Project,
    decision_id: str,
    *,
    citation_authority: CitationAuthority = "normative_active_primary",
) -> None:
    live = ps.load_project(project.id)
    tw = TreeWorkspace(ps, live)
    apply_simple_span_m4_characterization(tw, decision_id, citation_authority=citation_authority)


__all__ = [
    "RETRIEVAL_QUERY_BY_CATALOG_KEY",
    "apply_m4_characterization_for_project",
    "apply_simple_span_m4_characterization",
    "build_characterization_payload_for_alternative",
]
