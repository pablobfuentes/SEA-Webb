"""
Read-only projection of persisted simple-span workflow state for workbench templates.

Loads entities via ``TreeStore`` / ``ProjectService`` only — no business rules beyond
what is already stored (same category as a thin read model / DTO).
"""

from __future__ import annotations

from dataclasses import dataclass

from structural_tree_app.domain.enums import NodeType
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.storage.tree_store import TreeStore


@dataclass(frozen=True)
class AlternativeWorkbenchRow:
    id: str
    title: str
    catalog_key: str | None
    suggested: bool
    suggestion_rank: int | None


@dataclass(frozen=True)
class SimpleSpanWorkflowWorkbenchSnapshot:
    """Mirrors identifiers exposed by ``SimpleSpanWorkflowResult`` where applicable."""

    workflow_id: str
    main_branch_id: str
    root_problem_node_id: str
    root_problem_title: str
    decision_node_id: str
    decision_id: str
    decision_prompt: str
    alternatives: tuple[AlternativeWorkbenchRow, ...]


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

    alts: list[AlternativeWorkbenchRow] = []
    for aid in decision_row.alternative_ids:
        a = store.load_alternative(aid)
        ck = a.catalog_key.strip() if a.catalog_key else None
        alts.append(
            AlternativeWorkbenchRow(
                id=a.id,
                title=a.title,
                catalog_key=ck,
                suggested=bool(a.suggested),
                suggestion_rank=a.suggestion_rank,
            )
        )

    from structural_tree_app.domain.simple_span_workflow import WORKFLOW_ID

    return SimpleSpanWorkflowWorkbenchSnapshot(
        workflow_id=WORKFLOW_ID,
        main_branch_id=root.branch_id,
        root_problem_node_id=root.id,
        root_problem_title=root.title,
        decision_node_id=decision_node_id,
        decision_id=decision_row.id,
        decision_prompt=decision_row.prompt,
        alternatives=tuple(alts),
    )
