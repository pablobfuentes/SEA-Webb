"""Per-document corpus readiness for normative vs supporting retrieval (bridge milestone).

Aligns with ``DocumentRetrievalService.search`` authority gates and G4 projection blocks.
"""

from __future__ import annotations

from dataclasses import dataclass

from structural_tree_app.domain.enums import (
    DocumentApprovalStatus,
    NormativeClassification,
)
from structural_tree_app.domain.governance_enums import GovernanceRetrievalBinding
from structural_tree_app.domain.governance_models import (
    ActiveKnowledgeProjection,
    DocumentGovernanceIndex,
    DocumentGovernanceRecord,
)
from structural_tree_app.domain.models import Document, Project
from structural_tree_app.services.retrieval_service import (
    _authoritative_set_has_unresolved_conflict,
    _effective_authoritative_document_ids,
    _filter_authoritative_ids_against_index,
)

# Stable codes for templates, tests, and evidence UX
READY_FOR_NORMATIVE_RETRIEVAL = "ready_for_normative_retrieval"
READY_FOR_SUPPORTING_ONLY = "ready_for_supporting_retrieval_only"
BLOCKED_MISSING_APPROVAL = "blocked_missing_approval"
BLOCKED_MISSING_PRIMARY_CLASSIFICATION = "blocked_missing_primary_classification"
BLOCKED_MISSING_STANDARD_FAMILY = "blocked_missing_standard_family"
BLOCKED_STANDARD_FAMILY_MISMATCH = "blocked_standard_family_mismatch"
BLOCKED_NOT_IN_LEGACY_ALLOWED = "blocked_not_in_legacy_allowed"
BLOCKED_NOT_IN_AUTHORITATIVE_PROJECTION = "blocked_not_in_authoritative_projection"
BLOCKED_GOVERNANCE_INDEX_MISSING = "blocked_governance_index_missing"
BLOCKED_EMPTY_AUTHORITATIVE_PROJECTION = "blocked_empty_authoritative_projection"
BLOCKED_PROJECT_AUTHORITATIVE_CONFLICT = "blocked_project_authoritative_conflict"


@dataclass(frozen=True)
class CorpusReadinessReport:
    document_id: str
    readiness_label: str
    normative_eligible: bool
    supporting_eligible: bool
    approval_status: str
    approval_ok: bool
    governance_disposition: str | None
    normative_classification: str
    primary_classification_ok: bool
    standard_family: str | None
    project_primary_standard_family: str
    family_matches_when_gate_enabled: bool | None
    """When False, normative retrieval with “match primary family” would skip this document."""
    match_primary_family_assumed: bool
    retrieval_binding_mode: str
    in_legacy_allowed_ids: bool
    in_effective_authoritative_projection: bool
    in_governance_index: bool
    project_normative_block_code: str | None
    project_normative_block_detail: str | None
    block_codes: tuple[str, ...]
    explanations: tuple[str, ...]


def evaluate_document_readiness(
    *,
    document: Document,
    project: Project,
    governance_record: DocumentGovernanceRecord | None,
    projection: ActiveKnowledgeProjection | None,
    governance_index: DocumentGovernanceIndex | None,
    match_project_primary_standard_family: bool = True,
) -> CorpusReadinessReport:
    """Evaluate whether ``document`` can be used for normative vs supporting retrieval.

    ``match_project_primary_standard_family`` mirrors the evidence panel checkbox default (``True``).
    """
    did = document.id
    approval_ok = document.approval_status == DocumentApprovalStatus.APPROVED
    primary_ok = document.normative_classification == NormativeClassification.PRIMARY_STANDARD

    proj_fam = (project.active_code_context.primary_standard_family or "").strip()
    doc_fam = (document.standard_family or "").strip()
    has_family = bool(doc_fam)
    if match_project_primary_standard_family:
        family_ok_for_normative = has_family and doc_fam == proj_fam
        family_mismatch = has_family and doc_fam != proj_fam
    else:
        family_ok_for_normative = has_family
        family_mismatch = None

    disp = governance_record.disposition.value if governance_record else None
    in_index = governance_index is not None and did in governance_index.by_document_id

    binding = (
        projection.retrieval_binding.value
        if projection is not None
        else GovernanceRetrievalBinding.LEGACY_ALLOWED_DOCUMENTS.value
    )

    legacy_allowed = did in (project.active_code_context.allowed_document_ids or [])

    explicit_mode = (
        projection is not None
        and projection.retrieval_binding == GovernanceRetrievalBinding.EXPLICIT_PROJECTION
    )
    filtered_auth: frozenset[str] = frozenset()
    project_block_code: str | None = None
    project_block_detail: str | None = None

    if explicit_mode:
        if governance_index is None:
            project_block_code = BLOCKED_GOVERNANCE_INDEX_MISSING
            project_block_detail = (
                "Normative retrieval (explicit binding) requires a document governance index for this project."
            )
        else:
            assert projection is not None
            raw_auth = _effective_authoritative_document_ids(projection)
            filtered_auth, _ = _filter_authoritative_ids_against_index(raw_auth, governance_index)
            if not filtered_auth:
                project_block_code = BLOCKED_EMPTY_AUTHORITATIVE_PROJECTION
                project_block_detail = (
                    "No authoritative document ids resolve against the governance index; normative retrieval is blocked."
                )
            elif _authoritative_set_has_unresolved_conflict(governance_index, filtered_auth):
                project_block_code = BLOCKED_PROJECT_AUTHORITATIVE_CONFLICT
                project_block_detail = (
                    "At least one authoritative document has conflicting_unresolved disposition; normative retrieval is refused."
                )

    in_eff_projection = did in filtered_auth if explicit_mode and governance_index is not None else False

    membership_ok = False
    if explicit_mode:
        membership_ok = in_eff_projection and project_block_code is None
    else:
        membership_ok = legacy_allowed

    per_doc_normative_ok = (
        approval_ok
        and primary_ok
        and family_ok_for_normative
        and membership_ok
    )

    normative_eligible = project_block_code is None and per_doc_normative_ok

    supporting_eligible = approval_ok

    block_codes: list[str] = []
    explanations: list[str] = []

    if project_block_code:
        block_codes.append(project_block_code)
        if project_block_detail:
            explanations.append(project_block_detail)

    if not approval_ok:
        block_codes.append(BLOCKED_MISSING_APPROVAL)
        explanations.append("Document metadata: approval_status must be approved for any retrieval path.")

    if not primary_ok:
        block_codes.append(BLOCKED_MISSING_PRIMARY_CLASSIFICATION)
        explanations.append("Normative path requires normative_classification=primary_standard.")

    if not has_family:
        block_codes.append(BLOCKED_MISSING_STANDARD_FAMILY)
        explanations.append("Set standard_family on the document (required for lexical normative filtering).")
    elif match_project_primary_standard_family and family_mismatch:
        block_codes.append(BLOCKED_STANDARD_FAMILY_MISMATCH)
        explanations.append(
            f"With “match primary family” enabled, document.standard_family ({doc_fam!r}) must equal "
            f"project.active_code_context.primary_standard_family ({proj_fam!r})."
        )

    if project_block_code is None:
        if explicit_mode:
            if not in_eff_projection:
                block_codes.append(BLOCKED_NOT_IN_AUTHORITATIVE_PROJECTION)
                explanations.append(
                    "Explicit binding: document id must be in the effective authoritative set "
                    "(projection authoritative minus exclusions, present in governance index)."
                )
        else:
            if not legacy_allowed:
                block_codes.append(BLOCKED_NOT_IN_LEGACY_ALLOWED)
                explanations.append(
                    "Legacy binding: add this document to active_code_context.allowed_document_ids "
                    "(corpus bootstrap authoritative, sync, or activate_for_normative_corpus)."
                )

    block_codes = list(dict.fromkeys(block_codes))

    # Prefer explicit normative blockers over the generic “supporting only” label when approved.
    if normative_eligible:
        label = READY_FOR_NORMATIVE_RETRIEVAL
    elif project_block_code == BLOCKED_GOVERNANCE_INDEX_MISSING:
        label = BLOCKED_GOVERNANCE_INDEX_MISSING
    elif project_block_code == BLOCKED_EMPTY_AUTHORITATIVE_PROJECTION:
        label = BLOCKED_EMPTY_AUTHORITATIVE_PROJECTION
    elif project_block_code == BLOCKED_PROJECT_AUTHORITATIVE_CONFLICT:
        label = BLOCKED_PROJECT_AUTHORITATIVE_CONFLICT
    elif BLOCKED_MISSING_APPROVAL in block_codes:
        label = BLOCKED_MISSING_APPROVAL
    elif BLOCKED_MISSING_PRIMARY_CLASSIFICATION in block_codes:
        label = BLOCKED_MISSING_PRIMARY_CLASSIFICATION
    elif BLOCKED_MISSING_STANDARD_FAMILY in block_codes:
        label = BLOCKED_MISSING_STANDARD_FAMILY
    elif BLOCKED_STANDARD_FAMILY_MISMATCH in block_codes:
        label = BLOCKED_STANDARD_FAMILY_MISMATCH
    elif BLOCKED_NOT_IN_LEGACY_ALLOWED in block_codes:
        label = BLOCKED_NOT_IN_LEGACY_ALLOWED
    elif BLOCKED_NOT_IN_AUTHORITATIVE_PROJECTION in block_codes:
        label = BLOCKED_NOT_IN_AUTHORITATIVE_PROJECTION
    elif supporting_eligible:
        label = READY_FOR_SUPPORTING_ONLY
    else:
        label = "blocked_unknown"

    return CorpusReadinessReport(
        document_id=did,
        readiness_label=label,
        normative_eligible=normative_eligible,
        supporting_eligible=supporting_eligible,
        approval_status=document.approval_status.value,
        approval_ok=approval_ok,
        governance_disposition=disp,
        normative_classification=document.normative_classification.value,
        primary_classification_ok=primary_ok,
        standard_family=document.standard_family,
        project_primary_standard_family=project.active_code_context.primary_standard_family,
        family_matches_when_gate_enabled=family_ok_for_normative if match_project_primary_standard_family else None,
        match_primary_family_assumed=match_project_primary_standard_family,
        retrieval_binding_mode=binding,
        in_legacy_allowed_ids=legacy_allowed,
        in_effective_authoritative_projection=in_eff_projection,
        in_governance_index=in_index,
        project_normative_block_code=project_block_code,
        project_normative_block_detail=project_block_detail,
        block_codes=tuple(block_codes),
        explanations=tuple(explanations),
    )


def readiness_hint_html_for_evidence(
    *,
    answer_status: str,
    citation_authority_requested: str | None,
    refusal_codes: tuple[str, ...],
    project_id: str,
) -> str:
    """Compact HTML snippet for evidence panel when normative retrieval yields no usable passages."""
    if citation_authority_requested != "normative_active_primary":
        return ""
    corpus_url = "/workbench/project/corpus"
    parts: list[str] = []
    if any(c.startswith("GOVERNANCE_") for c in refusal_codes):
        parts.append(
            "<p class=\"readiness-hint\"><strong>Governance / projection</strong> blocked normative retrieval. "
            "Open <a href=\"{url}\">corpus</a> for project <code>{pid}</code> to repair index, authoritative set, or conflicts.</p>"
        )
    elif answer_status == "insufficient_evidence":
        parts.append(
            "<p class=\"readiness-hint\"><strong>No normative passages</strong> matched. "
            "If you expected hits, check <a href=\"{url}\">corpus readiness</a> "
            "(approval, primary_standard classification, standard family vs <code>active_code_context.primary_standard_family</code>, "
            "and legacy allow-list or explicit projection membership).</p>"
        )
    if not parts:
        return ""
    return "".join(p.format(url=corpus_url, pid=project_id) for p in parts)
