"""G1.5 / U0 — engineer-driven corpus bootstrap: manual disposition + projection updates with audit."""

from __future__ import annotations

from typing import Literal

from structural_tree_app.domain.governance_enums import (
    DocumentGovernanceDisposition,
    GovernanceEventType,
    GovernanceRetrievalBinding,
)
from structural_tree_app.domain.governance_models import (
    ActiveKnowledgeProjection,
    DocumentGovernanceIndex,
    DocumentGovernanceRecord,
    GovernanceEvent,
)
from structural_tree_app.domain.models import new_id, utc_now
from structural_tree_app.services.governance_store import GovernanceStore, GovernanceStoreError
from structural_tree_app.services.project_service import ProjectService

CorpusBootstrapRole = Literal["authoritative_active", "supporting", "pending_review"]


class CorpusBootstrapError(Exception):
    """Invalid bootstrap action or inconsistent governance state."""


def apply_manual_corpus_bootstrap(
    store: GovernanceStore,
    project_id: str,
    document_id: str,
    role: CorpusBootstrapRole,
    *,
    actor: str = "corpus_bootstrap",
    rationale: str = "",
) -> None:
    """
    Explicit engineer action: set disposition and align projection lists.

    Does **not** auto-approve legacy ``Document`` metadata or switch retrieval binding;
    use ``set_projection_retrieval_binding`` and optional legacy sync separately.

    - **authoritative_active**: disposition ACTIVE; add to authoritative list; remove from supporting/excluded.
    - **supporting**: disposition SUPPORTING; add to supporting; remove from authoritative/excluded.
    - **pending_review**: disposition PENDING_REVIEW; remove from authoritative and supporting (not auto-excluded).
    """
    store.initialize_governance_baseline(project_id)
    idx = store.try_load_document_governance_index(project_id)
    proj = store.try_load_active_knowledge_projection(project_id)
    if idx is None or proj is None:
        raise CorpusBootstrapError("Governance index or active projection missing after baseline init.")

    prev_rec = idx.by_document_id.get(document_id)
    if prev_rec is None:
        raise CorpusBootstrapError(
            f"No governance record for document_id={document_id}; ingest the document first."
        )

    prior_disp = prev_rec.disposition.value
    if role == "authoritative_active":
        new_disp = DocumentGovernanceDisposition.ACTIVE
    elif role == "supporting":
        new_disp = DocumentGovernanceDisposition.SUPPORTING
    else:
        new_disp = DocumentGovernanceDisposition.PENDING_REVIEW

    auth = set(proj.authoritative_document_ids)
    sup = set(proj.supporting_document_ids)
    exc = set(proj.excluded_from_authoritative_document_ids)

    if role == "authoritative_active":
        auth.add(document_id)
        sup.discard(document_id)
        exc.discard(document_id)
    elif role == "supporting":
        sup.add(document_id)
        auth.discard(document_id)
        exc.discard(document_id)
    else:
        auth.discard(document_id)
        sup.discard(document_id)

    now = utc_now()
    new_rec = DocumentGovernanceRecord(
        document_id=document_id,
        pipeline_stage=prev_rec.pipeline_stage,
        disposition=new_disp,
        updated_at=now,
        notes=prev_rec.notes,
        analysis=prev_rec.analysis,
        classification=prev_rec.classification,
    )
    new_by = dict(idx.by_document_id)
    new_by[document_id] = new_rec
    new_idx = DocumentGovernanceIndex(
        project_id=project_id,
        schema_version=idx.schema_version,
        updated_at=now,
        by_document_id=new_by,
    )

    tail = f"\n[manual corpus bootstrap {now} role={role}]"
    if rationale.strip():
        tail += f" {rationale.strip()}"

    new_proj = ActiveKnowledgeProjection(
        project_id=project_id,
        schema_version="g3.1",
        updated_at=now,
        retrieval_binding=proj.retrieval_binding,
        authoritative_document_ids=tuple(sorted(auth)),
        supporting_document_ids=tuple(sorted(sup)),
        excluded_from_authoritative_document_ids=tuple(sorted(exc)),
        notes=(proj.notes or "") + tail,
    )

    store.save_document_governance_index(new_idx)
    store.save_active_knowledge_projection(new_proj)

    ev_d = GovernanceEvent(
        project_id=project_id,
        event_type=GovernanceEventType.DISPOSITION_CHANGED,
        rationale=rationale or f"Manual corpus bootstrap: disposition set via role={role}.",
        occurred_at=now,
        id=new_id("gov"),
        actor=actor,
        affected_document_ids=(document_id,),
        prior_retrieval_binding=None,
        new_retrieval_binding=None,
        prior_projection_schema_version=proj.schema_version,
        payload={
            "governance_phase": "g1_5_bootstrap",
            "document_id": document_id,
            "prior_disposition": prior_disp,
            "new_disposition": new_disp.value,
            "bootstrap_role": role,
        },
    )
    ev_p = GovernanceEvent(
        project_id=project_id,
        event_type=GovernanceEventType.PROJECTION_UPDATED,
        rationale="Active knowledge projection lists updated from manual corpus bootstrap (explicit user action).",
        occurred_at=now,
        id=new_id("gov"),
        actor=actor,
        affected_document_ids=(document_id,),
        prior_retrieval_binding=proj.retrieval_binding.value,
        new_retrieval_binding=new_proj.retrieval_binding.value,
        prior_projection_schema_version=proj.schema_version,
        payload={
            "governance_phase": "g1_5_bootstrap",
            "bootstrap_role": role,
        },
    )
    store.append_governance_events(project_id, (ev_d, ev_p))


def set_projection_retrieval_binding(
    store: GovernanceStore,
    project_id: str,
    binding: GovernanceRetrievalBinding,
    *,
    actor: str = "corpus_bootstrap",
    rationale: str = "",
) -> ActiveKnowledgeProjection:
    """Set ``retrieval_binding`` on the active projection (e.g. switch to explicit_projection). Audited."""
    store.initialize_governance_baseline(project_id)
    proj = store.try_load_active_knowledge_projection(project_id)
    if proj is None:
        raise CorpusBootstrapError("Active knowledge projection missing.")

    if proj.retrieval_binding == binding:
        return proj

    now = utc_now()
    new_proj = ActiveKnowledgeProjection(
        project_id=project_id,
        schema_version="g3.1",
        updated_at=now,
        retrieval_binding=binding,
        authoritative_document_ids=proj.authoritative_document_ids,
        supporting_document_ids=proj.supporting_document_ids,
        excluded_from_authoritative_document_ids=proj.excluded_from_authoritative_document_ids,
        notes=(proj.notes or "") + f"\n[retrieval_binding -> {binding.value} {now}]",
    )
    store.save_active_knowledge_projection(new_proj)

    ev = GovernanceEvent(
        project_id=project_id,
        event_type=GovernanceEventType.PROJECTION_UPDATED,
        rationale=rationale or f"Retrieval binding set to {binding.value} (explicit corpus bootstrap action).",
        occurred_at=now,
        id=new_id("gov"),
        actor=actor,
        affected_document_ids=(),
        prior_retrieval_binding=proj.retrieval_binding.value,
        new_retrieval_binding=binding.value,
        prior_projection_schema_version=proj.schema_version,
        payload={"governance_phase": "g1_5_bootstrap", "change": "retrieval_binding_only"},
    )
    store.append_governance_events(project_id, (ev,))
    return new_proj


def sync_legacy_allowed_documents_from_authoritative(
    ps: ProjectService,
    project_id: str,
    *,
    actor: str = "corpus_bootstrap",
) -> None:
    """
    Copy **authoritative** ids from the active knowledge projection into
    ``Project.active_code_context.allowed_document_ids`` (sorted, de-duplicated).

    Explicit bridge for projects still using legacy normative paths; audited.
    """
    store = ps.governance_store()
    proj = store.try_load_active_knowledge_projection(project_id)
    if proj is None:
        raise CorpusBootstrapError("Active knowledge projection missing.")

    authoritative = sorted(
        set(proj.authoritative_document_ids) - set(proj.excluded_from_authoritative_document_ids)
    )
    project = ps.load_project(project_id)
    prior = list(project.active_code_context.allowed_document_ids)
    project.active_code_context.allowed_document_ids = authoritative
    ps.save_project(project)

    now = utc_now()
    ev = GovernanceEvent(
        project_id=project_id,
        event_type=GovernanceEventType.PROJECTION_UPDATED,
        rationale="Legacy active_code_context.allowed_document_ids synced from authoritative projection lists (explicit user action).",
        occurred_at=now,
        id=new_id("gov"),
        actor=actor,
        affected_document_ids=tuple(authoritative),
        prior_retrieval_binding=None,
        new_retrieval_binding=None,
        prior_projection_schema_version=proj.schema_version,
        payload={
            "governance_phase": "g1_5_bootstrap",
            "change": "sync_legacy_allowed_from_projection",
            "prior_allowed_count": len(prior),
            "new_allowed_count": len(authoritative),
        },
    )
    log = store.try_load_governance_event_log(project_id)
    if log is None:
        raise GovernanceStoreError("Governance event log missing.")
    store.append_governance_events(project_id, (ev,))


__all__ = [
    "CorpusBootstrapError",
    "CorpusBootstrapRole",
    "apply_manual_corpus_bootstrap",
    "set_projection_retrieval_binding",
    "sync_legacy_allowed_documents_from_authoritative",
]
