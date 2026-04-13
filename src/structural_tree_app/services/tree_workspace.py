from __future__ import annotations

from dataclasses import replace

from structural_tree_app.domain.branch_transitions import BranchTransitionError, assert_branch_transition
from structural_tree_app.domain.enums import BranchState, NodeType
from structural_tree_app.domain.models import Alternative, Branch, Decision, Node, Project, new_id, utc_now
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.services.tree_service import TreeService
from structural_tree_app.storage.tree_store import TreeStore


class TreeWorkspaceError(RuntimeError):
    """Domain or persistence error for tree operations."""


class TreeWorkspace:
    """Persisted tree: branches/nodes/decisions/alternatives under tree/ with lifecycle rules."""

    def __init__(self, project_service: ProjectService, project: Project) -> None:
        self.ps = project_service
        self.project = project
        self.store = TreeStore.for_live_project(project_service.repository, project.id)
        self.store.ensure_layout()
        self._logic = TreeService()

    def _touch_branch(self, branch: Branch) -> Branch:
        return replace(branch, updated_at=utc_now())

    def _touch_node(self, node: Node) -> Node:
        return replace(node, updated_at=utc_now())

    def sync_project_branch_index(self) -> None:
        self.project.branch_ids = sorted(self.store.list_branch_ids())

    def create_root_problem(self, title: str, description: str) -> tuple[Branch, Node]:
        branch, node = self._logic.create_root_problem(self.project, title, description)
        branch = self._touch_branch(branch)
        node = self._touch_node(node)
        self.store.save_branch(branch)
        self.store.save_node(node)
        self.sync_project_branch_index()
        self.ps.save_project(self.project)
        return branch, node

    def load_branch(self, branch_id: str) -> Branch:
        return self.store.load_branch(branch_id)

    def load_node(self, node_id: str) -> Node:
        return self.store.load_node(node_id)

    def add_child_node(
        self,
        branch_id: str,
        parent_node_id: str,
        node_type: NodeType,
        title: str,
        description: str,
    ) -> Node:
        parent = self.store.load_node(parent_node_id)
        if parent.branch_id != branch_id:
            raise TreeWorkspaceError("Parent node is not on the requested branch")
        child = Node(
            project_id=self.project.id,
            branch_id=branch_id,
            node_type=node_type,
            title=title,
            description=description,
            parent_node_id=parent_node_id,
            depth=parent.depth + 1,
        )
        child = self._touch_node(child)
        parent = self._touch_node(parent)
        parent.child_node_ids = [*parent.child_node_ids, child.id]
        self.store.save_node(parent)
        self.store.save_node(child)
        self.ps.save_project(self.project)
        return child

    def add_decision_with_options(
        self,
        branch_id: str,
        parent_node_id: str,
        prompt: str,
        option_defs: list[tuple[str, str, list[str], list[str]]],
    ) -> tuple[Node, Decision, list[Alternative]]:
        """Create a decision node, Decision record, and alternatives (title, desc, pros, cons)."""
        parent = self.store.load_node(parent_node_id)
        node, decision = self._logic.create_decision(self.project.id, branch_id, parent_node_id, prompt)
        node = replace(node, depth=parent.depth + 1)
        node = self._touch_node(node)
        decision = replace(decision, updated_at=utc_now())
        parent = self._touch_node(parent)
        parent.child_node_ids = [*parent.child_node_ids, node.id]
        alts: list[Alternative] = []
        alt_ids: list[str] = []
        for title, desc, pros, cons in option_defs:
            alt = self._logic.create_alternative(decision.id, title, desc, pros, cons)
            alt_ids.append(alt.id)
            alts.append(alt)
        decision = replace(decision, alternative_ids=alt_ids)
        self.store.save_node(parent)
        self.store.save_node(node)
        self.store.save_decision(decision)
        for alt in alts:
            self.store.save_alternative(alt)
        self.ps.save_project(self.project)
        return node, decision, alts

    def _demote_other_active(self, except_branch_id: str) -> None:
        for bid in self.store.list_branch_ids():
            if bid == except_branch_id:
                continue
            b = self.store.load_branch(bid)
            if b.state != BranchState.ACTIVE:
                continue
            try:
                assert_branch_transition(b.state, BranchState.EXPLORED)
            except BranchTransitionError:
                continue
            b = self._touch_branch(replace(b, state=BranchState.EXPLORED))
            self.store.save_branch(b)

    def activate_branch(self, branch_id: str) -> Branch:
        b = self.store.load_branch(branch_id)
        if b.state == BranchState.DISCARDED:
            raise TreeWorkspaceError("Use reopen_branch() to restore a discarded branch")
        try:
            assert_branch_transition(b.state, BranchState.ACTIVE)
        except BranchTransitionError as e:
            raise TreeWorkspaceError(str(e)) from e
        self._demote_other_active(branch_id)
        b = self._touch_branch(replace(b, state=BranchState.ACTIVE))
        self.store.save_branch(b)
        self.ps.save_project(self.project)
        return b

    def discard_branch(self, branch_id: str) -> Branch:
        b = self.store.load_branch(branch_id)
        try:
            assert_branch_transition(b.state, BranchState.DISCARDED)
        except BranchTransitionError as e:
            raise TreeWorkspaceError(str(e)) from e
        b = self._touch_branch(replace(b, state=BranchState.DISCARDED))
        self.store.save_branch(b)
        self.ps.save_project(self.project)
        return b

    def reopen_branch(self, branch_id: str) -> Branch:
        b = self.store.load_branch(branch_id)
        if b.state != BranchState.DISCARDED:
            raise TreeWorkspaceError("reopen_branch requires state discarded")
        self._demote_other_active(branch_id)
        b = self._touch_branch(replace(b, state=BranchState.ACTIVE, reactivated_from_branch_id=None))
        self.store.save_branch(b)
        self.ps.save_project(self.project)
        return b

    def clone_branch(self, source_branch_id: str, title: str | None = None) -> Branch:
        src = self.store.load_branch(source_branch_id)
        nodes = [n for n in self.store.load_all_nodes() if n.branch_id == source_branch_id]
        if not nodes:
            raise TreeWorkspaceError("Source branch has no persisted nodes")
        by_id = {n.id: n for n in nodes}
        if src.root_node_id not in by_id:
            raise TreeWorkspaceError("Missing root node for source branch")
        old_to_new: dict[str, str] = {}
        for n in nodes:
            old_to_new[n.id] = new_id("node")
        new_branch_id = new_id("branch")
        new_root_old = src.root_node_id
        new_root_new = old_to_new[new_root_old]

        def map_node_id(oid: str | None) -> str | None:
            if oid is None:
                return None
            return old_to_new.get(oid)

        new_branch = Branch(
            project_id=self.project.id,
            title=title or f"{src.title} (copy)",
            description=src.description,
            origin_decision_node_id=map_node_id(src.origin_decision_node_id),
            root_node_id=new_root_new,
            state=BranchState.PENDING,
            parent_branch_id=src.parent_branch_id,
            cloned_from_branch_id=source_branch_id,
            reactivated_from_branch_id=None,
            comparison_tags=list(src.comparison_tags),
            id=new_branch_id,
        )
        new_branch = self._touch_branch(new_branch)

        old_decision_nodes = {d.decision_node_id: d for d in self._load_decisions_for_nodes(set(by_id))}
        old_to_new_dec: dict[str, str] = {}
        for dec in old_decision_nodes.values():
            old_to_new_dec[dec.id] = new_id("dec")

        old_to_new_alt: dict[str, str] = {}
        for dec in old_decision_nodes.values():
            for aid in dec.alternative_ids:
                old_to_new_alt[aid] = new_id("alt")

        for n in sorted(nodes, key=lambda x: x.depth):
            oid = n.id
            nid = old_to_new[oid]
            mapped_parent = map_node_id(n.parent_node_id)
            mapped_children = [old_to_new[c] for c in n.child_node_ids if c in old_to_new]
            nn = Node(
                project_id=self.project.id,
                branch_id=new_branch_id,
                node_type=n.node_type,
                title=n.title,
                description=n.description,
                parent_node_id=mapped_parent,
                state=n.state,
                order_index=n.order_index,
                depth=n.depth,
                id=nid,
                child_node_ids=mapped_children,
                linked_reference_ids=list(n.linked_reference_ids),
                linked_calculation_ids=list(n.linked_calculation_ids),
                linked_assumption_ids=list(n.linked_assumption_ids),
                created_at=n.created_at,
                updated_at=utc_now(),
            )
            self.store.save_node(nn)

        for old_dec in old_decision_nodes.values():
            new_dec_id = old_to_new_dec[old_dec.id]
            new_node_id = old_to_new[old_dec.decision_node_id]
            new_alts = [old_to_new_alt[a] for a in old_dec.alternative_ids if a in old_to_new_alt]
            sel = old_dec.selected_alternative_id
            new_sel = old_to_new_alt.get(sel) if sel else None
            dec = Decision(
                project_id=self.project.id,
                decision_node_id=new_node_id,
                prompt=old_dec.prompt,
                criterion_ids=list(old_dec.criterion_ids),
                alternative_ids=new_alts,
                selected_alternative_id=new_sel,
                status=old_dec.status,
                rationale=old_dec.rationale,
                id=new_dec_id,
                created_at=old_dec.created_at,
                updated_at=utc_now(),
            )
            self.store.save_decision(dec)

        for old_dec in old_decision_nodes.values():
            for aid in old_dec.alternative_ids:
                alt = self.store.load_alternative(aid)
                new_alt_id = old_to_new_alt[aid]
                new_dec_id = old_to_new_dec[old_dec.id]
                na = Alternative(
                    decision_id=new_dec_id,
                    title=alt.title,
                    description=alt.description,
                    pros=list(alt.pros),
                    cons=list(alt.cons),
                    constraints=list(alt.constraints),
                    next_expected_decisions=list(alt.next_expected_decisions),
                    status=alt.status,
                    reactivatable=alt.reactivatable,
                    id=new_alt_id,
                )
                self.store.save_alternative(na)

        self.store.save_branch(new_branch)
        self.project.branch_ids = sorted({*self.project.branch_ids, new_branch_id})
        self.ps.save_project(self.project)
        return new_branch

    def _load_decisions_for_nodes(self, node_ids: set[str]) -> list[Decision]:
        out: list[Decision] = []
        for did in self.store.list_decision_ids():
            d = self.store.load_decision(did)
            if d.decision_node_id in node_ids:
                out.append(d)
        return out

    def get_subtree(self, branch_id: str, root_node_id: str) -> list[Node]:
        by_id = {n.id: n for n in self.store.load_all_nodes() if n.branch_id == branch_id}
        if root_node_id not in by_id:
            raise TreeWorkspaceError("Unknown root for subtree")
        out: list[Node] = []
        stack = [root_node_id]
        seen: set[str] = set()
        while stack:
            nid = stack.pop()
            if nid in seen:
                continue
            seen.add(nid)
            n = by_id[nid]
            out.append(n)
            for c in n.child_node_ids:
                if c in by_id:
                    stack.append(c)
        return out

    def list_branch_paths(self, branch_id: str) -> list[list[str]]:
        nodes = [n for n in self.store.load_all_nodes() if n.branch_id == branch_id]
        by_id = {n.id: n for n in nodes}
        branch_obj = self.store.load_branch(branch_id)
        root = branch_obj.root_node_id
        if not root or root not in by_id:
            return []
        paths: list[list[str]] = []

        def walk(nid: str, acc: list[str]) -> None:
            n = by_id[nid]
            here = [*acc, nid]
            if not n.child_node_ids:
                paths.append(here)
                return
            for c in n.child_node_ids:
                if c in by_id:
                    walk(c, here)

        walk(root, [])
        return paths


__all__ = ["TreeWorkspace", "TreeWorkspaceError"]
