"""U5 — case-scoped visual board: thin view-model helpers over ``ReasoningBridgeResult`` (no logic duplication)."""

from __future__ import annotations

from structural_tree_app.domain.reasoning_bridge_contract import (
    CandidateFormulaOrCheck,
    CandidateProcessStep,
    EvidenceAnchor,
    FormulaExecutionStatus,
    ProblemInterpretation,
    ProcessStepScope,
    ReasoningBridgeResult,
    SupportedExecutionStep,
    UnsupportedReasoningGap,
)


def evidence_fragment_href(anchor: EvidenceAnchor) -> str:
    return f"/workbench/project/evidence/fragment/{anchor.document_id}/{anchor.fragment_id}"


def _interpretation_view(interp: ProblemInterpretation | None) -> dict[str, object] | None:
    if interp is None:
        return None
    conf = interp.confidence
    conf_class = "u5-conf-deterministic" if conf == "deterministic_keyword_map" else "u5-conf-low"
    return {
        "problem_family_label": interp.problem_family_label,
        "problem_family_id": interp.problem_family_id,
        "confidence": conf,
        "confidence_class": conf_class,
        "tokens": interp.query_tokens_matched,
    }


def _scope_class(scope: ProcessStepScope) -> str:
    return {
        "evidence_led": "u5-scope-evidence",
        "derived_navigation": "u5-scope-derived",
        "heuristic_vertical_slice": "u5-scope-heuristic",
    }[scope]


def _process_step_view(step: CandidateProcessStep) -> dict[str, object]:
    return {
        "step_id": step.step_id,
        "label": step.label,
        "process_scope": step.process_scope,
        "scope_class": _scope_class(step.process_scope),
        "notes": step.notes,
        "anchors": [_anchor_view(a) for a in step.supported_by_anchors],
    }


def _formula_execution_tier(status: FormulaExecutionStatus) -> tuple[str, str]:
    """Returns (tier_key, human label) for visual distinction."""
    if status == "deterministic_m5_available":
        return ("supported", "Supported execution today (deterministic hook)")
    if status == "recognition_only":
        return ("recognized", "Recognized — not executable as coded check here")
    return ("gap", "Insufficient evidence link / not supported")


def _formula_execution_class(tier: str) -> str:
    return {
        "supported": "u5-formula-supported",
        "recognized": "u5-formula-recognized",
        "gap": "u5-formula-gap",
    }[tier]


def _anchor_view(a: EvidenceAnchor) -> dict[str, object]:
    return {
        "anchor_id": a.anchor_id,
        "anchor_kind": a.anchor_kind,
        "provenance_label": a.provenance_label,
        "authority_note": a.authority_note,
        "href": evidence_fragment_href(a),
        "is_derived_kind": a.anchor_kind != "retrieval_hit",
    }


def _formula_view(f: CandidateFormulaOrCheck) -> dict[str, object]:
    tier_key, tier_label = _formula_execution_tier(f.execution_status)
    return {
        "formula_id": f.formula_id,
        "label": f.label,
        "source": f.source,
        "execution_status": f.execution_status,
        "tier_key": tier_key,
        "tier_label": tier_label,
        "tier_class": _formula_execution_class(tier_key),
        "non_authoritative": f.non_authoritative,
        "anchors": [_anchor_view(a) for a in f.supported_by_anchors],
    }


def _exec_step_view(s: SupportedExecutionStep) -> dict[str, object]:
    return {
        "step_id": s.step_id,
        "kind": s.kind,
        "calculation_id": s.calculation_id,
        "node_id": s.node_id,
        "method_label": s.method_label,
        "authority_boundary": s.authority_boundary,
        "notes": s.notes,
    }


def _gap_view(g: UnsupportedReasoningGap) -> dict[str, object]:
    return {"gap_id": g.gap_id, "category": g.category, "message": g.message}


def u5_canvas_board_from_result(result: ReasoningBridgeResult) -> dict[str, object]:
    """Serialize bridge result for Jinja (lists of plain dicts; stable keys)."""
    return {
        "analysis_status": result.analysis_status,
        "analysis_error_message": result.analysis_error_message,
        "bridge_disclaimer": result.bridge_disclaimer,
        "retrieval_status": result.retrieval_status,
        "retrieval_normative_source": result.retrieval_normative_source,
        "governance_normative_block": result.governance_normative_block,
        "retrieval_message": result.retrieval_message,
        "interpretation": _interpretation_view(result.interpretation),
        "process_steps": [_process_step_view(s) for s in result.candidate_process_steps],
        "formulas": [_formula_view(f) for f in result.candidate_formulas],
        "execution_steps": [_exec_step_view(s) for s in result.supported_execution_steps],
        "gaps": [_gap_view(g) for g in result.unsupported_gaps],
        "evidence_anchors_flat": [_anchor_view(a) for a in result.evidence_anchors],
        "warnings": list(result.warnings),
    }


__all__ = [
    "evidence_fragment_href",
    "u5_canvas_board_from_result",
]
