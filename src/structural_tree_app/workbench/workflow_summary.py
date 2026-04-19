"""
Read-only projection of persisted simple-span workflow state for workbench templates.

Loads entities via ``TreeStore`` / ``ProjectService`` only — no business rules beyond
what is already stored (same category as a thin read model / DTO).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from structural_tree_app.domain.enums import NodeType
from structural_tree_app.domain.simple_span_workflow import SUGGESTED_TOP_K, WORKFLOW_ID
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.storage.tree_store import TreeStore


@dataclass(frozen=True)
class CharacterizationItemWorkbenchRow:
    """One persisted characterization dict, normalized for templates (escape in Jinja)."""

    text: str
    polarity: str
    provenance: str
    reference_id: str | None
    retrieval_query: str | None
    citation_authority: str | None


@dataclass(frozen=True)
class AlternativeWorkbenchRow:
    id: str
    title: str
    description: str
    catalog_key: str | None
    suggested: bool
    suggestion_rank: int | None
    suggestion_score: float | None
    suggestion_provenance: str
    characterization_items: tuple[CharacterizationItemWorkbenchRow, ...]


@dataclass(frozen=True)
class SimpleSpanWorkflowWorkbenchSnapshot:
    """Mirrors identifiers exposed by ``SimpleSpanWorkflowResult`` where applicable."""

    workflow_id: str
    suggested_top_k: int
    main_branch_id: str
    root_problem_node_id: str
    root_problem_title: str
    decision_node_id: str
    decision_id: str
    decision_prompt: str
    alternatives: tuple[AlternativeWorkbenchRow, ...]
    suggested_alternatives: tuple[AlternativeWorkbenchRow, ...]
    other_eligible_alternatives: tuple[AlternativeWorkbenchRow, ...]


def _characterization_row_from_dict(d: dict[str, Any]) -> CharacterizationItemWorkbenchRow:
    return CharacterizationItemWorkbenchRow(
        text=str(d.get("text", "")),
        polarity=str(d.get("polarity", "")),
        provenance=str(d.get("provenance", "")),
        reference_id=d.get("reference_id") if d.get("reference_id") else None,
        retrieval_query=d.get("retrieval_query") if d.get("retrieval_query") else None,
        citation_authority=d.get("citation_authority") if d.get("citation_authority") else None,
    )


def _characterization_items_from_alt(raw: list[dict[str, Any]]) -> tuple[CharacterizationItemWorkbenchRow, ...]:
    out: list[CharacterizationItemWorkbenchRow] = []
    for item in raw:
        if isinstance(item, dict):
            out.append(_characterization_row_from_dict(item))
    return tuple(out)


def load_simple_span_workbench_snapshot(
    project_service: ProjectService, project_id: str
) -> SimpleSpanWorkflowWorkbenchSnapshot | None:
    """
    Return ``None`` if the project has no root node or no simple-span decision subtree found.
    """
    project = project_service.load_project(project_id)
    if not project.root_node_id:
        return None

    store = TreeStore.for_live_project(project_service.repository, project_id)
    root = store.load_node(project.root_node_id)
    decision_node_id: str | None = None
    for cid in root.child_node_ids:
        node = store.load_node(cid)
        if node.node_type == NodeType.DECISION:
            decision_node_id = node.id
            break
    if not decision_node_id:
        return None

    decision_row = None
    for did in store.list_decision_ids():
        d = store.load_decision(did)
        if d.decision_node_id == decision_node_id:
            decision_row = d
            break
    if decision_row is None:
        return None

    def _sort_alternatives(rows: list[AlternativeWorkbenchRow]) -> tuple[AlternativeWorkbenchRow, ...]:
        """Display order: suggested by rank, then eligible-not-suggested by title."""
        sug = [r for r in rows if r.suggested]
        sug.sort(key=lambda r: (r.suggestion_rank is None, r.suggestion_rank if r.suggestion_rank is not None else 10**9))
        other = [r for r in rows if not r.suggested]
        other.sort(key=lambda r: r.title.lower())
        return tuple(sug + other)

    alts: list[AlternativeWorkbenchRow] = []
    for aid in decision_row.alternative_ids:
        a = store.load_alternative(aid)
        ck = a.catalog_key.strip() if a.catalog_key else None
        items = _characterization_items_from_alt(
            a.characterization_items if isinstance(a.characterization_items, list) else []
        )
        alts.append(
            AlternativeWorkbenchRow(
                id=a.id,
                title=a.title,
                description=a.description,
                catalog_key=ck,
                suggested=bool(a.suggested),
                suggestion_rank=a.suggestion_rank,
                suggestion_score=a.suggestion_score,
                suggestion_provenance=str(a.suggestion_provenance or ""),
                characterization_items=items,
            )
        )

    ordered = _sort_alternatives(alts)
    suggested_only = tuple(r for r in ordered if r.suggested)
    other_only = tuple(r for r in ordered if not r.suggested)
    return SimpleSpanWorkflowWorkbenchSnapshot(
        workflow_id=WORKFLOW_ID,
        suggested_top_k=SUGGESTED_TOP_K,
        main_branch_id=root.branch_id,
        root_problem_node_id=root.id,
        root_problem_title=root.title,
        decision_node_id=decision_node_id,
        decision_id=decision_row.id,
        decision_prompt=decision_row.prompt,
        alternatives=ordered,
        suggested_alternatives=suggested_only,
        other_eligible_alternatives=other_only,
    )
