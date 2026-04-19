"""Dataclasses for document governance, active knowledge projection, and audit events (Phase G0+)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from structural_tree_app.domain.governance_enums import (
    CorpusAssessmentCandidateRelation,
    DocumentGovernanceDisposition,
    GovernanceEventType,
    GovernancePipelineStage,
    GovernanceRetrievalBinding,
    TruthProposalStatus,
)
from structural_tree_app.domain.models import new_id, utc_now


@dataclass(frozen=True)
class DocumentAnalysisSnapshot:
    """Deterministic post-ingest analysis facts (text segmented, fragments persisted)."""

    fragment_count: int = 0
    normalized_char_count: int = 0


@dataclass(frozen=True)
class DocumentClassificationSnapshot:
    """
    Narrow, explicit classification metadata for governance (G1).

    ``classification_incomplete`` must stay true when normative role or scope is not yet
    confidently known — never implied from ingestion alone except where deterministic.
    """

    normative_classification: str
    authority_level: str
    standard_family: str | None = None
    discipline: str | None = None
    topic_scope_tags: tuple[str, ...] = ()
    classification_incomplete: bool = True


@dataclass(frozen=True)
class ActiveKnowledgeProjection:
    """
    Operational authoritative corpus for AI retrieval (future G4 wiring).

    When ``retrieval_binding`` is ``legacy_allowed_documents``, retrieval services keep
    current behavior using ``active_code_context.allowed_document_ids``; list fields are advisory.
    """

    project_id: str
    schema_version: str = "g0.1"
    updated_at: str = field(default_factory=utc_now)
    retrieval_binding: GovernanceRetrievalBinding = GovernanceRetrievalBinding.LEGACY_ALLOWED_DOCUMENTS
    authoritative_document_ids: tuple[str, ...] = ()
    supporting_document_ids: tuple[str, ...] = ()
    excluded_from_authoritative_document_ids: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class DocumentGovernanceRecord:
    """Per-document governance state (pipeline + disposition + G1 analysis/classification)."""

    document_id: str
    pipeline_stage: GovernancePipelineStage
    disposition: DocumentGovernanceDisposition
    updated_at: str = field(default_factory=utc_now)
    notes: str = ""
    analysis: DocumentAnalysisSnapshot | None = None
    classification: DocumentClassificationSnapshot | None = None


@dataclass(frozen=True)
class DocumentGovernanceIndex:
    """Project-scoped map of document_id -> governance record."""

    project_id: str
    schema_version: str = "g1.1"
    updated_at: str = field(default_factory=utc_now)
    by_document_id: dict[str, DocumentGovernanceRecord] = field(default_factory=dict)


@dataclass(frozen=True)
class GovernanceEvent:
    """
    Immutable audit record: what changed, when, why, on which projection/documents.

    ``payload`` holds extensibility for G1+ without schema churn for known fields.
    """

    project_id: str
    event_type: GovernanceEventType
    rationale: str
    occurred_at: str = field(default_factory=utc_now)
    id: str = field(default_factory=lambda: new_id("gov"))
    actor: str = "system"
    affected_document_ids: tuple[str, ...] = ()
    prior_retrieval_binding: str | None = None
    new_retrieval_binding: str | None = None
    prior_projection_schema_version: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GovernanceEventLog:
    """Ordered list of events (persisted as JSON array under schema)."""

    schema_version: str = "g0.1"
    project_id: str = ""
    events: tuple[GovernanceEvent, ...] = ()


@dataclass(frozen=True)
class CorpusAssessmentCandidate:
    """
    One directed relation from ``subject_document_id`` toward ``other_document_id``.

    ``confidence`` is a coarse heuristic tier (``high`` / ``medium`` / ``low``), not a statistical score.
    """

    other_document_id: str
    relation: CorpusAssessmentCandidateRelation
    confidence: str
    signals: tuple[str, ...] = ()
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DocumentCorpusAssessment:
    """
    G2 persisted artifact: deterministic, candidate-level comparison vs the governed corpus.

    ``assessment_framing`` must remain explicit: this is **not** an active-truth decision.
    """

    project_id: str
    subject_document_id: str
    schema_version: str = "g2.1"
    assessed_at: str = field(default_factory=utc_now)
    assessment_framing: str = "candidate_assessment_not_governance_decision"
    candidates: tuple[CorpusAssessmentCandidate, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class TruthProposalProjectionDelta:
    """Deterministic, explicit set operations on the active knowledge projection (advisory until G4 retrieval)."""

    add_authoritative_document_ids: tuple[str, ...] = ()
    remove_authoritative_document_ids: tuple[str, ...] = ()
    add_supporting_document_ids: tuple[str, ...] = ()
    remove_supporting_document_ids: tuple[str, ...] = ()
    add_excluded_document_ids: tuple[str, ...] = ()
    remove_excluded_document_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class TruthProposalDispositionChange:
    """Proposed ``DocumentGovernanceDisposition`` transition for one document (auditable)."""

    document_id: str
    from_disposition: str
    to_disposition: str
    rationale_rule_id: str


@dataclass(frozen=True)
class TruthProposalDecision:
    """Recorded human/system decision on a proposal (immutable once written)."""

    outcome: str
    decided_at: str = field(default_factory=utc_now)
    actor: str = "system"
    notes: str = ""


@dataclass(frozen=True)
class TruthProposal:
    """
    G3 structured proposal: how governed truth should change, pending explicit approval.

    Does not itself change retrieval; approval mutates projection + index with audit events.
    """

    proposal_id: str
    project_id: str
    subject_document_id: str
    schema_version: str = "g3.1"
    created_at: str = field(default_factory=utc_now)
    status: TruthProposalStatus = TruthProposalStatus.PENDING_APPROVAL
    source_assessment_schema_version: str = "g2.1"
    rules_applied: tuple[str, ...] = ()
    projection_delta: TruthProposalProjectionDelta = field(default_factory=TruthProposalProjectionDelta)
    disposition_changes: tuple[TruthProposalDispositionChange, ...] = ()
    narrative: str = ""
    decision: TruthProposalDecision | None = None


__all__ = [
    "ActiveKnowledgeProjection",
    "CorpusAssessmentCandidate",
    "DocumentAnalysisSnapshot",
    "DocumentClassificationSnapshot",
    "DocumentCorpusAssessment",
    "DocumentGovernanceIndex",
    "DocumentGovernanceRecord",
    "GovernanceEvent",
    "GovernanceEventLog",
    "TruthProposal",
    "TruthProposalDecision",
    "TruthProposalDispositionChange",
    "TruthProposalProjectionDelta",
]
