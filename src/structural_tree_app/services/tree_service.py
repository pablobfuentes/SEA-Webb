from __future__ import annotations

from structural_tree_app.domain.enums import BranchState, NodeType
from structural_tree_app.domain.models import Alternative, Branch, Decision, Node, Project


class TreeService:
    """Servicio base para crear el árbol del problema."""

    def create_root_problem(self, project: Project, title: str, description: str) -> tuple[Branch, Node]:
        branch = Branch(
            project_id=project.id,
            title="Ruta principal",
            description="Rama inicial del proyecto",
            origin_decision_node_id=None,
            state=BranchState.ACTIVE,
        )
        node = Node(
            project_id=project.id,
            branch_id=branch.id,
            node_type=NodeType.PROBLEM,
            title=title,
            description=description,
            depth=0,
        )
        branch.root_node_id = node.id
        project.root_node_id = node.id
        project.branch_ids.append(branch.id)
        return branch, node

    def create_decision(self, project_id: str, branch_id: str, parent_node_id: str, prompt: str) -> tuple[Node, Decision]:
        node = Node(
            project_id=project_id,
            branch_id=branch_id,
            node_type=NodeType.DECISION,
            title=prompt,
            description="Nodo de bifurcación",
            parent_node_id=parent_node_id,
        )
        decision = Decision(project_id=project_id, decision_node_id=node.id, prompt=prompt)
        return node, decision

    def create_alternative(self, decision_id: str, title: str, description: str, pros: list[str], cons: list[str]) -> Alternative:
        return Alternative(
            decision_id=decision_id,
            title=title,
            description=description,
            pros=pros,
            cons=cons,
        )
