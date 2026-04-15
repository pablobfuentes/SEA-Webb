from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from structural_tree_app.domain.enums import BranchState, NodeState, NodeType
from structural_tree_app.domain.models import Project, utc_now
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.services.simple_span_m5_service import METHOD_LABEL as M5_METHOD_LABEL
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
    "deterministic_preliminary",
]

ComparisonFieldSource = Literal[
    "m5_deterministic_preliminary",
    "branch_tree_derived",
    "manual_placeholder",
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
    m5_preliminary: dict[str, Any] | None = None
    m5_checks_via_calculation_id: list[dict[str, Any]] = field(default_factory=list)
    comparison_field_sources: dict[str, ComparisonFieldSource] = field(default_factory=dict)
    """
    Explicit source classification used by M6 output:
    - m5_deterministic_preliminary
    - branch_tree_derived
    - manual_placeholder
    - document_trace_pending
    """
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
    p["m5_preliminary"] = "deterministic_preliminary"
    p["m5_checks_via_calculation_id"] = "deterministic_preliminary"
    return dict(sorted(p.items()))


def _build_comparison_field_sources(
    *,
    has_manual_placeholders: bool,
) -> dict[str, ComparisonFieldSource]:
    placeholder_source: ComparisonFieldSource = (
        "manual_placeholder" if has_manual_placeholders else "branch_tree_derived"
    )
    out: dict[str, ComparisonFieldSource] = {
        "m5_preliminary": "m5_deterministic_preliminary",
        "m5_checks_via_calculation_id": "m5_deterministic_preliminary",
        "title": "branch_tree_derived",
        "state": "branch_tree_derived",
        "unresolved_blockers": "branch_tree_derived",
        "assumptions_count": "branch_tree_derived",
        "calculations_count": "branch_tree_derived",
        "pending_checks_count": "branch_tree_derived",
        "qualitative_advantages": "branch_tree_derived",
        "qualitative_disadvantages": "branch_tree_derived",
        "max_subtree_depth": "branch_tree_derived",
        "node_count": "branch_tree_derived",
        "reference_ids": "document_trace_pending",
        "citation_traces": "document_trace_pending",
        "linked_reference_ids_count": "document_trace_pending",
        "estimated_depth_or_height": placeholder_source,
        "estimated_weight_category": placeholder_source,
        "fabrication_complexity_category": placeholder_source,
        "erection_complexity_category": placeholder_source,
    }
    return dict(sorted(out.items()))


def _compact_m5_result(result: dict[str, Any], *, method_label: str) -> dict[str, Any]:
    return {
        "classification": "preliminary_workflow_signal",
        "method_label": method_label,
        "disclaimer": result.get("disclaimer"),
        "deterministic_signals": {
            "nominal_depth_demand_m": result.get("nominal_depth_demand_m"),
            "nominal_depth_ratio_of_span": result.get("nominal_depth_ratio_of_span"),
            "fabrication_complexity_rank": result.get("fabrication_complexity_rank"),
            "fabrication_complexity_label": result.get("fabrication_complexity_label"),
            "lightweight_fit": result.get("lightweight_fit"),
            "fabrication_simplicity_alignment_score": result.get("fabrication_simplicity_alignment_score"),
            "fabrication_simplicity_alignment_reason": result.get("fabrication_simplicity_alignment_reason"),
        },
        "authority": result.get("authority", {}),
        "inputs_echo": result.get("inputs_echo", {}),
    }


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
        node_ids = {n.id for n in nodes}
        blockers = sorted(n.title for n in nodes if n.state == NodeState.BLOCKED)
        calc_ids = []
        for cid in sorted(self.store.list_calculation_ids()):
            calc = self.store.load_calculation(cid)
            if calc.node_id in node_ids:
                calc_ids.append(calc.id)
        calculations_count = len(calc_ids)

        checks_for_branch = []
        for ckid in sorted(self.store.list_check_ids()):
            chk = self.store.load_check(ckid)
            if chk.node_id in node_ids or chk.calculation_id in calc_ids:
                checks_for_branch.append(chk)
        pending_checks = sum(
            1
            for c in checks_for_branch
            if str(c.status).lower() in {"pending", "pending_inputs", "open", "todo"}
        )

        ref_ids: list[str] = []
        for n in nodes:
            ref_ids.extend(n.linked_reference_ids)
        ref_ids = sorted(_dedupe_preserve(ref_ids))
        traces = [
            DocumentCitationTrace(reference_id=rid, resolution_status="ids_only") for rid in ref_ids
        ]

        assumptions = self._load_assumptions()
        assumptions_count = sum(1 for a in assumptions if a.node_id in node_ids)

        advantages, disadvantages = self._aggregate_alternative_pros_cons(branch_id, by_id)

        depths = [n.depth for n in nodes] if nodes else [0]
        max_depth = max(depths)

        est_depth, weight, fab, erection = self._placeholders_from_tags(branch.comparison_tags)
        has_manual = any(x is not None for x in (est_depth, weight, fab, erection))
        provenance = _build_metric_provenance(has_manual_placeholders=has_manual)
        field_sources = _build_comparison_field_sources(has_manual_placeholders=has_manual)

        m5_calc_ids = []
        for cid in calc_ids:
            c = self.store.load_calculation(cid)
            if c.method_label == M5_METHOD_LABEL:
                m5_calc_ids.append(cid)
        m5_calc_ids = sorted(m5_calc_ids)

        m5_preliminary = None
        if m5_calc_ids:
            selected = self.store.load_calculation(m5_calc_ids[-1])
            m5_preliminary = _compact_m5_result(selected.result, method_label=selected.method_label)

        m5_checks: list[dict[str, Any]] = []
        for chk in sorted(checks_for_branch, key=lambda c: (c.check_type, c.id)):
            if chk.calculation_id not in m5_calc_ids:
                continue
            m5_checks.append(
                {
                    "check_id": chk.id,
                    "check_type": chk.check_type,
                    "status": chk.status,
                    "message": chk.message,
                    "utilization_ratio": chk.utilization_ratio,
                    "disclaimer": "preliminary_workflow_signal",
                }
            )

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
            m5_preliminary=m5_preliminary,
            m5_checks_via_calculation_id=m5_checks,
            comparison_field_sources=field_sources,
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
