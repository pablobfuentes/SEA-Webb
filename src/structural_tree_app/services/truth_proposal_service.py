"""G3: deterministic truth proposals, explicit approval, projection + index mutation, audit events."""

from __future__ import annotations

from structural_tree_app.domain.governance_enums import (
    CorpusAssessmentCandidateRelation,
    DocumentGovernanceDisposition,
    GovernanceEventType,
    TruthProposalStatus,
)
from structural_tree_app.domain.governance_codec import truth_proposal_to_dict
from structural_tree_app.domain.governance_models import (
    ActiveKnowledgeProjection,
    DocumentCorpusAssessment,
    DocumentGovernanceIndex,
    DocumentGovernanceRecord,
    GovernanceEvent,
    TruthProposal,
    TruthProposalDecision,
    TruthProposalDispositionChange,
    TruthProposalProjectionDelta,
)
from structural_tree_app.domain.models import new_id, utc_now
from structural_tree_app.services.governance_store import GovernanceStore, GovernanceStoreError


def _disp_str(index: DocumentGovernanceIndex, document_id: str) -> str:
    rec = index.by_document_id.get(document_id)
    if rec is None:
        return DocumentGovernanceDisposition.PENDING_REVIEW.value
    return rec.disposition.value


def build_truth_proposal(
    store: GovernanceStore,
    project_id: str,
    subject_document_id: str,
) -> TruthProposal:
    """
    Deterministic proposal from G2 assessment + current governance index.

    Branch priority (first match wins): duplicate → supersession → contradiction → supporting → overlap → empty.
    """
    assessment = store.try_load_document_corpus_assessment(project_id, subject_document_id)
    if assessment is None:
        raise ValueError(f"No G2 corpus assessment for subject_document_id={subject_document_id}")
    index = store.try_load_document_governance_index(project_id)
    if index is None:
        raise GovernanceStoreError("Governance index missing.")

    rels = {c.relation for c in assessment.candidates}
    proposal_id = new_id("tpr")
    now = utc_now()

    if not assessment.candidates:
        return TruthProposal(
            proposal_id=proposal_id,
            project_id=project_id,
            subject_document_id=subject_document_id,
            created_at=now,
            status=TruthProposalStatus.PENDING_APPROVAL,
            source_assessment_schema_version=assessment.schema_version,
            rules_applied=tuple(sorted(("g3.no_g2_candidates",))),
            projection_delta=TruthProposalProjectionDelta(),
            disposition_changes=(),
            narrative="No G2 candidate relations for this subject; no automatic projection or disposition changes proposed.",
            decision=None,
        )

    if CorpusAssessmentCandidateRelation.DUPLICATE_CANDIDATE in rels:
        return _proposal_duplicate(proposal_id, project_id, subject_document_id, now, assessment)

    if CorpusAssessmentCandidateRelation.SUPERSESSION_CANDIDATE in rels:
        return _proposal_supersession(
            proposal_id, project_id, subject_document_id, now, assessment, index
        )

    if CorpusAssessmentCandidateRelation.CONTRADICTION_CANDIDATE in rels:
        return _proposal_contradiction(
            proposal_id, project_id, subject_document_id, now, assessment, index
        )

    if CorpusAssessmentCandidateRelation.SUPPORTING_CANDIDATE in rels:
        return _proposal_supporting(
            proposal_id, project_id, subject_document_id, now, assessment, index
        )

    if CorpusAssessmentCandidateRelation.OVERLAP_CANDIDATE in rels:
        return _proposal_overlap_only(proposal_id, project_id, subject_document_id, now, assessment)

    return TruthProposal(
        proposal_id=proposal_id,
        project_id=project_id,
        subject_document_id=subject_document_id,
        created_at=now,
        status=TruthProposalStatus.PENDING_APPROVAL,
        source_assessment_schema_version=assessment.schema_version,
        rules_applied=tuple(sorted(("g3.unhandled_candidate_mix",))),
        projection_delta=TruthProposalProjectionDelta(),
        disposition_changes=(),
        narrative="G2 candidates present but no G3 rule branch matched; manual review required.",
        decision=None,
    )


def _proposal_duplicate(
    proposal_id: str,
    project_id: str,
    subject_document_id: str,
    now: str,
    assessment: DocumentCorpusAssessment,
) -> TruthProposal:
    dups = [c for c in assessment.candidates if c.relation == CorpusAssessmentCandidateRelation.DUPLICATE_CANDIDATE]
    others = sorted({c.other_document_id for c in dups})
    delta = TruthProposalProjectionDelta(add_excluded_document_ids=(subject_document_id,))
    narrative = (
        "G2 duplicate_candidate: subject shares content_hash with another ingested document; "
        "propose excluding this copy from authoritative activation lists (advisory projection until G4)."
    )
    if others:
        narrative += f" Compared duplicate material against other document id(s): {', '.join(others)}."
    return TruthProposal(
        proposal_id=proposal_id,
        project_id=project_id,
        subject_document_id=subject_document_id,
        created_at=now,
        status=TruthProposalStatus.PENDING_APPROVAL,
        source_assessment_schema_version=assessment.schema_version,
        rules_applied=tuple(sorted(("g3.duplicate_exclude_copy_from_authoritative_lists",))),
        projection_delta=delta,
        disposition_changes=(),
        narrative=narrative,
        decision=None,
    )


def _proposal_supersession(
    proposal_id: str,
    project_id: str,
    subject_document_id: str,
    now: str,
    assessment: DocumentCorpusAssessment,
    index: DocumentGovernanceIndex,
) -> TruthProposal:
    supers = [
        c
        for c in assessment.candidates
        if c.relation == CorpusAssessmentCandidateRelation.SUPERSESSION_CANDIDATE
    ]
    supers.sort(key=lambda c: c.other_document_id)
    remove_auth: set[str] = set()
    for c in supers:
        remove_auth.add(c.other_document_id)
    remove_auth.discard(subject_document_id)
    delta = TruthProposalProjectionDelta(
        add_authoritative_document_ids=(subject_document_id,),
        remove_authoritative_document_ids=tuple(sorted(remove_auth)),
    )
    changes: list[TruthProposalDispositionChange] = []
    for oid in sorted(remove_auth):
        changes.append(
            TruthProposalDispositionChange(
                document_id=oid,
                from_disposition=_disp_str(index, oid),
                to_disposition=DocumentGovernanceDisposition.SUPERSEDED.value,
                rationale_rule_id="g3.supersession_prior_mark_superseded",
            )
        )
    changes.append(
        TruthProposalDispositionChange(
            document_id=subject_document_id,
            from_disposition=_disp_str(index, subject_document_id),
            to_disposition=DocumentGovernanceDisposition.ACTIVE.value,
            rationale_rule_id="g3.supersession_subject_mark_active",
        )
    )
    changes.sort(key=lambda x: (x.document_id, x.rationale_rule_id))
    return TruthProposal(
        proposal_id=proposal_id,
        project_id=project_id,
        subject_document_id=subject_document_id,
        created_at=now,
        status=TruthProposalStatus.PENDING_APPROVAL,
        source_assessment_schema_version=assessment.schema_version,
        rules_applied=tuple(sorted(("g3.supersession_replace_authoritative_primary",))),
        projection_delta=delta,
        disposition_changes=tuple(changes),
        narrative="G2 supersession_candidate: propose replacing prior primary in projection with subject; mark superseded documents accordingly.",
        decision=None,
    )


def _proposal_contradiction(
    proposal_id: str,
    project_id: str,
    subject_document_id: str,
    now: str,
    assessment: DocumentCorpusAssessment,
    index: DocumentGovernanceIndex,
) -> TruthProposal:
    cons = [
        c
        for c in assessment.candidates
        if c.relation == CorpusAssessmentCandidateRelation.CONTRADICTION_CANDIDATE
    ]
    cons.sort(key=lambda c: c.other_document_id)
    doc_ids: set[str] = {subject_document_id}
    for c in cons:
        doc_ids.add(c.other_document_id)
    changes: list[TruthProposalDispositionChange] = []
    for did in sorted(doc_ids):
        changes.append(
            TruthProposalDispositionChange(
                document_id=did,
                from_disposition=_disp_str(index, did),
                to_disposition=DocumentGovernanceDisposition.CONFLICTING_UNRESOLVED.value,
                rationale_rule_id="g3.contradiction_mark_unresolved",
            )
        )
    return TruthProposal(
        proposal_id=proposal_id,
        project_id=project_id,
        subject_document_id=subject_document_id,
        created_at=now,
        status=TruthProposalStatus.PENDING_APPROVAL,
        source_assessment_schema_version=assessment.schema_version,
        rules_applied=tuple(sorted(("g3.contradiction_no_authoritative_activation",))),
        projection_delta=TruthProposalProjectionDelta(),
        disposition_changes=tuple(changes),
        narrative="G2 contradiction_candidate: propose conflicting_unresolved disposition; do not activate subject as authoritative primary until resolved.",
        decision=None,
    )


def _proposal_supporting(
    proposal_id: str,
    project_id: str,
    subject_document_id: str,
    now: str,
    assessment: DocumentCorpusAssessment,
    index: DocumentGovernanceIndex,
) -> TruthProposal:
    delta = TruthProposalProjectionDelta(add_supporting_document_ids=(subject_document_id,))
    ch = TruthProposalDispositionChange(
        document_id=subject_document_id,
        from_disposition=_disp_str(index, subject_document_id),
        to_disposition=DocumentGovernanceDisposition.SUPPORTING.value,
        rationale_rule_id="g3.supporting_register_in_projection",
    )
    return TruthProposal(
        proposal_id=proposal_id,
        project_id=project_id,
        subject_document_id=subject_document_id,
        created_at=now,
        status=TruthProposalStatus.PENDING_APPROVAL,
        source_assessment_schema_version=assessment.schema_version,
        rules_applied=tuple(sorted(("g3.supporting_add_to_supporting_list",))),
        projection_delta=delta,
        disposition_changes=(ch,),
        narrative="G2 supporting_candidate: propose registering subject as supporting in the active knowledge projection.",
        decision=None,
    )


def _proposal_overlap_only(
    proposal_id: str,
    project_id: str,
    subject_document_id: str,
    now: str,
    assessment: DocumentCorpusAssessment,
) -> TruthProposal:
    return TruthProposal(
        proposal_id=proposal_id,
        project_id=project_id,
        subject_document_id=subject_document_id,
        created_at=now,
        status=TruthProposalStatus.PENDING_APPROVAL,
        source_assessment_schema_version=assessment.schema_version,
        rules_applied=tuple(sorted(("g3.overlap_manual_review_only",))),
        projection_delta=TruthProposalProjectionDelta(),
        disposition_changes=(),
        narrative="G2 overlap_candidate only: no automatic disposition or projection mutation; manual governance review required.",
        decision=None,
    )


def persist_new_truth_proposal(store: GovernanceStore, proposal: TruthProposal) -> None:
    """Persist proposal JSON and append ``truth_proposal_created`` to the governance event log."""
    if proposal.status != TruthProposalStatus.PENDING_APPROVAL:
        raise ValueError("persist_new_truth_proposal expects status=pending_approval")
    if proposal.decision is not None:
        raise ValueError("persist_new_truth_proposal expects decision=None")
    store.save_truth_proposal(proposal)
    payload = truth_proposal_to_dict(proposal)
    ev = GovernanceEvent(
        project_id=proposal.project_id,
        event_type=GovernanceEventType.TRUTH_PROPOSAL_CREATED,
        rationale="G3 truth proposal persisted (pending explicit approval).",
        occurred_at=utc_now(),
        id=new_id("gov"),
        actor="system",
        affected_document_ids=(proposal.subject_document_id,),
        prior_retrieval_binding=None,
        new_retrieval_binding=None,
        prior_projection_schema_version=None,
        payload=dict(
            sorted(
                {
                    "governance_phase": "g3",
                    "proposal_id": proposal.proposal_id,
                    "rules_applied": list(proposal.rules_applied),
                    "schema_version": payload["schema_version"],
                }.items()
            )
        ),
    )
    store.append_governance_events(proposal.project_id, (ev,))


def _apply_projection_delta(
    proj: ActiveKnowledgeProjection,
    delta: TruthProposalProjectionDelta,
    *,
    proposal_id: str,
) -> ActiveKnowledgeProjection:
    auth = set(proj.authoritative_document_ids)
    sup = set(proj.supporting_document_ids)
    exc = set(proj.excluded_from_authoritative_document_ids)
    auth |= set(delta.add_authoritative_document_ids)
    auth -= set(delta.remove_authoritative_document_ids)
    sup |= set(delta.add_supporting_document_ids)
    sup -= set(delta.remove_supporting_document_ids)
    exc |= set(delta.add_excluded_document_ids)
    exc -= set(delta.remove_excluded_document_ids)
    now = utc_now()
    tail = f"\n[g3 proposal {proposal_id} applied {now}]"
    return ActiveKnowledgeProjection(
        project_id=proj.project_id,
        schema_version="g3.1",
        updated_at=now,
        retrieval_binding=proj.retrieval_binding,
        authoritative_document_ids=tuple(sorted(auth)),
        supporting_document_ids=tuple(sorted(sup)),
        excluded_from_authoritative_document_ids=tuple(sorted(exc)),
        notes=(proj.notes or "") + tail,
    )


def _merge_index_dispositions(
    index: DocumentGovernanceIndex,
    changes: tuple[TruthProposalDispositionChange, ...],
    *,
    now: str,
) -> DocumentGovernanceIndex:
    new_by = dict(index.by_document_id)
    for ch in changes:
        prev = new_by.get(ch.document_id)
        if prev is None:
            raise GovernanceStoreError(f"Governance record missing for document_id={ch.document_id}")
        if prev.disposition.value != ch.from_disposition:
            raise ValueError(
                f"Stale proposal: document {ch.document_id} disposition is {prev.disposition.value!r}, "
                f"expected {ch.from_disposition!r}"
            )
        new_by[ch.document_id] = DocumentGovernanceRecord(
            document_id=prev.document_id,
            pipeline_stage=prev.pipeline_stage,
            disposition=DocumentGovernanceDisposition(ch.to_disposition),
            updated_at=now,
            notes=prev.notes,
            analysis=prev.analysis,
            classification=prev.classification,
        )
    return DocumentGovernanceIndex(
        project_id=index.project_id,
        schema_version=index.schema_version,
        updated_at=now,
        by_document_id=new_by,
    )


def approve_truth_proposal(
    store: GovernanceStore,
    project_id: str,
    proposal_id: str,
    *,
    actor: str = "system",
    notes: str = "",
) -> TruthProposal:
    """Apply an approved proposal to projection + index; append audit events. Retrieval wiring remains G4."""
    prop = store.try_load_truth_proposal(project_id, proposal_id)
    if prop is None:
        raise ValueError(f"Unknown truth proposal: {proposal_id}")
    if prop.status != TruthProposalStatus.PENDING_APPROVAL:
        raise ValueError(f"Proposal {proposal_id} is not pending approval (status={prop.status}).")

    idx = store.try_load_document_governance_index(project_id)
    proj = store.try_load_active_knowledge_projection(project_id)
    if idx is None or proj is None:
        raise GovernanceStoreError("Governance index or projection missing.")

    now = utc_now()
    new_idx = _merge_index_dispositions(idx, prop.disposition_changes, now=now)
    new_proj = _apply_projection_delta(proj, prop.projection_delta, proposal_id=proposal_id)

    decided = TruthProposalDecision(outcome="approved", decided_at=now, actor=actor, notes=notes)
    approved_prop = TruthProposal(
        proposal_id=prop.proposal_id,
        project_id=prop.project_id,
        subject_document_id=prop.subject_document_id,
        schema_version=prop.schema_version,
        created_at=prop.created_at,
        status=TruthProposalStatus.APPROVED,
        source_assessment_schema_version=prop.source_assessment_schema_version,
        rules_applied=prop.rules_applied,
        projection_delta=prop.projection_delta,
        disposition_changes=prop.disposition_changes,
        narrative=prop.narrative,
        decision=decided,
    )
    store.save_document_governance_index(new_idx)
    store.save_active_knowledge_projection(new_proj)
    store.save_truth_proposal(approved_prop)

    affected = tuple(sorted({prop.subject_document_id, *[c.document_id for c in prop.disposition_changes]}))
    ev_a = GovernanceEvent(
        project_id=project_id,
        event_type=GovernanceEventType.TRUTH_PROPOSAL_APPROVED,
        rationale=f"G3 truth proposal {proposal_id} approved; projection and disposition changes applied.",
        occurred_at=now,
        id=new_id("gov"),
        actor=actor,
        affected_document_ids=affected,
        prior_retrieval_binding=None,
        new_retrieval_binding=None,
        prior_projection_schema_version=proj.schema_version,
        payload=dict(
            sorted(
                {
                    "governance_phase": "g3",
                    "proposal_id": proposal_id,
                    "new_projection_schema_version": new_proj.schema_version,
                }.items()
            )
        ),
    )
    ev_p = GovernanceEvent(
        project_id=project_id,
        event_type=GovernanceEventType.PROJECTION_UPDATED,
        rationale=f"Active knowledge projection updated from approved truth proposal {proposal_id} (advisory until G4 retrieval).",
        occurred_at=now,
        id=new_id("gov"),
        actor=actor,
        affected_document_ids=affected,
        prior_retrieval_binding=proj.retrieval_binding.value,
        new_retrieval_binding=new_proj.retrieval_binding.value,
        prior_projection_schema_version=proj.schema_version,
        payload=dict(
            sorted(
                {
                    "governance_phase": "g3",
                    "proposal_id": proposal_id,
                }.items()
            )
        ),
    )
    store.append_governance_events(project_id, (ev_a, ev_p))
    return approved_prop


def reject_truth_proposal(
    store: GovernanceStore,
    project_id: str,
    proposal_id: str,
    *,
    actor: str = "system",
    notes: str = "",
) -> TruthProposal:
    prop = store.try_load_truth_proposal(project_id, proposal_id)
    if prop is None:
        raise ValueError(f"Unknown truth proposal: {proposal_id}")
    if prop.status != TruthProposalStatus.PENDING_APPROVAL:
        raise ValueError(f"Proposal {proposal_id} is not pending approval.")

    now = utc_now()
    decided = TruthProposalDecision(outcome="rejected", decided_at=now, actor=actor, notes=notes)
    rejected = TruthProposal(
        proposal_id=prop.proposal_id,
        project_id=prop.project_id,
        subject_document_id=prop.subject_document_id,
        schema_version=prop.schema_version,
        created_at=prop.created_at,
        status=TruthProposalStatus.REJECTED,
        source_assessment_schema_version=prop.source_assessment_schema_version,
        rules_applied=prop.rules_applied,
        projection_delta=prop.projection_delta,
        disposition_changes=prop.disposition_changes,
        narrative=prop.narrative,
        decision=decided,
    )
    store.save_truth_proposal(rejected)
    ev = GovernanceEvent(
        project_id=project_id,
        event_type=GovernanceEventType.TRUTH_PROPOSAL_REJECTED,
        rationale=f"G3 truth proposal {proposal_id} rejected; no projection or disposition changes applied.",
        occurred_at=now,
        id=new_id("gov"),
        actor=actor,
        affected_document_ids=(prop.subject_document_id,),
        prior_retrieval_binding=None,
        new_retrieval_binding=None,
        prior_projection_schema_version=None,
        payload=dict(sorted({"governance_phase": "g3", "proposal_id": proposal_id}.items())),
    )
    store.append_governance_events(project_id, (ev,))
    return rejected


__all__ = [
    "approve_truth_proposal",
    "build_truth_proposal",
    "persist_new_truth_proposal",
    "reject_truth_proposal",
]
