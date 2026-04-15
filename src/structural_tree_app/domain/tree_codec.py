from __future__ import annotations

from dataclasses import asdict
from typing import Any

from structural_tree_app.domain.enums import BranchState, NodeState, NodeType, SourceType
from structural_tree_app.domain.models import Alternative, Branch, Calculation, Check, Decision, Node, Reference


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
        origin_alternative_id=data.get("origin_alternative_id"),
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
        catalog_key=data.get("catalog_key", ""),
        characterization_items=list(data.get("characterization_items", [])),
        pros=list(data.get("pros", [])),
        cons=list(data.get("cons", [])),
        constraints=list(data.get("constraints", [])),
        next_expected_decisions=list(data.get("next_expected_decisions", [])),
        suggested=bool(data.get("suggested", False)),
        suggestion_rank=data.get("suggestion_rank"),
        suggestion_score=data.get("suggestion_score"),
        suggestion_provenance=data.get("suggestion_provenance", "workflow_heuristic"),
        status=data.get("status", "candidate"),
        reactivatable=bool(data.get("reactivatable", True)),
        id=data["id"],
    )


def canonicalize_json(obj: Any) -> Any:
    """Recursively sort dict keys for deterministic JSON-compatible payloads (lists preserve order)."""
    if isinstance(obj, dict):
        return {k: canonicalize_json(obj[k]) for k in sorted(obj.keys())}
    if isinstance(obj, list):
        return [canonicalize_json(x) for x in obj]
    return obj


def calculation_to_dict(calc: Calculation) -> dict[str, Any]:
    d = asdict(calc)
    d["inputs"] = canonicalize_json(d.get("inputs", {}))
    d["substitutions"] = canonicalize_json(d.get("substitutions", {}))
    d["result"] = canonicalize_json(d.get("result", {}))
    if d.get("dimensional_validation") is not None:
        d["dimensional_validation"] = canonicalize_json(d["dimensional_validation"])
    d["reference_ids"] = sorted(d.get("reference_ids", []))
    return canonicalize_json(d)


def calculation_from_dict(data: dict[str, Any]) -> Calculation:
    return Calculation(
        project_id=data["project_id"],
        node_id=data["node_id"],
        objective=data["objective"],
        method_label=data["method_label"],
        formula_text=data["formula_text"],
        inputs=dict(data.get("inputs", {})),
        substitutions=dict(data.get("substitutions", {})),
        result=dict(data.get("result", {})),
        formula_id=data.get("formula_id"),
        dimensional_validation=data.get("dimensional_validation"),
        reference_ids=list(data.get("reference_ids", [])),
        status=data.get("status", "draft"),
        id=data["id"],
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def check_to_dict(check: Check) -> dict[str, Any]:
    d = asdict(check)
    d["demand"] = canonicalize_json(d.get("demand", {}))
    d["capacity"] = canonicalize_json(d.get("capacity", {}))
    d["reference_ids"] = sorted(d.get("reference_ids", []))
    return canonicalize_json(d)


def check_from_dict(data: dict[str, Any]) -> Check:
    return Check(
        project_id=data["project_id"],
        node_id=data["node_id"],
        calculation_id=data["calculation_id"],
        check_type=data["check_type"],
        demand=dict(data.get("demand", {})),
        capacity=dict(data.get("capacity", {})),
        utilization_ratio=float(data["utilization_ratio"]),
        status=data["status"],
        message=data.get("message", ""),
        reference_ids=list(data.get("reference_ids", [])),
        id=data["id"],
    )


def reference_to_dict(ref: Reference) -> dict[str, Any]:
    return canonicalize_json(asdict(ref))


def reference_from_dict(data: dict[str, Any]) -> Reference:
    return Reference(
        project_id=data["project_id"],
        document_id=data["document_id"],
        fragment_id=data["fragment_id"],
        usage_type=data["usage_type"],
        citation_short=data["citation_short"],
        citation_long=data.get("citation_long", ""),
        quoted_context=data.get("quoted_context", ""),
        id=data["id"],
    )


__all__ = [
    "alternative_from_dict",
    "alternative_to_dict",
    "branch_from_dict",
    "branch_to_dict",
    "calculation_from_dict",
    "calculation_to_dict",
    "canonicalize_json",
    "check_from_dict",
    "check_to_dict",
    "decision_from_dict",
    "decision_to_dict",
    "node_from_dict",
    "node_to_dict",
    "reference_from_dict",
    "reference_to_dict",
]
