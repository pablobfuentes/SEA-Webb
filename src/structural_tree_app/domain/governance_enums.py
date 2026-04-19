"""Governance lifecycle, disposition, and event types (Phase G0)."""

from __future__ import annotations

from enum import Enum


class GovernancePipelineStage(str, Enum):
    """Processing stage for a document under governance (ordered conceptually, not enforced as FSM in G0)."""

    INGESTED = "ingested"
    ANALYZED = "analyzed"
    CLASSIFIED = "classified"
    COMPARED = "compared"
    ASSESSED = "assessed"
    PROPOSED = "proposed"


class DocumentGovernanceDisposition(str, Enum):
    """Operational truth / review status for authoritative retrieval policy (G0 data model)."""

    PENDING_REVIEW = "pending_review"
    ACTIVE = "active"
    SUPPORTING = "supporting"
    SUPERSEDED = "superseded"
    CONFLICTING_UNRESOLVED = "conflicting_unresolved"
    REJECTED = "rejected"


class GovernanceEventType(str, Enum):
    """Append-only governance audit event types."""

    BASELINE_INITIALIZED = "baseline_initialized"
    PROJECTION_UPDATED = "projection_updated"
    DOCUMENT_GOVERNANCE_UPSERTED = "document_governance_upserted"
    DISPOSITION_CHANGED = "disposition_changed"
    PIPELINE_STAGE_CHANGED = "pipeline_stage_changed"
    TRUTH_PROPOSAL_CREATED = "truth_proposal_created"
    TRUTH_PROPOSAL_APPROVED = "truth_proposal_approved"
    TRUTH_PROPOSAL_REJECTED = "truth_proposal_rejected"


class TruthProposalStatus(str, Enum):
    """Lifecycle for a persisted G3 truth proposal (not retrieval truth until approved + G4 wiring)."""

    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"


class CorpusAssessmentCandidateRelation(str, Enum):
    """
    G2 corpus comparison labels — **candidates only**, not governance truth.

    Human or later phases (G3+) may reject or refine these signals.
    """

    DUPLICATE_CANDIDATE = "duplicate_candidate"
    OVERLAP_CANDIDATE = "overlap_candidate"
    CONTRADICTION_CANDIDATE = "contradiction_candidate"
    SUPERSESSION_CANDIDATE = "supersession_candidate"
    SUPPORTING_CANDIDATE = "supporting_candidate"


class GovernanceRetrievalBinding(str, Enum):
    """
    How authoritative retrieval selects documents.

    ``legacy_allowed_documents``: use ``Project.active_code_context.allowed_document_ids`` only
    (current behavior; G4 may switch to explicit_projection).
    """

    LEGACY_ALLOWED_DOCUMENTS = "legacy_allowed_documents"
    EXPLICIT_PROJECTION = "explicit_projection"


__all__ = [
    "CorpusAssessmentCandidateRelation",
    "DocumentGovernanceDisposition",
    "GovernanceEventType",
    "GovernancePipelineStage",
    "GovernanceRetrievalBinding",
    "TruthProposalStatus",
]
