"""
R1 — Local assist orchestrator: retrieval-only assembly, no LLM, no direct corpus reads.

Uses ``DocumentRetrievalService`` as the sole path to document text. Optional read-only
tree pointers for deterministic Calculation records (clearly labeled, never as citations).
"""

from __future__ import annotations

from structural_tree_app.domain.local_assist_contract import (
    AssumptionItem,
    CitationAuthorityClass,
    DeterministicHookItem,
    EvidenceItem,
    LocalAssistQuery,
    LocalAssistResponse,
    OrchestrationCitation,
    RefusalItem,
    citation_authority_class_for_mode,
)
from structural_tree_app.services.project_service import ProjectPersistenceError, ProjectService
from structural_tree_app.services.retrieval_service import CitationPayload, DocumentRetrievalService, RetrievalResponse
from structural_tree_app.services.simple_span_m5_service import METHOD_LABEL as M5_METHOD_LABEL
from structural_tree_app.storage.tree_store import TreeStore

_MAX_QUERY_LEN = 8000

_R1_DISCLOSURE = (
    "[R1 bounded assembly] Passages below come only from approved-corpus retrieval. "
    "This response does not synthesize a design conclusion or merge sources into a single recommendation. "
    "A future conversational layer may restate content under the same authority boundaries."
)


class LocalAssistOrchestrator:
    """Thin orchestration over ``DocumentRetrievalService`` + optional project/tree reads."""

    def __init__(self, project_service: ProjectService) -> None:
        self._ps = project_service

    def run(self, query: LocalAssistQuery) -> LocalAssistResponse:
        text = query.retrieval_query_text.strip()
        if not text:
            return self._unsupported_empty()
        if len(text) > _MAX_QUERY_LEN:
            return self._unsupported_too_long(len(text))

        try:
            self._ps.load_project(query.project_id)
        except ProjectPersistenceError as e:
            msg = str(e)
            if "Missing project" in msg or "project file" in msg.lower():
                return self._project_missing(msg)
            return self._project_error(msg)

        rsvc = DocumentRetrievalService(self._ps, query.project_id)
        rr = rsvc.search(
            text,
            citation_authority=query.citation_authority,
            limit=query.retrieval_limit,
            match_project_primary_standard_family=query.match_project_primary_standard_family,
            language=query.language,
            topic=query.topic,
            document_ids=set(query.document_ids) if query.document_ids is not None else None,
        )

        assumptions: tuple[AssumptionItem, ...] = ()
        if query.include_project_assumptions:
            assumptions = self._load_assumptions(query.project_id)

        hooks: tuple[DeterministicHookItem, ...] = ()
        if query.include_deterministic_hooks:
            hooks = self._load_deterministic_hooks(query.project_id)

        warnings: list[str] = []
        if hooks:
            warnings.append(
                "Deterministic hooks list engine outputs (e.g. preliminary M5); they are not normative document citations."
            )
        warnings.extend(rr.governance_warnings)

        if rr.status == "insufficient_evidence":
            return LocalAssistResponse(
                answer_status="insufficient_evidence",
                answer_text=f"{_R1_DISCLOSURE}\n\n{rr.message}",
                answer_status_detail="retrieval_returned_no_hits_under_authority_gate",
                response_authority_summary="no_passages_retrieval_refusal",
                retrieval_query_effective=text,
                citation_authority_requested=query.citation_authority,
                normative_retrieval_binding=rr.normative_retrieval_source,
                citations=(),
                evidence_items=(),
                assumptions=assumptions,
                deterministic_hooks=hooks,
                warnings=tuple(warnings),
                refusal_reasons=(_refusal_for_retrieval(rr),),
            )

        auth_class = citation_authority_class_for_mode(query.citation_authority)
        citations: list[OrchestrationCitation] = []
        evidence_items: list[EvidenceItem] = []
        for i, hit in enumerate(rr.hits):
            cid = f"cite-{i:04d}"
            citations.append(_payload_to_citation(hit, cid, auth_class, query.citation_authority))
            evidence_items.append(EvidenceItem(evidence_id=f"ev-{i:04d}", citation_id=cid))

        body = (
            f"{_R1_DISCLOSURE}\n\n"
            f"Retrieved {len(rr.hits)} passage(s) from the corpus under mode "
            f"{query.citation_authority!r}. Review each citation row; no merged conclusion is implied."
        )

        return LocalAssistResponse(
            answer_status="evidence_passages_assembled",
            answer_text=body,
            answer_status_detail="retrieval_ok_lexical_hits",
            response_authority_summary="retrieval_passages_only_not_synthesized",
            retrieval_query_effective=text,
            citation_authority_requested=query.citation_authority,
            normative_retrieval_binding=rr.normative_retrieval_source,
            citations=tuple(citations),
            evidence_items=tuple(evidence_items),
            assumptions=assumptions,
            deterministic_hooks=hooks,
            warnings=tuple(warnings),
            refusal_reasons=(),
        )

    def _load_assumptions(self, project_id: str) -> tuple[AssumptionItem, ...]:
        try:
            raw = self._ps.load_assumptions(project_id)
        except ProjectPersistenceError:
            return ()
        out: list[AssumptionItem] = []
        for a in raw:
            st = a.source_type.value if hasattr(a.source_type, "value") else str(a.source_type)
            out.append(
                AssumptionItem(
                    assumption_id=a.id,
                    label=a.label,
                    value=str(a.value),
                    unit=a.unit,
                    source_type=st,
                    rationale=a.rationale or "",
                )
            )
        return tuple(out)

    def _load_deterministic_hooks(self, project_id: str) -> tuple[DeterministicHookItem, ...]:
        store = TreeStore.for_live_project(self._ps.repository, project_id)
        out: list[DeterministicHookItem] = []
        for i, cid in enumerate(store.list_calculation_ids()):
            c = store.load_calculation(cid)
            boundary = (
                "preliminary_deterministic_m5" if c.method_label == M5_METHOD_LABEL else "deterministic_computation_other"
            )
            out.append(
                DeterministicHookItem(
                    hook_id=f"hook-{i:04d}",
                    calculation_id=c.id,
                    node_id=c.node_id,
                    method_label=c.method_label,
                    authority_boundary=boundary,
                )
            )
        return tuple(out)

    @staticmethod
    def _unsupported_empty() -> LocalAssistResponse:
        msg = "Query text is empty after strip; nothing to retrieve."
        return LocalAssistResponse(
            answer_status="unsupported_query",
            answer_text=msg,
            answer_status_detail="empty_query",
            response_authority_summary="query_invalid",
            retrieval_query_effective="",
            citation_authority_requested="normative_active_primary",
            citations=(),
            evidence_items=(),
            assumptions=(),
            deterministic_hooks=(),
            warnings=(),
            refusal_reasons=(RefusalItem(code="EMPTY_QUERY", message=msg),),
        )

    @staticmethod
    def _unsupported_too_long(n: int) -> LocalAssistResponse:
        msg = f"Query exceeds maximum length ({_MAX_QUERY_LEN}); refused."
        return LocalAssistResponse(
            answer_status="unsupported_query",
            answer_text=msg,
            answer_status_detail="query_too_long",
            response_authority_summary="query_invalid",
            retrieval_query_effective="",
            citation_authority_requested="normative_active_primary",
            citations=(),
            evidence_items=(),
            assumptions=(),
            deterministic_hooks=(),
            warnings=(),
            refusal_reasons=(RefusalItem(code="QUERY_TOO_LONG", message=msg),),
        )

    @staticmethod
    def _project_missing(message: str) -> LocalAssistResponse:
        return LocalAssistResponse(
            answer_status="error",
            answer_text=message,
            answer_status_detail="project_not_found",
            response_authority_summary="system_error",
            retrieval_query_effective="",
            citation_authority_requested="normative_active_primary",
            citations=(),
            evidence_items=(),
            assumptions=(),
            deterministic_hooks=(),
            warnings=(),
            refusal_reasons=(RefusalItem(code="PROJECT_NOT_FOUND", message=message),),
        )

    @staticmethod
    def _project_error(message: str) -> LocalAssistResponse:
        return LocalAssistResponse(
            answer_status="error",
            answer_text=message,
            answer_status_detail="project_load_failed",
            response_authority_summary="system_error",
            retrieval_query_effective="",
            citation_authority_requested="normative_active_primary",
            citations=(),
            evidence_items=(),
            assumptions=(),
            deterministic_hooks=(),
            warnings=(),
            refusal_reasons=(RefusalItem(code="PROJECT_INVALID", message=message),),
        )


def _refusal_for_retrieval(rr: RetrievalResponse) -> RefusalItem:
    if rr.governance_normative_block == "conflict":
        return RefusalItem(code="GOVERNANCE_CONFLICT_BLOCKS_NORMATIVE", message=rr.message)
    if rr.governance_normative_block in ("missing_index", "empty_authoritative"):
        return RefusalItem(code="GOVERNANCE_EXPLICIT_PROJECTION_UNAVAILABLE", message=rr.message)
    return RefusalItem(code="INSUFFICIENT_CORPUS_EVIDENCE", message=rr.message)


def _payload_to_citation(
    hit: CitationPayload,
    citation_id: str,
    authority_class: CitationAuthorityClass,
    mode: str,
) -> OrchestrationCitation:
    return OrchestrationCitation(
        citation_id=citation_id,
        document_id=hit.document_id,
        fragment_id=hit.fragment_id,
        chunk_index=hit.chunk_index,
        document_title=hit.document_title,
        snippet=hit.snippet,
        score=hit.score,
        content_hash=hit.content_hash,
        fragment_content_hash=hit.fragment_content_hash,
        page_start=hit.page_start,
        page_end=hit.page_end,
        ingestion_method=hit.ingestion_method,
        document_approval_status=hit.document_approval_status,
        normative_classification=hit.normative_classification,
        standard_family=hit.standard_family,
        authority_class=authority_class,  # type: ignore[arg-type]
        retrieval_citation_authority=mode,  # type: ignore[arg-type]
    )


__all__ = ["LocalAssistOrchestrator", "_MAX_QUERY_LEN"]
