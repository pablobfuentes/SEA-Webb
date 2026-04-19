"""Persisted governance layer: active knowledge projection, document index, event log (Phase G0)."""

from __future__ import annotations

from pathlib import Path

from jsonschema.exceptions import ValidationError

from structural_tree_app.domain.governance_codec import (
    active_knowledge_projection_from_dict,
    active_knowledge_projection_to_dict,
    document_corpus_assessment_from_dict,
    document_corpus_assessment_to_dict,
    document_governance_index_from_dict,
    document_governance_index_to_dict,
    governance_event_log_from_dict,
    governance_event_log_to_dict,
    truth_proposal_from_dict,
    truth_proposal_to_dict,
)
from structural_tree_app.domain.governance_enums import GovernanceEventType, GovernanceRetrievalBinding
from structural_tree_app.domain.governance_models import (
    ActiveKnowledgeProjection,
    DocumentCorpusAssessment,
    DocumentGovernanceIndex,
    GovernanceEvent,
    GovernanceEventLog,
    TruthProposal,
)
from structural_tree_app.domain.models import new_id, utc_now
from structural_tree_app.storage.json_repository import JsonRepository
from structural_tree_app.validation.json_schema import (
    validate_active_knowledge_projection_payload,
    validate_document_corpus_assessment_payload,
    validate_document_governance_index_payload,
    validate_governance_event_log_payload,
    validate_truth_proposal_payload,
)


class GovernanceStoreError(Exception):
    """Invalid or inconsistent governance persistence under a project."""


class GovernanceStore:
    """Read/write `{project_id}/governance/*.json` with schema validation."""

    ACTIVE_KNOWLEDGE_PROJECTION_JSON = "active_knowledge_projection.json"
    DOCUMENT_GOVERNANCE_INDEX_JSON = "document_governance_index.json"
    GOVERNANCE_EVENT_LOG_JSON = "governance_event_log.json"
    ASSESSMENTS_SUBDIR = "assessments"
    PROPOSALS_SUBDIR = "proposals"

    def __init__(self, repository: JsonRepository) -> None:
        self._repo = repository

    def _rel(self, project_id: str, *parts: str) -> str:
        return str(Path(project_id, *parts))

    def try_load_active_knowledge_projection(self, project_id: str) -> ActiveKnowledgeProjection | None:
        rel = self._rel(project_id, "governance", self.ACTIVE_KNOWLEDGE_PROJECTION_JSON)
        if not self._repo.exists(rel):
            return None
        try:
            raw = self._repo.read(rel)
        except ValueError as e:
            raise GovernanceStoreError(str(e)) from e
        try:
            validate_active_knowledge_projection_payload(raw)
        except ValidationError as e:
            raise GovernanceStoreError(f"Invalid active knowledge projection: {e.message}") from e
        return active_knowledge_projection_from_dict(raw)

    def save_active_knowledge_projection(self, projection: ActiveKnowledgeProjection) -> None:
        payload = active_knowledge_projection_to_dict(projection)
        validate_active_knowledge_projection_payload(payload)
        self._repo.write(
            self._rel(projection.project_id, "governance", self.ACTIVE_KNOWLEDGE_PROJECTION_JSON),
            payload,
        )

    def try_load_document_governance_index(self, project_id: str) -> DocumentGovernanceIndex | None:
        rel = self._rel(project_id, "governance", self.DOCUMENT_GOVERNANCE_INDEX_JSON)
        if not self._repo.exists(rel):
            return None
        try:
            raw = self._repo.read(rel)
        except ValueError as e:
            raise GovernanceStoreError(str(e)) from e
        try:
            validate_document_governance_index_payload(raw)
        except ValidationError as e:
            raise GovernanceStoreError(f"Invalid document governance index: {e.message}") from e
        return document_governance_index_from_dict(raw)

    def save_document_governance_index(self, index: DocumentGovernanceIndex) -> None:
        payload = document_governance_index_to_dict(index)
        validate_document_governance_index_payload(payload)
        self._repo.write(
            self._rel(index.project_id, "governance", self.DOCUMENT_GOVERNANCE_INDEX_JSON),
            payload,
        )

    def try_load_governance_event_log(self, project_id: str) -> GovernanceEventLog | None:
        rel = self._rel(project_id, "governance", self.GOVERNANCE_EVENT_LOG_JSON)
        if not self._repo.exists(rel):
            return None
        try:
            raw = self._repo.read(rel)
        except ValueError as e:
            raise GovernanceStoreError(str(e)) from e
        try:
            validate_governance_event_log_payload(raw)
        except ValidationError as e:
            raise GovernanceStoreError(f"Invalid governance event log: {e.message}") from e
        return governance_event_log_from_dict(raw)

    def save_governance_event_log(self, log: GovernanceEventLog) -> None:
        payload = governance_event_log_to_dict(log)
        validate_governance_event_log_payload(payload)
        self._repo.write(
            self._rel(log.project_id, "governance", self.GOVERNANCE_EVENT_LOG_JSON),
            payload,
        )

    def try_load_document_corpus_assessment(
        self, project_id: str, subject_document_id: str
    ) -> DocumentCorpusAssessment | None:
        rel = self._rel(project_id, "governance", self.ASSESSMENTS_SUBDIR, f"{subject_document_id}.json")
        if not self._repo.exists(rel):
            return None
        try:
            raw = self._repo.read(rel)
        except ValueError as e:
            raise GovernanceStoreError(str(e)) from e
        try:
            validate_document_corpus_assessment_payload(raw)
        except ValidationError as e:
            raise GovernanceStoreError(f"Invalid document corpus assessment: {e.message}") from e
        return document_corpus_assessment_from_dict(raw)

    def save_document_corpus_assessment(self, assessment: DocumentCorpusAssessment) -> None:
        payload = document_corpus_assessment_to_dict(assessment)
        validate_document_corpus_assessment_payload(payload)
        self._repo.write(
            self._rel(
                assessment.project_id,
                "governance",
                self.ASSESSMENTS_SUBDIR,
                f"{assessment.subject_document_id}.json",
            ),
            payload,
        )

    def try_load_truth_proposal(self, project_id: str, proposal_id: str) -> TruthProposal | None:
        rel = self._rel(project_id, "governance", self.PROPOSALS_SUBDIR, f"{proposal_id}.json")
        if not self._repo.exists(rel):
            return None
        try:
            raw = self._repo.read(rel)
        except ValueError as e:
            raise GovernanceStoreError(str(e)) from e
        try:
            validate_truth_proposal_payload(raw)
        except ValidationError as e:
            raise GovernanceStoreError(f"Invalid truth proposal: {e.message}") from e
        return truth_proposal_from_dict(raw)

    def save_truth_proposal(self, proposal: TruthProposal) -> None:
        payload = truth_proposal_to_dict(proposal)
        validate_truth_proposal_payload(payload)
        self._repo.write(
            self._rel(proposal.project_id, "governance", self.PROPOSALS_SUBDIR, f"{proposal.proposal_id}.json"),
            payload,
        )

    def append_governance_events(self, project_id: str, events: tuple[GovernanceEvent, ...]) -> None:
        """Append events to the governance log (load + save)."""
        if not events:
            return
        log = self.try_load_governance_event_log(project_id)
        if log is None:
            raise GovernanceStoreError("Governance event log missing; initialize baseline first.")
        merged = GovernanceEventLog(
            schema_version=log.schema_version,
            project_id=project_id,
            events=log.events + events,
        )
        self.save_governance_event_log(merged)

    def initialize_governance_baseline(self, project_id: str, *, actor: str = "system") -> bool:
        """
        Create G0 baseline files if the projection file is absent.

        Returns True if files were written, False if baseline already present (idempotent).

        Does not change retrieval behavior until a later phase wires projection into services;
        default binding is ``legacy_allowed_documents``.
        """
        rel_proj = self._rel(project_id, "governance", self.ACTIVE_KNOWLEDGE_PROJECTION_JSON)
        has_idx = self._repo.exists(self._rel(project_id, "governance", self.DOCUMENT_GOVERNANCE_INDEX_JSON))
        has_log = self._repo.exists(self._rel(project_id, "governance", self.GOVERNANCE_EVENT_LOG_JSON))
        if self._repo.exists(rel_proj):
            return False
        if has_idx or has_log:
            raise GovernanceStoreError(
                "Partial governance state: projection missing but index or event log exists."
            )
        now = utc_now()
        binding = GovernanceRetrievalBinding.LEGACY_ALLOWED_DOCUMENTS.value
        projection = ActiveKnowledgeProjection(
            project_id=project_id,
            schema_version="g0.1",
            updated_at=now,
            retrieval_binding=GovernanceRetrievalBinding.LEGACY_ALLOWED_DOCUMENTS,
        )
        event = GovernanceEvent(
            project_id=project_id,
            event_type=GovernanceEventType.BASELINE_INITIALIZED,
            rationale="G0 governance baseline initialized (legacy retrieval binding; no retrieval wiring change).",
            occurred_at=now,
            id=new_id("gov"),
            actor=actor,
            affected_document_ids=(),
            prior_retrieval_binding=None,
            new_retrieval_binding=binding,
            prior_projection_schema_version=None,
            payload={"governance_phase": "g0"},
        )
        index = DocumentGovernanceIndex(project_id=project_id, schema_version="g1.1", updated_at=now, by_document_id={})
        log = GovernanceEventLog(schema_version="g0.1", project_id=project_id, events=(event,))
        self.save_active_knowledge_projection(projection)
        self.save_document_governance_index(index)
        self.save_governance_event_log(log)
        return True


__all__ = ["GovernanceStore", "GovernanceStoreError"]
