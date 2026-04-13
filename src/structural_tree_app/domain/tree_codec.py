from __future__ import annotations

from dataclasses import asdict
from typing import Any

from structural_tree_app.domain.enums import BranchState, NodeState, NodeType, SourceType
from structural_tree_app.domain.models import Alternative, Branch, Decision, Node


def branch_to_dict(branch: Branch) -> dict[str, Any]:
    d = asdict(branch)
    d["state"] = branch.state.value if isinstance(branch.state, BranchState) else str(branch.state)
    return d


def branch_from_dict(data: dict[str, Any]) -> Branch:
    st = data["state"]
    if isinstance(st, str):
        st = BranchState(st)
    return Branch(
        project_id=data["project_id"],
        title=data["title"],
        description=data.get("description", ""),
        origin_decision_node_id=data.get("origin_decision_node_id"),
        root_node_id=data.get("root_node_id"),
        state=st,
        parent_branch_id=data.get("parent_branch_id"),
        cloned_from_branch_id=data.get("cloned_from_branch_id"),
        reactivated_from_branch_id=data.get("reactivated_from_branch_id"),
        comparison_tags=list(data.get("comparison_tags", [])),
        id=data["id"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def node_to_dict(node: Node) -> dict[str, Any]:
    d = asdict(node)
    d["node_type"] = node.node_type.value if isinstance(node.node_type, NodeType) else str(node.node_type)
    d["state"] = node.state.value if isinstance(node.state, NodeState) else str(node.state)
    return d


def node_from_dict(data: dict[str, Any]) -> Node:
    nt = data["node_type"]
    if isinstance(nt, str):
        nt = NodeType(nt)
    st = data["state"]
    if isinstance(st, str):
        st = NodeState(st)
    return Node(
        project_id=data["project_id"],
        branch_id=data["branch_id"],
        node_type=nt,
        title=data["title"],
        description=data.get("description", ""),
        parent_node_id=data.get("parent_node_id"),
        state=st,
        order_index=int(data.get("order_index", 0)),
        depth=int(data.get("depth", 0)),
        id=data["id"],
        child_node_ids=list(data.get("child_node_ids", [])),
        linked_reference_ids=list(data.get("linked_reference_ids", [])),
        linked_calculation_ids=list(data.get("linked_calculation_ids", [])),
        linked_assumption_ids=list(data.get("linked_assumption_ids", [])),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def decision_to_dict(decision: Decision) -> dict[str, Any]:
    return asdict(decision)


def decision_from_dict(data: dict[str, Any]) -> Decision:
    return Decision(
        project_id=data["project_id"],
        decision_node_id=data["decision_node_id"],
        prompt=data["prompt"],
        criterion_ids=list(data.get("criterion_ids", [])),
        alternative_ids=list(data.get("alternative_ids", [])),
        selected_alternative_id=data.get("selected_alternative_id"),
        status=data.get("status", "open"),
        rationale=data.get("rationale", ""),
        id=data["id"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def alternative_to_dict(alt: Alternative) -> dict[str, Any]:
    return asdict(alt)


def alternative_from_dict(data: dict[str, Any]) -> Alternative:
    return Alternative(
        decision_id=data["decision_id"],
        title=data["title"],
        description=data.get("description", ""),
        pros=list(data.get("pros", [])),
        cons=list(data.get("cons", [])),
        constraints=list(data.get("constraints", [])),
        next_expected_decisions=list(data.get("next_expected_decisions", [])),
        status=data.get("status", "candidate"),
        reactivatable=bool(data.get("reactivatable", True)),
        id=data["id"],
    )


__all__ = [
    "alternative_from_dict",
    "alternative_to_dict",
    "branch_from_dict",
    "branch_to_dict",
    "decision_from_dict",
    "decision_to_dict",
    "node_from_dict",
    "node_to_dict",
]
