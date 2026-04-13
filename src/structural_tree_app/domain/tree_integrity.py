from __future__ import annotations

from dataclasses import dataclass

from structural_tree_app.domain.models import Project
from structural_tree_app.storage.tree_store import TreeStore


@dataclass
class TreeIntegrityReport:
    errors: list[str]
    warnings: list[str]

    @property
    def ok(self) -> bool:
        return len(self.errors) == 0


def validate_tree_integrity(store: TreeStore, project: Project) -> TreeIntegrityReport:
    """
    Validate cross-references for the tree under ``store`` against ``project`` summaries.
    Intended for load/save boundaries and tests — does not mutate disk.
    """
    errors: list[str] = []
    warnings: list[str] = []

    branches = {b.id: b for b in store.load_all_branches()}
    nodes = {n.id: n for n in store.load_all_nodes()}
    decisions = {d.id: store.load_decision(did) for did in store.list_decision_ids()}
    alts = {a.id: store.load_alternative(aid) for aid in store.list_alternative_ids()}

    for bid in project.branch_ids:
        if bid not in branches:
            errors.append(f"project.branch_ids references missing branch file: {bid}")

    for bid, br in branches.items():
        if br.project_id != project.id:
            errors.append(f"branch {bid} project_id mismatch")
        if br.root_node_id and br.root_node_id not in nodes:
            errors.append(f"branch {bid} root_node_id {br.root_node_id} has no node file")
        if br.origin_decision_node_id and br.origin_decision_node_id not in nodes:
            warnings.append(f"branch {bid} origin_decision_node_id not found in nodes")

    if project.root_node_id and project.root_node_id not in nodes:
        errors.append(f"project.root_node_id {project.root_node_id} has no node file")

    for nid, node in nodes.items():
        if node.project_id != project.id:
            errors.append(f"node {nid} project_id mismatch")
        if node.branch_id not in branches:
            errors.append(f"node {nid} branch_id {node.branch_id} has no branch file")
        if node.parent_node_id and node.parent_node_id not in nodes:
            errors.append(f"node {nid} parent_node_id {node.parent_node_id} missing")
        for cid in node.child_node_ids:
            if cid not in nodes:
                errors.append(f"node {nid} child_node_ids references missing node {cid}")
        if node.parent_node_id:
            parent = nodes.get(node.parent_node_id)
            if parent and node.id not in parent.child_node_ids:
                warnings.append(f"node {nid} not listed in parent.child_node_ids (reverse link)")

    for did, dec in decisions.items():
        if dec.project_id != project.id:
            errors.append(f"decision {did} project_id mismatch")
        if dec.decision_node_id not in nodes:
            errors.append(f"decision {did} decision_node_id {dec.decision_node_id} missing")
        for aid in dec.alternative_ids:
            if aid not in alts:
                errors.append(f"decision {did} alternative_ids references missing {aid}")
        if dec.selected_alternative_id and dec.selected_alternative_id not in alts:
            errors.append(f"decision {did} selected_alternative_id invalid")

    for aid, alt in alts.items():
        if alt.decision_id not in decisions:
            errors.append(f"alternative {aid} decision_id {alt.decision_id} missing")

    # Orphan files (present on disk but not referenced by traversal from branch roots)
    referenced_nodes: set[str] = set()
    for br in branches.values():
        if not br.root_node_id or br.root_node_id not in nodes:
            continue
        stack = [br.root_node_id]
        while stack:
            cur = stack.pop()
            if cur in referenced_nodes:
                continue
            referenced_nodes.add(cur)
            n = nodes.get(cur)
            if not n:
                continue
            for c in n.child_node_ids:
                if c in nodes:
                    stack.append(c)

    orphan_nodes = set(nodes.keys()) - referenced_nodes
    for oid in sorted(orphan_nodes):
        warnings.append(f"orphan node file (not reachable from any branch root): {oid}")

    return TreeIntegrityReport(errors=errors, warnings=warnings)


__all__ = ["TreeIntegrityReport", "validate_tree_integrity"]
