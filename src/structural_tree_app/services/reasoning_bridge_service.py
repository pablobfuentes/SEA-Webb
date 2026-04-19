"""
R2B — Thin reasoning / formula-selection bridge over governed retrieval + derived knowledge.

Does not modify ``DocumentRetrievalService`` or ``LocalAssistOrchestrator``. Call explicitly when needed.
"""

from __future__ import annotations

import hashlib
import re

from structural_tree_app.domain.derived_knowledge_models import (
    DerivedKnowledgeBundle,
    FormulaRegistryEntry,
    SourceAnchorRef,
)
from structural_tree_app.domain.reasoning_bridge_contract import (
    CandidateFormulaOrCheck,
    CandidateProcessStep,
    EvidenceAnchor,
    ProblemInterpretation,
    ReasoningBridgeRequest,
    ReasoningBridgeResult,
    SupportedExecutionStep,
    UnsupportedReasoningGap,
)
from structural_tree_app.services.derived_knowledge_service import DerivedKnowledgeService
from structural_tree_app.services.project_service import ProjectPersistenceError, ProjectService
from structural_tree_app.services.retrieval_service import CitationPayload, DocumentRetrievalService, RetrievalResponse
from structural_tree_app.services.simple_span_m5_service import METHOD_LABEL as M5_METHOD_LABEL
from structural_tree_app.storage.tree_store import TreeStore

REASONING_BRIDGE_MAX_QUERY_LEN = 8000

_SLICE_CORE = frozenset({"span", "beam", "flexure", "flexural"})
_SLICE_CTX = frozenset({"steel", "aisc", "simple", "uniform", "load"})


def _tokenize(q: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", q.lower()) if t]


def _stable_id(prefix: str, *parts: str) -> str:
    h = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{h}"


def _interpret_problem(query_text: str) -> ProblemInterpretation:
    toks = _tokenize(query_text)
    st = set(toks)
    has_core = bool(st & _SLICE_CORE)
    has_ctx = bool(st & _SLICE_CTX)
    matched = sorted(st & (_SLICE_CORE | _SLICE_CTX))
    if has_core and has_ctx:
        return ProblemInterpretation(
            problem_family_id="simple_span_steel_vertical_slice",
            problem_family_label="Simple-span / beam steel flexure (foundation vertical slice; not full catalog).",
            confidence="deterministic_keyword_map",
            query_tokens_matched=tuple(matched[:24]),
        )
    if has_core:
        return ProblemInterpretation(
            problem_family_id="beam_flexure_partial_slice",
            problem_family_label="Beam/flexure-related query; vertical slice classification incomplete without steel/span context.",
            confidence="low",
            query_tokens_matched=tuple(matched[:24]),
        )
    return ProblemInterpretation(
        problem_family_id="unknown",
        problem_family_label="No narrow vertical-slice keyword map matched (bridge does not use opaque NLP).",
        confidence="low",
        query_tokens_matched=tuple(toks[:24]),
    )


def _anchor_from_retrieval(hit: CitationPayload, idx: int) -> EvidenceAnchor:
    return EvidenceAnchor(
        anchor_id=_stable_id("ea", "retrieval", hit.document_id, hit.fragment_id, str(idx)),
        anchor_kind="retrieval_hit",
        document_id=hit.document_id,
        fragment_id=hit.fragment_id,
        document_content_hash=hit.content_hash,
        fragment_content_hash=hit.fragment_content_hash,
        provenance_label=f"Retrieval hit {idx} (lexical score={hit.score:.4f})",
        authority_note="Normative evidence only if retrieval mode is normative_active_primary and governance permits; passages are not merged conclusions.",
    )


def _anchor_from_derived_ref(
    ref: SourceAnchorRef,
    kind_str: str,
    suffix: str,
) -> EvidenceAnchor:
    return EvidenceAnchor(
        anchor_id=_stable_id("ea", "derived", kind_str, ref.document_id, ref.fragment_id, suffix),
        anchor_kind=kind_str,  # type: ignore[arg-type]
        document_id=ref.document_id,
        fragment_id=ref.fragment_id,
        document_content_hash=ref.document_content_hash,
        fragment_content_hash=ref.fragment_content_hash,
        provenance_label="Derived knowledge layer (G5)",
        authority_note="Derived artifact — not standalone evidence.",
    )


def _formula_execution_status(
    entry: FormulaRegistryEntry,
    *,
    has_m5_hooks: bool,
) -> str:
    if entry.execution_capability == "deterministic_m5_hook":
        if has_m5_hooks:
            return "deterministic_m5_available"
        return "recognition_only"
    return "recognition_only"


def _derived_formula_candidates(
    bundle: DerivedKnowledgeBundle | None,
    query_tokens: set[str],
    hit_ids: set[tuple[str, str]],
    *,
    has_m5_hooks: bool,
) -> tuple[CandidateFormulaOrCheck, ...]:
    if bundle is None:
        return ()
    out: list[CandidateFormulaOrCheck] = []
    for ent in sorted(bundle.artifacts.formula_registry_entries, key=lambda e: e.entry_id):
        label_toks = set(_tokenize(ent.label))
        overlap = bool(query_tokens & label_toks) or any(
            (a.document_id, a.fragment_id) in hit_ids for a in ent.supported_by_anchors
        )
        if not overlap:
            continue
        anchors = tuple(_anchor_from_derived_ref(a, "derived_formula_registry", ent.entry_id) for a in ent.supported_by_anchors)
        ex = _formula_execution_status(ent, has_m5_hooks=has_m5_hooks)
        out.append(
            CandidateFormulaOrCheck(
                formula_id=ent.entry_id,
                label=ent.label,
                source="derived_registry",
                execution_status=ex,  # type: ignore[arg-type]
                supported_by_anchors=anchors,
                non_authoritative=True,
            )
        )
    return tuple(sorted(out, key=lambda x: x.formula_id))


def _load_deterministic_steps(project_id: str, ps: ProjectService) -> tuple[SupportedExecutionStep, ...]:
    store = TreeStore.for_live_project(ps.repository, project_id)
    out: list[SupportedExecutionStep] = []
    for cid in sorted(store.list_calculation_ids()):
        c = store.load_calculation(cid)
        if c.method_label == M5_METHOD_LABEL:
            out.append(
                SupportedExecutionStep(
                    step_id=_stable_id("sex", "m5", c.id),
                    kind="deterministic_m5_preliminary",
                    calculation_id=c.id,
                    node_id=c.node_id,
                    method_label=c.method_label,
                    authority_boundary="preliminary_deterministic_m5",
                    notes="Preliminary M5 output is engine-only; not a substitute for governed passage review.",
                )
            )
        else:
            out.append(
                SupportedExecutionStep(
                    step_id=_stable_id("sex", "oth", c.id),
                    kind="deterministic_computation_other",
                    calculation_id=c.id,
                    node_id=c.node_id,
                    method_label=c.method_label,
                    authority_boundary="deterministic_computation_other",
                    notes="Deterministic calculation record; separate from document citations.",
                )
            )
    return tuple(sorted(out, key=lambda s: s.step_id))


def _process_steps(
    interp: ProblemInterpretation,
    retrieval_anchors: tuple[EvidenceAnchor, ...],
    rr: RetrievalResponse,
) -> tuple[CandidateProcessStep, ...]:
    steps: list[CandidateProcessStep] = []
    if retrieval_anchors:
        steps.append(
            CandidateProcessStep(
                step_id=_stable_id("cps", "evidence"),
                label="Review governed passages for limit states, resistance factors, and applicability.",
                process_scope="evidence_led",
                supported_by_anchors=retrieval_anchors,
                notes="Follow citation rows; bridge does not merge sources into one design decision.",
            )
        )
    else:
        notes = rr.message or "No lexical hits under the active authority gate."
        steps.append(
            CandidateProcessStep(
                step_id=_stable_id("cps", "no_evidence"),
                label="No governed passages matched this query under the current retrieval mode.",
                process_scope="evidence_led",
                supported_by_anchors=(),
                notes=notes,
            )
        )

    if interp.problem_family_id in ("simple_span_steel_vertical_slice", "beam_flexure_partial_slice"):
        steps.append(
            CandidateProcessStep(
                step_id=_stable_id("cps", "slice"),
                label="Foundation vertical slice: simple-span steel workflow may apply (catalog/alternatives on tree).",
                process_scope="heuristic_vertical_slice",
                supported_by_anchors=retrieval_anchors[:3],
                notes="Heuristic only — confirm against project workflow and governed references.",
            )
        )
    return tuple(sorted(steps, key=lambda s: s.step_id))


def _merge_anchors(*groups: tuple[EvidenceAnchor, ...]) -> tuple[EvidenceAnchor, ...]:
    by_id: dict[str, EvidenceAnchor] = {}
    for g in groups:
        for a in g:
            by_id[a.anchor_id] = a
    return tuple(sorted(by_id.values(), key=lambda x: x.anchor_id))


class ReasoningBridgeService:
    """Build ``ReasoningBridgeResult`` using retrieval + optional derived bundle + deterministic scan."""

    def __init__(self, project_service: ProjectService) -> None:
        self._ps = project_service

    def analyze(self, req: ReasoningBridgeRequest) -> ReasoningBridgeResult:
        text = req.query_text.strip()
        if not text:
            return ReasoningBridgeResult(
                project_id=req.project_id,
                query_text=req.query_text,
                analysis_status="unsupported_query",
                analysis_error_message="Query text is empty after strip.",
                retrieval_status="insufficient_evidence",
                retrieval_normative_source="n_a",
                retrieval_message="",
                unsupported_gaps=(
                    UnsupportedReasoningGap(
                        gap_id=_stable_id("gap", "empty"),
                        category="empty_query",
                        message="Nothing to analyze.",
                    ),
                ),
                warnings=("reasoning_bridge_empty_query",),
            )
        if len(text) > REASONING_BRIDGE_MAX_QUERY_LEN:
            return ReasoningBridgeResult(
                project_id=req.project_id,
                query_text=req.query_text,
                analysis_status="unsupported_query",
                analysis_error_message=f"Query exceeds {REASONING_BRIDGE_MAX_QUERY_LEN} characters.",
                retrieval_status="insufficient_evidence",
                retrieval_normative_source="n_a",
                retrieval_message="",
                unsupported_gaps=(
                    UnsupportedReasoningGap(
                        gap_id=_stable_id("gap", "long"),
                        category="query_too_long",
                        message="Query too long for bridge analysis.",
                    ),
                ),
                warnings=("reasoning_bridge_query_too_long",),
            )

        try:
            self._ps.load_project(req.project_id)
        except ProjectPersistenceError as e:
            return ReasoningBridgeResult(
                project_id=req.project_id,
                query_text=text,
                analysis_status="error",
                analysis_error_message=str(e),
                retrieval_status="insufficient_evidence",
                retrieval_normative_source="n_a",
                retrieval_message="",
                unsupported_gaps=(
                    UnsupportedReasoningGap(
                        gap_id=_stable_id("gap", "proj"),
                        category="project_error",
                        message=str(e),
                    ),
                ),
                warnings=("reasoning_bridge_project_error",),
            )

        rsvc = DocumentRetrievalService(self._ps, req.project_id)
        rr = rsvc.search(
            text,
            citation_authority=req.citation_authority,
            limit=req.retrieval_limit,
            match_project_primary_standard_family=req.match_project_primary_standard_family,
            language=req.language,
            topic=req.topic,
            document_ids=set(req.document_ids) if req.document_ids is not None else None,
        )

        interp = _interpret_problem(text)
        qtok = set(_tokenize(text))

        retrieval_anchors = tuple(_anchor_from_retrieval(h, i) for i, h in enumerate(rr.hits))
        hit_ids = {(h.document_id, h.fragment_id) for h in rr.hits}

        dks = DerivedKnowledgeService(self._ps)
        bundle = dks.try_load_bundle(req.project_id)

        supported_steps: tuple[SupportedExecutionStep, ...] = ()
        if req.include_deterministic_context:
            supported_steps = _load_deterministic_steps(req.project_id, self._ps)
        has_m5 = any(s.kind == "deterministic_m5_preliminary" for s in supported_steps)

        formulas = list(
            _derived_formula_candidates(
                bundle,
                qtok,
                hit_ids,
                has_m5_hooks=has_m5,
            )
        )

        gaps: list[UnsupportedReasoningGap] = []
        warnings: list[str] = list(rr.governance_warnings)

        if bundle is None:
            gaps.append(
                UnsupportedReasoningGap(
                    gap_id=_stable_id("gap", "dk"),
                    category="no_derived_knowledge_bundle",
                    message="No derived knowledge bundle on disk; formula/topic aids unavailable (retrieval still authoritative).",
                )
            )
            warnings.append("reasoning_bridge_no_derived_knowledge_bundle")

        if rr.governance_normative_block is not None:
            gaps.append(
                UnsupportedReasoningGap(
                    gap_id=_stable_id("gap", "gov"),
                    category="governance_normative_block",
                    message=rr.message,
                )
            )

        if rr.status != "ok":
            gaps.append(
                UnsupportedReasoningGap(
                    gap_id=_stable_id("gap", "ret"),
                    category="insufficient_retrieval",
                    message=rr.message or "No passages under current retrieval settings.",
                )
            )

        if interp.problem_family_id == "unknown":
            gaps.append(
                UnsupportedReasoningGap(
                    gap_id=_stable_id("gap", "slice"),
                    category="outside_vertical_slice",
                    message="Query did not match the narrow foundation vertical-slice keyword map.",
                )
            )

        extra_formulas: list[CandidateFormulaOrCheck] = []
        sorted_hits = sorted(rr.hits, key=lambda x: (-x.score, x.document_id, x.fragment_id))
        for i, h in enumerate(sorted_hits[:3]):
            ex = _anchor_from_retrieval(h, i)
            snippet = h.snippet if len(h.snippet) <= 200 else h.snippet[:197] + "..."
            extra_formulas.append(
                CandidateFormulaOrCheck(
                    formula_id=_stable_id("cf", "rh", h.document_id, h.fragment_id),
                    label=f"Retrieval passage excerpt: {snippet}",
                    source="retrieval_passage_heuristic",
                    execution_status="insufficient_evidence_link",
                    supported_by_anchors=(ex,),
                    non_authoritative=True,
                )
            )

        all_formulas = tuple(sorted(formulas + extra_formulas, key=lambda f: f.formula_id))
        steps = _process_steps(interp, retrieval_anchors, rr)
        formula_anchors = tuple(a for f in all_formulas for a in f.supported_by_anchors)
        all_anchors = _merge_anchors(retrieval_anchors, formula_anchors)

        return ReasoningBridgeResult(
            project_id=req.project_id,
            query_text=text,
            analysis_status="ok",
            retrieval_status=rr.status,
            retrieval_normative_source=rr.normative_retrieval_source,
            governance_normative_block=rr.governance_normative_block,
            retrieval_message=rr.message,
            interpretation=interp,
            candidate_process_steps=steps,
            candidate_formulas=all_formulas,
            supported_execution_steps=supported_steps,
            unsupported_gaps=tuple(sorted(gaps, key=lambda g: g.gap_id)),
            evidence_anchors=all_anchors,
            warnings=tuple(sorted(set(warnings))),
        )


__all__ = [
    "REASONING_BRIDGE_MAX_QUERY_LEN",
    "ReasoningBridgeService",
]
