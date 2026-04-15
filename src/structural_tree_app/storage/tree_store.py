from __future__ import annotations

import shutil
from pathlib import Path

from structural_tree_app.domain.models import Alternative, Branch, Calculation, Check, Decision, Node, Reference
from structural_tree_app.domain.tree_codec import (
    alternative_from_dict,
    alternative_to_dict,
    branch_from_dict,
    branch_to_dict,
    calculation_from_dict,
    calculation_to_dict,
    check_from_dict,
    check_to_dict,
    decision_from_dict,
    decision_to_dict,
    node_from_dict,
    node_to_dict,
    reference_from_dict,
    reference_to_dict,
)
from structural_tree_app.storage.json_repository import JsonRepository
from structural_tree_app.validation.json_schema import (
    validate_alternative_payload,
    validate_branch_payload,
    validate_calculation_payload,
    validate_check_payload,
    validate_decision_payload,
    validate_node_payload,
    validate_reference_payload,
)


class TreeStore:
    """Persist tree domain JSON: branches, nodes, decisions, alternatives, calculations, checks, references."""

    def __init__(self, repository: JsonRepository, relative_root: str) -> None:
        """
        :param relative_root: Path under workspace root, e.g. ``{project_id}/tree`` or
            ``{project_id}/revisions/{revision_id}/tree`` (revision isolation).
        """
        self.repo = repository
        self.rel_root = relative_root.replace("\\", "/").strip("/")

    @classmethod
    def for_live_project(cls, repository: JsonRepository, project_id: str) -> TreeStore:
        return cls(repository, f"{project_id}/tree")

    @classmethod
    def for_revision_snapshot(cls, repository: JsonRepository, project_id: str, revision_id: str) -> TreeStore:
        return cls(repository, f"{project_id}/revisions/{revision_id}/tree")

    def _rel(self, *parts: str) -> str:
        return str(Path(self.rel_root, *parts))

    def tree_root(self) -> Path:
        return self.repo.base_path / Path(self.rel_root)

    def ensure_layout(self) -> None:
        for sub in ("branches", "nodes", "decisions", "alternatives", "calculations", "checks", "references"):
            (self.tree_root() / sub).mkdir(parents=True, exist_ok=True)

    def list_branch_ids(self) -> list[str]:
        d = self.tree_root() / "branches"
        if not d.is_dir():
            return []
        return sorted(p.stem for p in d.glob("*.json"))

    def list_node_ids(self) -> list[str]:
        d = self.tree_root() / "nodes"
        if not d.is_dir():
            return []
        return sorted(p.stem for p in d.glob("*.json"))

    def save_branch(self, branch: Branch) -> None:
        payload = branch_to_dict(branch)
        validate_branch_payload(payload)
        self.repo.write(self._rel("branches", f"{branch.id}.json"), payload)

    def load_branch(self, branch_id: str) -> Branch:
        rel = self._rel("branches", f"{branch_id}.json")
        raw = self.repo.read(rel)
        validate_branch_payload(raw)
        return branch_from_dict(raw)

    def save_node(self, node: Node) -> None:
        payload = node_to_dict(node)
        validate_node_payload(payload)
        self.repo.write(self._rel("nodes", f"{node.id}.json"), payload)

    def load_node(self, node_id: str) -> Node:
        rel = self._rel("nodes", f"{node_id}.json")
        raw = self.repo.read(rel)
        validate_node_payload(raw)
        return node_from_dict(raw)

    def save_decision(self, decision: Decision) -> None:
        payload = decision_to_dict(decision)
        validate_decision_payload(payload)
        self.repo.write(self._rel("decisions", f"{decision.id}.json"), payload)

    def load_decision(self, decision_id: str) -> Decision:
        rel = self._rel("decisions", f"{decision_id}.json")
        raw = self.repo.read(rel)
        validate_decision_payload(raw)
        return decision_from_dict(raw)

    def save_alternative(self, alt: Alternative) -> None:
        payload = alternative_to_dict(alt)
        validate_alternative_payload(payload)
        self.repo.write(self._rel("alternatives", f"{alt.id}.json"), payload)

    def load_alternative(self, alt_id: str) -> Alternative:
        rel = self._rel("alternatives", f"{alt_id}.json")
        raw = self.repo.read(rel)
        validate_alternative_payload(raw)
        return alternative_from_dict(raw)

    def list_decision_ids(self) -> list[str]:
        d = self.tree_root() / "decisions"
        if not d.is_dir():
            return []
        return sorted(p.stem for p in d.glob("*.json"))

    def list_alternative_ids(self) -> list[str]:
        d = self.tree_root() / "alternatives"
        if not d.is_dir():
            return []
        return sorted(p.stem for p in d.glob("*.json"))

    def load_all_branches(self) -> list[Branch]:
        return [self.load_branch(bid) for bid in self.list_branch_ids()]

    def load_all_nodes(self) -> list[Node]:
        return [self.load_node(nid) for nid in self.list_node_ids()]

    def list_calculation_ids(self) -> list[str]:
        d = self.tree_root() / "calculations"
        if not d.is_dir():
            return []
        return sorted(p.stem for p in d.glob("*.json"))

    def save_calculation(self, calc: Calculation) -> None:
        payload = calculation_to_dict(calc)
        validate_calculation_payload(payload)
        self.repo.write(self._rel("calculations", f"{calc.id}.json"), payload)

    def load_calculation(self, calculation_id: str) -> Calculation:
        rel = self._rel("calculations", f"{calculation_id}.json")
        raw = self.repo.read(rel)
        validate_calculation_payload(raw)
        return calculation_from_dict(raw)

    def list_check_ids(self) -> list[str]:
        d = self.tree_root() / "checks"
        if not d.is_dir():
            return []
        return sorted(p.stem for p in d.glob("*.json"))

    def save_check(self, check: Check) -> None:
        payload = check_to_dict(check)
        validate_check_payload(payload)
        self.repo.write(self._rel("checks", f"{check.id}.json"), payload)

    def load_check(self, check_id: str) -> Check:
        rel = self._rel("checks", f"{check_id}.json")
        raw = self.repo.read(rel)
        validate_check_payload(raw)
        return check_from_dict(raw)

    def list_reference_ids(self) -> list[str]:
        d = self.tree_root() / "references"
        if not d.is_dir():
            return []
        return sorted(p.stem for p in d.glob("*.json"))

    def save_reference(self, ref: Reference) -> None:
        payload = reference_to_dict(ref)
        validate_reference_payload(payload)
        self.repo.write(self._rel("references", f"{ref.id}.json"), payload)

    def load_reference(self, reference_id: str) -> Reference:
        rel = self._rel("references", f"{reference_id}.json")
        raw = self.repo.read(rel)
        validate_reference_payload(raw)
        return reference_from_dict(raw)


def copy_tree_directory(src: Path, dst: Path) -> None:
    """Replace dst with a full copy of src (revision snapshot)."""
    if dst.exists():
        shutil.rmtree(dst)
    if src.exists():
        shutil.copytree(src, dst)


__all__ = ["TreeStore", "copy_tree_directory"]
