"""Deterministic JSON codecs for R2B reasoning bridge results."""

from __future__ import annotations

from typing import Any

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


def _anchor_to_dict(a: EvidenceAnchor) -> dict[str, Any]:
    return {
        "anchor_id": a.anchor_id,
        "anchor_kind": a.anchor_kind,
        "authority_note": a.authority_note,
        "document_content_hash": a.document_content_hash,
        "document_id": a.document_id,
        "fragment_content_hash": a.fragment_content_hash,
        "fragment_id": a.fragment_id,
        "provenance_label": a.provenance_label,
    }


def _anchor_from_dict(d: dict[str, Any]) -> EvidenceAnchor:
    return EvidenceAnchor(
        anchor_id=d["anchor_id"],
        anchor_kind=d["anchor_kind"],
        document_id=d["document_id"],
        fragment_id=d["fragment_id"],
        document_content_hash=d["document_content_hash"],
        fragment_content_hash=d["fragment_content_hash"],
        provenance_label=d.get("provenance_label", ""),
        authority_note=d.get("authority_note", ""),
    )


def reasoning_bridge_request_to_dict(r: ReasoningBridgeRequest) -> dict[str, Any]:
    return {
        "citation_authority": r.citation_authority,
        "document_ids": sorted(r.document_ids) if r.document_ids is not None else None,
        "include_deterministic_context": r.include_deterministic_context,
        "language": r.language,
        "match_project_primary_standard_family": r.match_project_primary_standard_family,
        "project_id": r.project_id,
        "query_text": r.query_text,
        "retrieval_limit": r.retrieval_limit,
        "topic": r.topic,
    }


def reasoning_bridge_result_to_dict(r: ReasoningBridgeResult) -> dict[str, Any]:
    interp = r.interpretation
    return {
        "analysis_error_message": r.analysis_error_message,
        "analysis_status": r.analysis_status,
        "bridge_disclaimer": r.bridge_disclaimer,
        "candidate_formulas": [_formula_to_dict(x) for x in r.candidate_formulas],
        "candidate_process_steps": [_step_to_dict(x) for x in r.candidate_process_steps],
        "evidence_anchors": [_anchor_to_dict(x) for x in r.evidence_anchors],
        "generated_at": r.generated_at,
        "governance_normative_block": r.governance_normative_block,
        "interpretation": None
        if interp is None
        else {
            "confidence": interp.confidence,
            "problem_family_id": interp.problem_family_id,
            "problem_family_label": interp.problem_family_label,
            "query_tokens_matched": list(interp.query_tokens_matched),
        },
        "project_id": r.project_id,
        "query_text": r.query_text,
        "retrieval_message": r.retrieval_message,
        "retrieval_normative_source": r.retrieval_normative_source,
        "retrieval_status": r.retrieval_status,
        "schema_version": r.schema_version,
        "supported_execution_steps": [_sup_to_dict(x) for x in r.supported_execution_steps],
        "unsupported_gaps": [_gap_to_dict(x) for x in r.unsupported_gaps],
        "warnings": list(r.warnings),
    }


def reasoning_bridge_result_from_dict(d: dict[str, Any]) -> ReasoningBridgeResult:
    ri = d.get("interpretation")
    interp: ProblemInterpretation | None = None
    if isinstance(ri, dict):
        interp = ProblemInterpretation(
            problem_family_id=ri["problem_family_id"],
            problem_family_label=ri.get("problem_family_label", ""),
            confidence=ri.get("confidence", "low"),
            query_tokens_matched=tuple(ri.get("query_tokens_matched", []) or []),
        )
    return ReasoningBridgeResult(
        project_id=d["project_id"],
        query_text=d["query_text"],
        schema_version=d.get("schema_version", "r2b.1"),
        analysis_status=d.get("analysis_status", "ok"),
        analysis_error_message=d.get("analysis_error_message"),
        generated_at=d.get("generated_at", ""),
        bridge_disclaimer=d.get(
            "bridge_disclaimer",
            (
                "Reasoning bridge output is interpretive and capability-scoped. "
                "Governed retrieval fragments remain the only normative evidence; "
                "derived artifacts and execution steps are labeled and subordinate."
            ),
        ),
        retrieval_status=d.get("retrieval_status", ""),
        retrieval_normative_source=d.get("retrieval_normative_source", "n_a"),
        governance_normative_block=d.get("governance_normative_block"),
        retrieval_message=d.get("retrieval_message", ""),
        interpretation=interp,
        candidate_process_steps=tuple(
            _step_from_dict(x) for x in d.get("candidate_process_steps", []) if isinstance(x, dict)
        ),
        candidate_formulas=tuple(
            _formula_from_dict(x) for x in d.get("candidate_formulas", []) if isinstance(x, dict)
        ),
        supported_execution_steps=tuple(
            _sup_from_dict(x) for x in d.get("supported_execution_steps", []) if isinstance(x, dict)
        ),
        unsupported_gaps=tuple(
            _gap_from_dict(x) for x in d.get("unsupported_gaps", []) if isinstance(x, dict)
        ),
        evidence_anchors=tuple(
            _anchor_from_dict(x) for x in d.get("evidence_anchors", []) if isinstance(x, dict)
        ),
        warnings=tuple(d.get("warnings", []) or []),
    )


def _step_to_dict(s: CandidateProcessStep) -> dict[str, Any]:
    return {
        "label": s.label,
        "notes": s.notes,
        "process_scope": s.process_scope,
        "step_id": s.step_id,
        "supported_by_anchors": [_anchor_to_dict(a) for a in s.supported_by_anchors],
    }


def _step_from_dict(d: dict[str, Any]) -> CandidateProcessStep:
    anc = tuple(_anchor_from_dict(x) for x in d.get("supported_by_anchors", []) if isinstance(x, dict))
    return CandidateProcessStep(
        step_id=d["step_id"],
        label=d.get("label", ""),
        process_scope=d.get("process_scope", "heuristic_vertical_slice"),
        supported_by_anchors=anc,
        notes=d.get("notes", ""),
    )


def _formula_to_dict(f: CandidateFormulaOrCheck) -> dict[str, Any]:
    return {
        "execution_status": f.execution_status,
        "formula_id": f.formula_id,
        "label": f.label,
        "non_authoritative": f.non_authoritative,
        "source": f.source,
        "supported_by_anchors": [_anchor_to_dict(a) for a in f.supported_by_anchors],
    }


def _formula_from_dict(d: dict[str, Any]) -> CandidateFormulaOrCheck:
    anc = tuple(_anchor_from_dict(x) for x in d.get("supported_by_anchors", []) if isinstance(x, dict))
    return CandidateFormulaOrCheck(
        formula_id=d["formula_id"],
        label=d.get("label", ""),
        source=d.get("source", "derived_registry"),
        execution_status=d.get("execution_status", "recognition_only"),
        supported_by_anchors=anc,
        non_authoritative=bool(d.get("non_authoritative", True)),
    )


def _sup_to_dict(s: SupportedExecutionStep) -> dict[str, Any]:
    return {
        "authority_boundary": s.authority_boundary,
        "calculation_id": s.calculation_id,
        "kind": s.kind,
        "method_label": s.method_label,
        "node_id": s.node_id,
        "notes": s.notes,
        "step_id": s.step_id,
    }


def _sup_from_dict(d: dict[str, Any]) -> SupportedExecutionStep:
    return SupportedExecutionStep(
        step_id=d["step_id"],
        kind=d.get("kind", "deterministic_computation_other"),
        calculation_id=d.get("calculation_id", ""),
        node_id=d.get("node_id", ""),
        method_label=d.get("method_label", ""),
        authority_boundary=d.get("authority_boundary", ""),
        notes=d.get("notes", ""),
    )


def _gap_to_dict(g: UnsupportedReasoningGap) -> dict[str, Any]:
    return {"category": g.category, "gap_id": g.gap_id, "message": g.message}


def _gap_from_dict(d: dict[str, Any]) -> UnsupportedReasoningGap:
    return UnsupportedReasoningGap(
        gap_id=d["gap_id"],
        category=d.get("category", "insufficient_retrieval"),
        message=d.get("message", ""),
    )


__all__ = [
    "reasoning_bridge_request_to_dict",
    "reasoning_bridge_result_from_dict",
    "reasoning_bridge_result_to_dict",
]
