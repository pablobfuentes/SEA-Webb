"""
R1 — Structured contract for local AI orchestration (chat-first foundation).

No LLM: request/response payloads only. Future conversational layer consumes
``LocalAssistResponse`` without bypassing retrieval authority.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

# --- Request -----------------------------------------------------------------

# Align with ``DocumentRetrievalService.search`` ``citation_authority`` (domain-owned alias).
LocalAssistCitationMode = Literal["normative_active_primary", "approved_ingested"]

# Mirrors ``RetrievalResponse.normative_retrieval_source`` (G4); exposed for UI provenance.
NormativeRetrievalBindingDisplay = Literal["n_a", "legacy_allowed_documents", "explicit_projection"]


@dataclass(frozen=True)
class LocalAssistQuery:
    """
    User question routed through approved-corpus retrieval only.

    ``retrieval_query_text`` is passed verbatim to ``DocumentRetrievalService.search``
    (lexical match over ingested fragments that pass the authority gate).
    """

    project_id: str
    retrieval_query_text: str
    citation_authority: LocalAssistCitationMode = "normative_active_primary"
    retrieval_limit: int = 20
    match_project_primary_standard_family: bool = True
    language: str | None = None
    topic: str | None = None
    document_ids: frozenset[str] | None = None
    include_project_assumptions: bool = True
    include_deterministic_hooks: bool = False
    """When True, lists preliminary / deterministic Calculation records from live tree (read-only pointers)."""


# --- Response: authority & status --------------------------------------------

LocalAssistAnswerStatus = Literal[
    "evidence_passages_assembled",
    "insufficient_evidence",
    "unsupported_query",
    "error",
]

"""How a citation row should be interpreted (never merged into a single 'truth')."""
CitationAuthorityClass = Literal[
    "authoritative_normative_active_primary",
    "approved_supporting_corpus",
]

ResponseAuthoritySummary = Literal[
    "retrieval_passages_only_not_synthesized",
    "no_passages_retrieval_refusal",
    "query_invalid",
    "system_error",
]

RefusalCode = Literal[
    "INSUFFICIENT_CORPUS_EVIDENCE",
    "EMPTY_QUERY",
    "QUERY_TOO_LONG",
    "PROJECT_NOT_FOUND",
    "PROJECT_INVALID",
    "GOVERNANCE_CONFLICT_BLOCKS_NORMATIVE",
    "GOVERNANCE_EXPLICIT_PROJECTION_UNAVAILABLE",
]


@dataclass(frozen=True)
class RefusalItem:
    code: RefusalCode
    message: str


@dataclass(frozen=True)
class OrchestrationCitation:
    """Exact citation row for UI / serialization (from retrieval, plus explicit class)."""

    citation_id: str
    document_id: str
    fragment_id: str
    chunk_index: int
    document_title: str
    snippet: str
    score: float
    content_hash: str
    fragment_content_hash: str
    page_start: int | None
    page_end: int | None
    ingestion_method: str
    document_approval_status: str
    normative_classification: str
    standard_family: str | None
    authority_class: CitationAuthorityClass
    retrieval_citation_authority: LocalAssistCitationMode


@dataclass(frozen=True)
class EvidenceItem:
    """One retrieved passage slot (evidence-backed; not a merged recommendation)."""

    evidence_id: str
    citation_id: str


@dataclass(frozen=True)
class AssumptionItem:
    """Project assumption log (not retrieval authority)."""

    assumption_id: str
    label: str
    value: str
    unit: str | None
    source_type: str
    rationale: str
    authority_note: str = "project_assumption_log_not_normative_citation"


DeterministicHookAuthority = Literal[
    "preliminary_deterministic_m5",
    "deterministic_computation_other",
]


@dataclass(frozen=True)
class DeterministicHookItem:
    """
    Pointer to a persisted Calculation (deterministic engine), never promoted to citation authority.
    """

    hook_id: str
    calculation_id: str
    node_id: str
    method_label: str
    authority_boundary: DeterministicHookAuthority
    disclosure: str = (
        "Deterministic engine output only; not a normative document citation; separate from retrieval evidence."
    )


@dataclass(frozen=True)
class LocalAssistResponse:
    """Bounded assembly for R1; answer text is honest about lack of LLM synthesis."""

    answer_status: LocalAssistAnswerStatus
    answer_text: str
    answer_status_detail: str
    response_authority_summary: ResponseAuthoritySummary
    retrieval_query_effective: str
    citation_authority_requested: LocalAssistCitationMode
    citations: tuple[OrchestrationCitation, ...]
    evidence_items: tuple[EvidenceItem, ...]
    assumptions: tuple[AssumptionItem, ...]
    deterministic_hooks: tuple[DeterministicHookItem, ...]
    warnings: tuple[str, ...]
    refusal_reasons: tuple[RefusalItem, ...]
    # G4: when citation_authority_requested is normative, which governed retrieval path applied.
    normative_retrieval_binding: NormativeRetrievalBindingDisplay = "n_a"


def citation_authority_class_for_mode(mode: LocalAssistCitationMode) -> CitationAuthorityClass:
    if mode == "normative_active_primary":
        return "authoritative_normative_active_primary"
    return "approved_supporting_corpus"


def local_assist_response_to_dict(resp: LocalAssistResponse) -> dict[str, Any]:
    """JSON-serializable dict with stable key ordering for contract tests."""

    def _citation(c: OrchestrationCitation) -> dict[str, Any]:
        return {
            "authority_class": c.authority_class,
            "chunk_index": c.chunk_index,
            "citation_id": c.citation_id,
            "content_hash": c.content_hash,
            "document_approval_status": c.document_approval_status,
            "document_id": c.document_id,
            "document_title": c.document_title,
            "fragment_content_hash": c.fragment_content_hash,
            "fragment_id": c.fragment_id,
            "ingestion_method": c.ingestion_method,
            "normative_classification": c.normative_classification,
            "page_end": c.page_end,
            "page_start": c.page_start,
            "retrieval_citation_authority": c.retrieval_citation_authority,
            "score": c.score,
            "snippet": c.snippet,
            "standard_family": c.standard_family,
        }

    def _refusal(r: RefusalItem) -> dict[str, str]:
        return {"code": r.code, "message": r.message}

    def _evidence(e: EvidenceItem) -> dict[str, str]:
        return {"citation_id": e.citation_id, "evidence_id": e.evidence_id}

    def _asm(a: AssumptionItem) -> dict[str, str]:
        return {
            "assumption_id": a.assumption_id,
            "authority_note": a.authority_note,
            "label": a.label,
            "rationale": a.rationale,
            "source_type": a.source_type,
            "unit": a.unit or "",
            "value": a.value,
        }

    def _hook(h: DeterministicHookItem) -> dict[str, str]:
        return {
            "authority_boundary": h.authority_boundary,
            "calculation_id": h.calculation_id,
            "disclosure": h.disclosure,
            "hook_id": h.hook_id,
            "method_label": h.method_label,
            "node_id": h.node_id,
        }

    return {
        "answer_status": resp.answer_status,
        "answer_status_detail": resp.answer_status_detail,
        "answer_text": resp.answer_text,
        "assumptions": [_asm(a) for a in resp.assumptions],
        "citation_authority_requested": resp.citation_authority_requested,
        "citations": [_citation(c) for c in resp.citations],
        "deterministic_hooks": [_hook(h) for h in resp.deterministic_hooks],
        "evidence_items": [_evidence(e) for e in resp.evidence_items],
        "normative_retrieval_binding": resp.normative_retrieval_binding,
        "refusal_reasons": [_refusal(r) for r in resp.refusal_reasons],
        "response_authority_summary": resp.response_authority_summary,
        "retrieval_query_effective": resp.retrieval_query_effective,
        "warnings": list(resp.warnings),
    }


__all__ = [
    "AssumptionItem",
    "CitationAuthorityClass",
    "DeterministicHookAuthority",
    "DeterministicHookItem",
    "EvidenceItem",
    "LocalAssistAnswerStatus",
    "LocalAssistCitationMode",
    "LocalAssistQuery",
    "LocalAssistResponse",
    "NormativeRetrievalBindingDisplay",
    "OrchestrationCitation",
    "RefusalCode",
    "RefusalItem",
    "ResponseAuthoritySummary",
    "citation_authority_class_for_mode",
    "local_assist_response_to_dict",
]
