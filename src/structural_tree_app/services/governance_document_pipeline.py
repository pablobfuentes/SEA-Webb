"""G1: document governance pipeline hooks (ingested → analyzed → classified) without retrieval changes."""

from __future__ import annotations

from structural_tree_app.domain.enums import NormativeClassification
from structural_tree_app.domain.governance_enums import (
    DocumentGovernanceDisposition,
    GovernanceEventType,
    GovernancePipelineStage,
)
from structural_tree_app.domain.governance_models import (
    DocumentAnalysisSnapshot,
    DocumentClassificationSnapshot,
    DocumentGovernanceIndex,
    DocumentGovernanceRecord,
    GovernanceEvent,
)
from structural_tree_app.domain.models import Document, new_id, utc_now
from structural_tree_app.services.governance_store import GovernanceStore, GovernanceStoreError


def classification_complete_for_g1(doc: Document) -> bool:
    """Deterministic G1 rule: unknown normative class, or primary_standard without standard_family, is incomplete."""
    if doc.normative_classification == NormativeClassification.UNKNOWN:
        return False
    if doc.normative_classification == NormativeClassification.PRIMARY_STANDARD:
        return bool(doc.standard_family and doc.standard_family.strip())
    return True


def classification_snapshot_from_document(doc: Document) -> DocumentClassificationSnapshot:
    tags = tuple(sorted(str(t) for t in (doc.topics or [])))
    incomplete = not classification_complete_for_g1(doc)
    return DocumentClassificationSnapshot(
        normative_classification=doc.normative_classification.value,
        authority_level=doc.authority_level.value,
        standard_family=doc.standard_family,
        discipline=doc.discipline,
        topic_scope_tags=tags,
        classification_incomplete=incomplete,
    )


def apply_governance_after_successful_ingestion(
    store: GovernanceStore,
    project_id: str,
    document: Document,
    *,
    fragment_count: int,
    normalized_char_count: int,
    actor: str = "ingestion",
) -> None:
    """
    After document.json + fragments are persisted and the project ingested list is updated:

    - Ensures G0 governance baseline files exist.
    - Records pipeline progression in the governance event log (ingested → analyzed, and
      analyzed → classified when classification is complete under G1 deterministic rules).
    - Persists the terminal ``DocumentGovernanceRecord`` (analyzed or classified).

    Does not approve documents or change retrieval.
    """
    store.initialize_governance_baseline(project_id)
    index = store.try_load_document_governance_index(project_id)
    if index is None:
        raise GovernanceStoreError("Expected document governance index after baseline initialization.")

    now = utc_now()
    analysis = DocumentAnalysisSnapshot(
        fragment_count=fragment_count,
        normalized_char_count=normalized_char_count,
    )
    cl = classification_snapshot_from_document(document)
    complete = classification_complete_for_g1(document)
    final_stage = GovernancePipelineStage.CLASSIFIED if complete else GovernancePipelineStage.ANALYZED

    record = DocumentGovernanceRecord(
        document_id=document.id,
        pipeline_stage=final_stage,
        disposition=DocumentGovernanceDisposition.PENDING_REVIEW,
        updated_at=now,
        notes="G1 post-ingestion governance record (ingestion does not imply approval).",
        analysis=analysis,
        classification=cl,
    )

    new_by = dict(index.by_document_id)
    new_by[document.id] = record
    new_index = DocumentGovernanceIndex(
        project_id=project_id,
        schema_version="g1.1",
        updated_at=now,
        by_document_id=new_by,
    )
    store.save_document_governance_index(new_index)

    ev_ingested = GovernanceEvent(
        project_id=project_id,
        event_type=GovernanceEventType.PIPELINE_STAGE_CHANGED,
        rationale="Document bundle persisted (ingested).",
        occurred_at=now,
        id=new_id("gov"),
        actor=actor,
        affected_document_ids=(document.id,),
        payload={
            "document_id": document.id,
            "new_stage": GovernancePipelineStage.INGESTED.value,
            "prior_stage": None,
        },
    )
    ev_analyzed = GovernanceEvent(
        project_id=project_id,
        event_type=GovernanceEventType.PIPELINE_STAGE_CHANGED,
        rationale="Normalized text segmented into fragments (analyzed).",
        occurred_at=now,
        id=new_id("gov"),
        actor=actor,
        affected_document_ids=(document.id,),
        payload={
            "document_id": document.id,
            "new_stage": GovernancePipelineStage.ANALYZED.value,
            "prior_stage": GovernancePipelineStage.INGESTED.value,
        },
    )
    extra: tuple[GovernanceEvent, ...]
    if final_stage == GovernancePipelineStage.CLASSIFIED:
        ev_classified = GovernanceEvent(
            project_id=project_id,
            event_type=GovernanceEventType.PIPELINE_STAGE_CHANGED,
            rationale="Deterministic G1 classification complete from document metadata.",
            occurred_at=now,
            id=new_id("gov"),
            actor=actor,
            affected_document_ids=(document.id,),
            payload={
                "document_id": document.id,
                "new_stage": GovernancePipelineStage.CLASSIFIED.value,
                "prior_stage": GovernancePipelineStage.ANALYZED.value,
            },
        )
        extra = (ev_ingested, ev_analyzed, ev_classified)
    else:
        extra = (ev_ingested, ev_analyzed)

    store.append_governance_events(project_id, extra)


def promote_document_to_classified(
    store: GovernanceStore,
    project_id: str,
    document_id: str,
    classification: DocumentClassificationSnapshot,
    *,
    analysis: DocumentAnalysisSnapshot | None = None,
    actor: str = "system",
    rationale: str = "Document promoted to classified (G1 explicit).",
) -> None:
    """Set pipeline to classified with an explicit classification snapshot (e.g. after manual review)."""
    store.initialize_governance_baseline(project_id)
    index = store.try_load_document_governance_index(project_id)
    if index is None:
        raise GovernanceStoreError("Expected document governance index after baseline initialization.")
    prev = index.by_document_id.get(document_id)
    if prev is None:
        raise ValueError(f"No governance record for document_id={document_id}")
    now = utc_now()
    merged_analysis = analysis if analysis is not None else prev.analysis
    record = DocumentGovernanceRecord(
        document_id=document_id,
        pipeline_stage=GovernancePipelineStage.CLASSIFIED,
        disposition=prev.disposition,
        updated_at=now,
        notes=prev.notes,
        analysis=merged_analysis,
        classification=classification,
    )
    new_by = dict(index.by_document_id)
    new_by[document_id] = record
    new_index = DocumentGovernanceIndex(
        project_id=project_id,
        schema_version="g1.1",
        updated_at=now,
        by_document_id=new_by,
    )
    store.save_document_governance_index(new_index)
    ev = GovernanceEvent(
        project_id=project_id,
        event_type=GovernanceEventType.PIPELINE_STAGE_CHANGED,
        rationale=rationale,
        occurred_at=now,
        id=new_id("gov"),
        actor=actor,
        affected_document_ids=(document_id,),
        payload={
            "document_id": document_id,
            "new_stage": GovernancePipelineStage.CLASSIFIED.value,
            "prior_stage": prev.pipeline_stage.value,
        },
    )
    store.append_governance_events(project_id, (ev,))


__all__ = [
    "apply_governance_after_successful_ingestion",
    "classification_complete_for_g1",
    "classification_snapshot_from_document",
    "promote_document_to_classified",
]
