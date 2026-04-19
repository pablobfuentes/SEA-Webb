"""Serialize / deserialize governance models with deterministic JSON-friendly dicts."""

from __future__ import annotations

from typing import Any

from structural_tree_app.domain.governance_enums import (
    CorpusAssessmentCandidateRelation,
    DocumentGovernanceDisposition,
    GovernanceEventType,
    GovernancePipelineStage,
    GovernanceRetrievalBinding,
    TruthProposalStatus,
)
from structural_tree_app.domain.governance_models import (
    ActiveKnowledgeProjection,
    CorpusAssessmentCandidate,
    DocumentAnalysisSnapshot,
    DocumentClassificationSnapshot,
    DocumentCorpusAssessment,
    DocumentGovernanceIndex,
    DocumentGovernanceRecord,
    GovernanceEvent,
    GovernanceEventLog,
    TruthProposal,
    TruthProposalDecision,
    TruthProposalDispositionChange,
    TruthProposalProjectionDelta,
)


def active_knowledge_projection_to_dict(p: ActiveKnowledgeProjection) -> dict[str, Any]:
    d: dict[str, Any] = {
        "authoritative_document_ids": list(p.authoritative_document_ids),
        "excluded_from_authoritative_document_ids": list(p.excluded_from_authoritative_document_ids),
        "notes": p.notes,
        "project_id": p.project_id,
        "retrieval_binding": p.retrieval_binding.value,
        "schema_version": p.schema_version,
        "supporting_document_ids": list(p.supporting_document_ids),
        "updated_at": p.updated_at,
    }
    return dict(sorted(d.items()))


def active_knowledge_projection_from_dict(data: dict[str, Any]) -> ActiveKnowledgeProjection:
    rb = data.get("retrieval_binding", GovernanceRetrievalBinding.LEGACY_ALLOWED_DOCUMENTS.value)
    return ActiveKnowledgeProjection(
        project_id=data["project_id"],
        schema_version=data.get("schema_version", "g0.1"),
        updated_at=data["updated_at"],
        retrieval_binding=GovernanceRetrievalBinding(str(rb)),
        authoritative_document_ids=tuple(data.get("authoritative_document_ids", [])),
        supporting_document_ids=tuple(data.get("supporting_document_ids", [])),
        excluded_from_authoritative_document_ids=tuple(data.get("excluded_from_authoritative_document_ids", [])),
        notes=data.get("notes", "") or "",
    )


def document_analysis_snapshot_to_dict(a: DocumentAnalysisSnapshot) -> dict[str, Any]:
    d: dict[str, Any] = {
        "fragment_count": a.fragment_count,
        "normalized_char_count": a.normalized_char_count,
    }
    return dict(sorted(d.items()))


def document_analysis_snapshot_from_dict(data: dict[str, Any]) -> DocumentAnalysisSnapshot:
    return DocumentAnalysisSnapshot(
        fragment_count=int(data.get("fragment_count", 0)),
        normalized_char_count=int(data.get("normalized_char_count", 0)),
    )


def document_classification_snapshot_to_dict(c: DocumentClassificationSnapshot) -> dict[str, Any]:
    d: dict[str, Any] = {
        "authority_level": c.authority_level,
        "classification_incomplete": c.classification_incomplete,
        "discipline": c.discipline,
        "normative_classification": c.normative_classification,
        "standard_family": c.standard_family,
        "topic_scope_tags": list(c.topic_scope_tags),
    }
    return dict(sorted(d.items()))


def document_classification_snapshot_from_dict(data: dict[str, Any]) -> DocumentClassificationSnapshot:
    tags = data.get("topic_scope_tags") or []
    stags = tuple(sorted(str(x) for x in tags))
    return DocumentClassificationSnapshot(
        normative_classification=data["normative_classification"],
        authority_level=data["authority_level"],
        standard_family=data.get("standard_family"),
        discipline=data.get("discipline"),
        topic_scope_tags=stags,
        classification_incomplete=bool(data.get("classification_incomplete", True)),
    )


def document_governance_record_to_dict(r: DocumentGovernanceRecord) -> dict[str, Any]:
    d: dict[str, Any] = {
        "disposition": r.disposition.value,
        "document_id": r.document_id,
        "notes": r.notes,
        "pipeline_stage": r.pipeline_stage.value,
        "updated_at": r.updated_at,
    }
    if r.analysis is not None:
        d["analysis"] = document_analysis_snapshot_to_dict(r.analysis)
    if r.classification is not None:
        d["classification"] = document_classification_snapshot_to_dict(r.classification)
    return dict(sorted(d.items()))


def document_governance_record_from_dict(data: dict[str, Any]) -> DocumentGovernanceRecord:
    analysis = None
    if data.get("analysis") is not None:
        analysis = document_analysis_snapshot_from_dict(data["analysis"])
    classification = None
    if data.get("classification") is not None:
        classification = document_classification_snapshot_from_dict(data["classification"])
    return DocumentGovernanceRecord(
        document_id=data["document_id"],
        pipeline_stage=GovernancePipelineStage(data["pipeline_stage"]),
        disposition=DocumentGovernanceDisposition(data["disposition"]),
        updated_at=data["updated_at"],
        notes=data.get("notes", "") or "",
        analysis=analysis,
        classification=classification,
    )


def document_governance_index_to_dict(idx: DocumentGovernanceIndex) -> dict[str, Any]:
    by_doc: dict[str, Any] = {}
    for k in sorted(idx.by_document_id.keys()):
        by_doc[k] = document_governance_record_to_dict(idx.by_document_id[k])
    outer: dict[str, Any] = {
        "by_document_id": by_doc,
        "project_id": idx.project_id,
        "schema_version": idx.schema_version,
        "updated_at": idx.updated_at,
    }
    return dict(sorted(outer.items()))


def document_governance_index_from_dict(data: dict[str, Any]) -> DocumentGovernanceIndex:
    raw = data.get("by_document_id", {})
    by_id: dict[str, DocumentGovernanceRecord] = {}
    for doc_id, rec in raw.items():
        by_id[doc_id] = document_governance_record_from_dict(rec)
    return DocumentGovernanceIndex(
        project_id=data["project_id"],
        schema_version=data.get("schema_version", "g0.1"),
        updated_at=data["updated_at"],
        by_document_id=by_id,
    )


def governance_event_to_dict(e: GovernanceEvent) -> dict[str, Any]:
    d: dict[str, Any] = {
        "actor": e.actor,
        "affected_document_ids": list(e.affected_document_ids),
        "event_type": e.event_type.value,
        "id": e.id,
        "occurred_at": e.occurred_at,
        "payload": dict(sorted(e.payload.items())) if e.payload else {},
        "prior_projection_schema_version": e.prior_projection_schema_version,
        "prior_retrieval_binding": e.prior_retrieval_binding,
        "project_id": e.project_id,
        "rationale": e.rationale,
        "new_retrieval_binding": e.new_retrieval_binding,
    }
    return dict(sorted(d.items()))


def governance_event_from_dict(data: dict[str, Any]) -> GovernanceEvent:
    return GovernanceEvent(
        project_id=data["project_id"],
        event_type=GovernanceEventType(data["event_type"]),
        rationale=data.get("rationale", "") or "",
        occurred_at=data["occurred_at"],
        id=data["id"],
        actor=data.get("actor", "system") or "system",
        affected_document_ids=tuple(data.get("affected_document_ids", [])),
        prior_retrieval_binding=data.get("prior_retrieval_binding"),
        new_retrieval_binding=data.get("new_retrieval_binding"),
        prior_projection_schema_version=data.get("prior_projection_schema_version"),
        payload=dict(data.get("payload", {})),
    )


def governance_event_log_to_dict(log: GovernanceEventLog) -> dict[str, Any]:
    events = [governance_event_to_dict(e) for e in log.events]
    outer: dict[str, Any] = {
        "events": events,
        "project_id": log.project_id,
        "schema_version": log.schema_version,
    }
    return dict(sorted(outer.items()))


def governance_event_log_from_dict(data: dict[str, Any]) -> GovernanceEventLog:
    evs = tuple(governance_event_from_dict(x) for x in data.get("events", []))
    return GovernanceEventLog(
        schema_version=data.get("schema_version", "g0.1"),
        project_id=data.get("project_id", ""),
        events=evs,
    )


def _details_sorted(details: dict[str, Any]) -> dict[str, Any]:
    return dict(sorted((k, details[k]) for k in sorted(details.keys())))


def corpus_assessment_candidate_to_dict(c: CorpusAssessmentCandidate) -> dict[str, Any]:
    d: dict[str, Any] = {
        "confidence": c.confidence,
        "details": _details_sorted(dict(c.details)),
        "other_document_id": c.other_document_id,
        "relation": c.relation.value,
        "signals": list(c.signals),
    }
    return dict(sorted(d.items()))


def corpus_assessment_candidate_from_dict(data: dict[str, Any]) -> CorpusAssessmentCandidate:
    rel = CorpusAssessmentCandidateRelation(str(data["relation"]))
    sigs = data.get("signals") or []
    st = tuple(sorted(str(s) for s in sigs))
    det_raw = data.get("details") or {}
    det = _details_sorted({str(k): det_raw[k] for k in sorted(det_raw.keys())})
    return CorpusAssessmentCandidate(
        other_document_id=data["other_document_id"],
        relation=rel,
        confidence=str(data["confidence"]),
        signals=st,
        details=det,
    )


def document_corpus_assessment_to_dict(a: DocumentCorpusAssessment) -> dict[str, Any]:
    ordered = sorted(
        a.candidates,
        key=lambda x: (x.other_document_id, x.relation.value, x.confidence, x.signals),
    )
    cands = [corpus_assessment_candidate_to_dict(x) for x in ordered]
    d: dict[str, Any] = {
        "assessment_framing": a.assessment_framing,
        "assessed_at": a.assessed_at,
        "candidates": cands,
        "notes": a.notes,
        "project_id": a.project_id,
        "schema_version": a.schema_version,
        "subject_document_id": a.subject_document_id,
    }
    return dict(sorted(d.items()))


def document_corpus_assessment_from_dict(data: dict[str, Any]) -> DocumentCorpusAssessment:
    raw_c = data.get("candidates") or []
    cands = tuple(corpus_assessment_candidate_from_dict(x) for x in raw_c)
    return DocumentCorpusAssessment(
        project_id=data["project_id"],
        subject_document_id=data["subject_document_id"],
        schema_version=data.get("schema_version", "g2.1"),
        assessed_at=data["assessed_at"],
        assessment_framing=data.get("assessment_framing", "candidate_assessment_not_governance_decision"),
        candidates=cands,
        notes=data.get("notes", "") or "",
    )


def truth_proposal_projection_delta_to_dict(d: TruthProposalProjectionDelta) -> dict[str, Any]:
    out: dict[str, Any] = {
        "add_authoritative_document_ids": sorted(d.add_authoritative_document_ids),
        "add_excluded_document_ids": sorted(d.add_excluded_document_ids),
        "add_supporting_document_ids": sorted(d.add_supporting_document_ids),
        "remove_authoritative_document_ids": sorted(d.remove_authoritative_document_ids),
        "remove_excluded_document_ids": sorted(d.remove_excluded_document_ids),
        "remove_supporting_document_ids": sorted(d.remove_supporting_document_ids),
    }
    return dict(sorted(out.items()))


def truth_proposal_projection_delta_from_dict(data: dict[str, Any]) -> TruthProposalProjectionDelta:
    return TruthProposalProjectionDelta(
        add_authoritative_document_ids=tuple(sorted(data.get("add_authoritative_document_ids", []))),
        remove_authoritative_document_ids=tuple(sorted(data.get("remove_authoritative_document_ids", []))),
        add_supporting_document_ids=tuple(sorted(data.get("add_supporting_document_ids", []))),
        remove_supporting_document_ids=tuple(sorted(data.get("remove_supporting_document_ids", []))),
        add_excluded_document_ids=tuple(sorted(data.get("add_excluded_document_ids", []))),
        remove_excluded_document_ids=tuple(sorted(data.get("remove_excluded_document_ids", []))),
    )


def truth_proposal_disposition_change_to_dict(c: TruthProposalDispositionChange) -> dict[str, Any]:
    d: dict[str, Any] = {
        "document_id": c.document_id,
        "from_disposition": c.from_disposition,
        "rationale_rule_id": c.rationale_rule_id,
        "to_disposition": c.to_disposition,
    }
    return dict(sorted(d.items()))


def truth_proposal_disposition_change_from_dict(data: dict[str, Any]) -> TruthProposalDispositionChange:
    return TruthProposalDispositionChange(
        document_id=data["document_id"],
        from_disposition=data["from_disposition"],
        to_disposition=data["to_disposition"],
        rationale_rule_id=data["rationale_rule_id"],
    )


def truth_proposal_decision_to_dict(d: TruthProposalDecision) -> dict[str, Any]:
    out: dict[str, Any] = {
        "actor": d.actor,
        "decided_at": d.decided_at,
        "notes": d.notes,
        "outcome": d.outcome,
    }
    return dict(sorted(out.items()))


def truth_proposal_decision_from_dict(data: dict[str, Any]) -> TruthProposalDecision:
    return TruthProposalDecision(
        outcome=data["outcome"],
        decided_at=data["decided_at"],
        actor=data.get("actor", "system") or "system",
        notes=data.get("notes", "") or "",
    )


def truth_proposal_to_dict(p: TruthProposal) -> dict[str, Any]:
    dchanges = sorted(
        p.disposition_changes,
        key=lambda x: (x.document_id, x.rationale_rule_id, x.from_disposition, x.to_disposition),
    )
    disp = [truth_proposal_disposition_change_to_dict(x) for x in dchanges]
    d: dict[str, Any] = {
        "created_at": p.created_at,
        "decision": truth_proposal_decision_to_dict(p.decision) if p.decision is not None else None,
        "disposition_changes": disp,
        "narrative": p.narrative,
        "project_id": p.project_id,
        "projection_delta": truth_proposal_projection_delta_to_dict(p.projection_delta),
        "proposal_id": p.proposal_id,
        "rules_applied": sorted(p.rules_applied),
        "schema_version": p.schema_version,
        "source_assessment_schema_version": p.source_assessment_schema_version,
        "status": p.status.value,
        "subject_document_id": p.subject_document_id,
    }
    return dict(sorted(d.items()))


def truth_proposal_from_dict(data: dict[str, Any]) -> TruthProposal:
    raw_dc = data.get("disposition_changes") or []
    dcs = tuple(truth_proposal_disposition_change_from_dict(x) for x in raw_dc)
    dec = None
    if data.get("decision") is not None:
        dec = truth_proposal_decision_from_dict(data["decision"])
    pd = truth_proposal_projection_delta_from_dict(data.get("projection_delta") or {})
    rules = data.get("rules_applied") or []
    rt = tuple(sorted(str(x) for x in rules))
    return TruthProposal(
        proposal_id=data["proposal_id"],
        project_id=data["project_id"],
        subject_document_id=data["subject_document_id"],
        schema_version=data.get("schema_version", "g3.1"),
        created_at=data["created_at"],
        status=TruthProposalStatus(str(data["status"])),
        source_assessment_schema_version=data.get("source_assessment_schema_version", "g2.1"),
        rules_applied=rt,
        projection_delta=pd,
        disposition_changes=dcs,
        narrative=data.get("narrative", "") or "",
        decision=dec,
    )


__all__ = [
    "active_knowledge_projection_from_dict",
    "active_knowledge_projection_to_dict",
    "truth_proposal_from_dict",
    "truth_proposal_to_dict",
    "truth_proposal_projection_delta_from_dict",
    "truth_proposal_projection_delta_to_dict",
    "corpus_assessment_candidate_from_dict",
    "corpus_assessment_candidate_to_dict",
    "document_analysis_snapshot_from_dict",
    "document_analysis_snapshot_to_dict",
    "document_classification_snapshot_from_dict",
    "document_classification_snapshot_to_dict",
    "document_corpus_assessment_from_dict",
    "document_corpus_assessment_to_dict",
    "document_governance_index_from_dict",
    "document_governance_index_to_dict",
    "document_governance_record_from_dict",
    "document_governance_record_to_dict",
    "governance_event_from_dict",
    "governance_event_log_from_dict",
    "governance_event_log_to_dict",
    "governance_event_to_dict",
]
