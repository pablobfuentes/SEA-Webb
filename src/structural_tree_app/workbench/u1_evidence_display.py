"""U1 — view helpers for local-assist evidence panel (labels only; no retrieval logic)."""

from __future__ import annotations

from structural_tree_app.domain.local_assist_contract import LocalAssistResponse, RefusalItem
from structural_tree_app.services.corpus_readiness import readiness_hint_html_for_evidence


def u1_retrieval_provenance_headline(resp: LocalAssistResponse) -> str:
    """Human-readable headline for governed retrieval path (G4 + citation mode)."""
    if resp.citation_authority_requested == "approved_ingested":
        return (
            "Retrieval mode: approved ingested corpus — supporting / audit path "
            "(not normative-authoritative primary standard gate)."
        )
    if resp.citation_authority_requested == "normative_active_primary":
        if resp.normative_retrieval_binding == "explicit_projection":
            return (
                "Normative retrieval: explicit active knowledge projection "
                "(governed authoritative document set; not legacy allowed-document list)."
            )
        if resp.normative_retrieval_binding == "legacy_allowed_documents":
            return (
                "Normative retrieval: legacy allowed-document gate "
                "(active code context allowed_document_ids)."
            )
        return "Normative retrieval: binding not applicable (n_a) for this response."
    return "Retrieval provenance: unknown configuration."


def u1_citation_row_badge(resp: LocalAssistResponse, authority_class: str) -> str:
    """Short badge text per citation row (orchestration authority_class + mode)."""
    if authority_class == "approved_supporting_corpus":
        return "Supporting / approved ingested"
    if authority_class == "authoritative_normative_active_primary":
        if resp.normative_retrieval_binding == "explicit_projection":
            return "Authoritative normative (explicit projection)"
        if resp.normative_retrieval_binding == "legacy_allowed_documents":
            return "Authoritative normative (legacy allowed docs)"
        return "Authoritative normative (primary)"
    return authority_class


def u1_refusal_is_governance_block(r: RefusalItem) -> bool:
    return r.code.startswith("GOVERNANCE_")


def u1_readiness_hint_html(assist: LocalAssistResponse | None, project_id: str) -> str:
    """HTML snippet when normative retrieval fails or is governance-blocked (corpus readiness bridge)."""
    if assist is None:
        return ""
    return readiness_hint_html_for_evidence(
        answer_status=assist.answer_status,
        citation_authority_requested=assist.citation_authority_requested,
        refusal_codes=tuple(r.code for r in assist.refusal_reasons),
        project_id=project_id,
    )


def u1_response_authority_summary_label(summary: str) -> str:
    mapping = {
        "retrieval_passages_only_not_synthesized": "Retrieval-only passages (no LLM synthesis)",
        "no_passages_retrieval_refusal": "No passages under authority gate / refusal",
        "query_invalid": "Query invalid",
        "system_error": "System / project error",
    }
    return mapping.get(summary, summary)

