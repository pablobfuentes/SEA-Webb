"""
R2B — Reasoning / formula-selection bridge (auditable; subordinate to retrieval + governed fragments).

Not a solver, not chain-of-thought: structured interpretation + explicit capability boundaries for U5.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from structural_tree_app.domain.models import utc_now

# --- Request -----------------------------------------------------------------

ReasoningBridgeCitationMode = Literal["normative_active_primary", "approved_ingested"]


@dataclass(frozen=True)
class ReasoningBridgeRequest:
    """Same retrieval parameters as ``LocalAssistQuery`` (without U3 / assumptions flags)."""

    project_id: str
    query_text: str
    citation_authority: ReasoningBridgeCitationMode = "normative_active_primary"
    retrieval_limit: int = 20
    match_project_primary_standard_family: bool = True
    language: str | None = None
    topic: str | None = None
    document_ids: frozenset[str] | None = None
    include_deterministic_context: bool = True
    """When True, scan live tree for preliminary M5 / other calculation hooks (read-only)."""


# --- Evidence / authority ----------------------------------------------------

EvidenceAnchorKind = Literal[
    "retrieval_hit",
    "derived_formula_registry",
    "derived_topic_digest",
    "derived_document_digest",
    "derived_navigation_hint",
]


@dataclass(frozen=True)
class EvidenceAnchor:
    """
    Traceable pointer to governed material (retrieval) or derived layer (navigation only).

    ``authority_note`` must state whether the row is normative evidence vs derived aid.
    """

    anchor_id: str
    anchor_kind: EvidenceAnchorKind
    document_id: str
    fragment_id: str
    document_content_hash: str
    fragment_content_hash: str
    provenance_label: str
    authority_note: str


# --- Interpretation -----------------------------------------------------------

ProblemConfidence = Literal["deterministic_keyword_map", "low"]


@dataclass(frozen=True)
class ProblemInterpretation:
    """Narrow, keyword-driven problem family (not NLP magic)."""

    problem_family_id: str
    problem_family_label: str
    confidence: ProblemConfidence
    query_tokens_matched: tuple[str, ...]


ProcessStepScope = Literal["evidence_led", "derived_navigation", "heuristic_vertical_slice"]


@dataclass(frozen=True)
class CandidateProcessStep:
    step_id: str
    label: str
    process_scope: ProcessStepScope
    supported_by_anchors: tuple[EvidenceAnchor, ...]
    notes: str


FormulaExecutionStatus = Literal[
    "deterministic_m5_available",
    "recognition_only",
    "insufficient_evidence_link",
]


@dataclass(frozen=True)
class CandidateFormulaOrCheck:
    formula_id: str
    label: str
    source: Literal["derived_registry", "retrieval_passage_heuristic"]
    execution_status: FormulaExecutionStatus
    supported_by_anchors: tuple[EvidenceAnchor, ...]
    non_authoritative: bool


@dataclass(frozen=True)
class SupportedExecutionStep:
    """Deterministic engine step — not normative document evidence."""

    step_id: str
    kind: Literal["deterministic_m5_preliminary", "deterministic_computation_other"]
    calculation_id: str
    node_id: str
    method_label: str
    authority_boundary: str
    notes: str


UnsupportedGapCategory = Literal[
    "empty_query",
    "query_too_long",
    "insufficient_retrieval",
    "governance_normative_block",
    "outside_vertical_slice",
    "no_derived_knowledge_bundle",
    "project_error",
]


@dataclass(frozen=True)
class UnsupportedReasoningGap:
    gap_id: str
    category: UnsupportedGapCategory
    message: str


ReasoningAnalysisStatus = Literal["ok", "unsupported_query", "error"]


@dataclass(frozen=True)
class ReasoningBridgeResult:
    """Serializable bridge output for UI / U5; deterministic ordering in codec."""

    project_id: str
    query_text: str
    schema_version: str = "r2b.1"
    analysis_status: ReasoningAnalysisStatus = "ok"
    analysis_error_message: str | None = None
    generated_at: str = field(default_factory=utc_now)
    bridge_disclaimer: str = (
        "Reasoning bridge output is interpretive and capability-scoped. "
        "Governed retrieval fragments remain the only normative evidence; "
        "derived artifacts and execution steps are labeled and subordinate."
    )
    retrieval_status: str = "insufficient_evidence"
    retrieval_normative_source: str = "n_a"
    governance_normative_block: str | None = None
    retrieval_message: str = ""
    interpretation: ProblemInterpretation | None = None
    candidate_process_steps: tuple[CandidateProcessStep, ...] = ()
    candidate_formulas: tuple[CandidateFormulaOrCheck, ...] = ()
    supported_execution_steps: tuple[SupportedExecutionStep, ...] = ()
    unsupported_gaps: tuple[UnsupportedReasoningGap, ...] = ()
    evidence_anchors: tuple[EvidenceAnchor, ...] = ()
    warnings: tuple[str, ...] = ()


__all__ = [
    "CandidateFormulaOrCheck",
    "CandidateProcessStep",
    "EvidenceAnchor",
    "EvidenceAnchorKind",
    "FormulaExecutionStatus",
    "ProblemInterpretation",
    "ProblemConfidence",
    "ProcessStepScope",
    "ReasoningAnalysisStatus",
    "ReasoningBridgeRequest",
    "ReasoningBridgeResult",
    "ReasoningBridgeCitationMode",
    "SupportedExecutionStep",
    "UnsupportedGapCategory",
    "UnsupportedReasoningGap",
]
