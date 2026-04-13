from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from structural_tree_app.domain.enums import BranchState, NodeState, NodeType
from structural_tree_app.domain.models import Project, utc_now
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.services.tree_workspace import TreeWorkspace
from structural_tree_app.storage.tree_store import TreeStore


class BranchComparisonError(ValueError):
    """Invalid branch selection or project mismatch."""


ResolutionStatus = Literal["ids_only", "resolved"]

CriterionProvenance = Literal[
    "computed",
    "derived_from_tree",
    "manual_tag",
    "document_trace_pending",
]


@dataclass(frozen=True)
class DocumentCitationTrace:
    """
    Internal trace for node-linked reference IDs during branch comparison.

    **Not** a substitute for authoritative citation output. Full design authority for
    document claims remains with ``DocumentRetrievalService`` / ``CitationPayload``
    (``normative_active_primary`` by default). ``resolution_status == "ids_only"``
    means document/fragment identity is not resolved from persisted Reference rows yet.
    """

    reference_id: str
    document_id: str | None = None
    fragment_id: str | None = None
    resolution_status: ResolutionStatus = "ids_only"


@dataclass
class BranchComparisonRow:
    """One branch column in a comparison matrix (read-only snapshot)."""

    branch_id: str
    title: str
    state: str
    unresolved_blockers: list[str]
    assumptions_count: int
    calculations_count: int
    pending_checks_count: int
    linked_reference_ids_count: int
    reference_ids: list[str]
    citation_traces: list[DocumentCitationTrace]
    qualitative_advantages: list[str]
    qualitative_disadvantages: list[str]
    max_subtree_depth: int
    node_count: int
    estimated_depth_or_height: str | None = None
    estimated_weight_category: str | None = None
    fabrication_complexity_category: str | None = None
    erection_complexity_category: str | None = None
    metric_provenance: dict[str, CriterionProvenance] = field(default_factory=dict)
    """
    Origin of each metric for this row (deterministic keys, sorted in ``to_dict`` output).
    ``document_trace_pending`` marks citation-adjacent fields that are not authoritative
    until Reference resolution; use retrieval citations for user-facing authority.
    """


@dataclass
class BranchComparisonResult:
    """Structured, serializable comparison; does not mutate branches."""

    project_id: str
    compared_branch_ids: list[str]
    rows: list[BranchComparisonRow]
    generated_at: str
    notes: list[str] = field(default_factory=list)
    citation_trace_authority: Literal["internal_trace_only", "full_citation_ready"] = (
        "internal_trace_only"
    )
    """
    ``internal_trace_only``: ``citation_traces`` are identifiers for engineering comparison,
    not full citations. Authoritative excerpts require ``DocumentRetrievalService`` results.
    """

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        for row in d.get("rows", []):
            mp = row.get("metric_provenance") or {}
            row["metric_provenance"] = dict(sorted(mp.items()))
        return d


def _dedupe_preserve(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in seq:
        if x in seen:
            continue
        seen.add(x)
        out.append(x)
    return out


def _build_metric_provenance(
    *,
    has_manual_placeholders: bool,
) -> dict[str, CriterionProvenance]:
    """Deterministic provenance map (same keys for every row; placeholder fields vary)."""
    p: dict[str, CriterionProvenance] = {
        "title": "derived_from_tree",
        "state": "derived_from_tree",
        "unresolved_blockers": "derived_from_tree",
        "assumptions_count": "computed",
        "calculations_count": "derived_from_tree",
        "pending_checks_count": "derived_from_tree",
        "linked_reference_ids_count": "document_trace_pending",
        "reference_ids": "document_trace_pending",
        "citation_traces": "document_trace_pending",
        "qualitative_advantages": "derived_from_tree",
        "qualitative_disadvantages": "derived_from_tree",
        "max_subtree_depth": "computed",
        "node_count": "computed",
    }
    tag_prov: CriterionProvenance = "manual_tag" if has_manual_placeholders else "derived_from_tree"
    p["estimated_depth_or_height"] = tag_prov
    p["estimated_weight_category"] = tag_prov
    p["fabrication_complexity_category"] = tag_prov
    p["erection_complexity_category"] = tag_prov
    return dict(sorted(p.items()))


class BranchComparisonService:
    """
    Domain service: compare branches as decision alternatives without mutating tree state.
    Discarded branches remain readable and comparable; comparison does not activate them.

    For reproducibility against a frozen workspace state, use
    ``for_revision_snapshot`` so tree + assumptions come from a revision snapshot.
    """

    def __init__(
        self,
        project_service: ProjectService,
        project: Project,
        *,
        tree_store: TreeStore | None = None,
        assumptions: list | None = None,
    ) -> None:
        self._ps = project_service
        self._project = project
        self._project_id = project.id
        if tree_store is None:
            self._tw = TreeWorkspace(project_service, project)
            self._store = self._tw.store
            self._assumptions_override: list | None = None
        else:
            self._tw = None
            self._store = tree_store
            self._assumptions_override = assumptions

    @classmethod
    def for_live(cls, project_service: ProjectService, project_id: str) -> BranchComparisonService:
        return cls(project_service, project_service.load_project(project_id))

    @classmethod
    def for_revision_snapshot(
        cls, project_service: ProjectService, project_id: str, revision_id: str
    ) -> BranchComparisonService:
        proj = project_service.load_revision_snapshot_project(project_id, revision_id)
        asm = project_service.load_revision_snapshot_assumptions(project_id, revision_id)
        store = TreeStore.for_revision_snapshot(project_service.repository, project_id, revision_id)
        return cls(project_service, proj, tree_store=store, assumptions=asm)

    @property
    def store(self) -> TreeStore:
        return self._store

    def _load_assumptions(self) -> list:
        if self._assumptions_override is not None:
            return self._assumptions_override
        return self._ps.load_assumptions(self._project_id)

    def compare_branches(self, branch_ids: list[str]) -> BranchComparisonResult:
        unique = sorted(set(branch_ids))
        if len(unique) < 2:
            raise BranchComparisonError("Select at least two distinct branches for comparison.")
        on_disk = set(self.store.list_branch_ids())
        for bid in unique:
            if bid not in on_disk:
                raise BranchComparisonError(f"Branch not found in tree store: {bid}")
        ordered = unique
        rows: list[BranchComparisonRow] = []
        for bid in ordered:
            rows.append(self._row_for_branch(self._project, bid))
        notes = [
            "Branch comparison v1: metrics are for engineering trade-off review, not "
            "user-facing normative citations.",
            "citation_traces with resolution_status='ids_only' are internal trace hooks only; "
            "they MUST NOT be treated as authoritative citation output. Use "
            "DocumentRetrievalService + CitationPayload (default normative_active_primary) "
            "for authoritative document excerpts.",
            "Reproducibility: use BranchComparisonService.for_revision_snapshot(project_id, "
            "revision_id) to compare branches against an immutable revision tree + assumptions.",
        ]
        return BranchComparisonResult(
            project_id=self._project_id,
            compared_branch_ids=ordered,
            rows=rows,
            generated_at=utc_now(),
            notes=notes,
            citation_trace_authority="internal_trace_only",
        )

    def _row_for_branch(self, project: Project, branch_id: str) -> BranchComparisonRow:
        branch = self.store.load_branch(branch_id)
        nodes = [n for n in self.store.load_all_nodes() if n.branch_id == branch_id]
        nodes.sort(key=lambda n: n.id)
        by_id = {n.id: n for n in nodes}
        blockers = sorted(n.title for n in nodes if n.state == NodeState.BLOCKED)
        pending_checks = sum(
            1 for n in nodes if n.node_type == NodeType.CHECK and n.state != NodeState.COMPLETE
        )
        calc_nodes = sum(1 for n in nodes if n.node_type == NodeType.CALCULATION)
        linked_calcs = sum(len(n.linked_calculation_ids) for n in nodes)
        calculations_count = calc_nodes + linked_calcs

        ref_ids: list[str] = []
        for n in nodes:
            ref_ids.extend(n.linked_reference_ids)
        ref_ids = sorted(_dedupe_preserve(ref_ids))
        traces = [
            DocumentCitationTrace(reference_id=rid, resolution_status="ids_only") for rid in ref_ids
        ]

        assumptions = self._load_assumptions()
        node_ids = {n.id for n in nodes}
        assumptions_count = sum(1 for a in assumptions if a.node_id in node_ids)

        advantages, disadvantages = self._aggregate_alternative_pros_cons(branch_id, by_id)

        depths = [n.depth for n in nodes] if nodes else [0]
        max_depth = max(depths)

        est_depth, weight, fab, erection = self._placeholders_from_tags(branch.comparison_tags)
        has_manual = any(x is not None for x in (est_depth, weight, fab, erection))
        provenance = _build_metric_provenance(has_manual_placeholders=has_manual)

        return BranchComparisonRow(
            branch_id=branch.id,
            title=branch.title,
            state=branch.state.value if isinstance(branch.state, BranchState) else str(branch.state),
            unresolved_blockers=blockers,
            assumptions_count=assumptions_count,
            calculations_count=calculations_count,
            pending_checks_count=pending_checks,
            linked_reference_ids_count=len(ref_ids),
            reference_ids=ref_ids,
            citation_traces=traces,
            qualitative_advantages=advantages,
            qualitative_disadvantages=disadvantages,
            max_subtree_depth=max_depth,
            node_count=len(nodes),
            estimated_depth_or_height=est_depth,
            estimated_weight_category=weight,
            fabrication_complexity_category=fab,
            erection_complexity_category=erection,
            metric_provenance=provenance,
        )

    def _aggregate_alternative_pros_cons(
        self, branch_id: str, by_id: dict[str, Node]
    ) -> tuple[list[str], list[str]]:
        decision_nodes = {nid for nid, n in by_id.items() if n.node_type == NodeType.DECISION}
        pros: list[str] = []
        cons: list[str] = []
        for did in sorted(self.store.list_decision_ids()):
            d = self.store.load_decision(did)
            if d.decision_node_id not in decision_nodes:
                continue
            for aid in d.alternative_ids:
                alt = self.store.load_alternative(aid)
                pros.extend(alt.pros)
                cons.extend(alt.cons)
        return sorted(_dedupe_preserve(pros)), sorted(_dedupe_preserve(cons))

    @staticmethod
    def _placeholders_from_tags(tags: list[str]) -> tuple[str | None, str | None, str | None, str | None]:
        """
        Optional convention: tags like ``depth:12m``, ``weight:heavy``, ``fab:high``, ``erect:medium``.
        Unknown tags are ignored for placeholders.
        """
        depth = weight = fab = erection = None
        for t in sorted(tags):
            if ":" not in t:
                continue
            k, v = t.split(":", 1)
            k, v = k.strip().lower(), v.strip()
            if k in ("depth", "height"):
                depth = v
            elif k in ("weight", "weight_cat"):
                weight = v
            elif k in ("fab", "fabrication"):
                fab = v
            elif k in ("erect", "erection"):
                erection = v
        return depth, weight, fab, erection


__all__ = [
    "BranchComparisonError",
    "BranchComparisonResult",
    "BranchComparisonRow",
    "BranchComparisonService",
    "CriterionProvenance",
    "DocumentCitationTrace",
]
