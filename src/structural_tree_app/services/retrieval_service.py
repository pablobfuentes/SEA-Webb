from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from structural_tree_app.domain.enums import DocumentApprovalStatus, NormativeClassification
from structural_tree_app.domain.models import Document, Project
from structural_tree_app.services.document_service import DocumentIngestionService
from structural_tree_app.services.project_service import ProjectService

CitationAuthority = Literal["normative_active_primary", "approved_ingested"]


@dataclass(frozen=True)
class CitationPayload:
    """Structured citation for UI, reports, and traceability (no LLM layer)."""

    document_title: str
    document_id: str
    fragment_id: str
    chunk_index: int
    content_hash: str
    """SHA-256 of raw file bytes (reproducible material identity)."""
    fragment_content_hash: str
    ingestion_method: str
    page_start: int | None
    page_end: int | None
    snippet: str
    document_approval_status: str
    normative_classification: str
    standard_family: str | None
    score: float


@dataclass(frozen=True)
class RetrievalResponse:
    status: Literal["ok", "insufficient_evidence"]
    query: str
    citation_authority: CitationAuthority
    hits: list[CitationPayload]
    message: str


def _lexical_score(query: str, text: str) -> float:
    qtok = [t for t in query.lower().split() if t]
    if not qtok:
        return 0.0
    tlow = text.lower()
    hits = sum(1 for t in qtok if t in tlow)
    return hits / len(qtok)


class DocumentRetrievalService:
    """
    Local lexical retrieval over project documents with explicit citation payloads.
    Does not fabricate answers: returns structured insufficient-evidence when the
    filtered corpus yields no support.
    """

    def __init__(self, project_service: ProjectService, project_id: str) -> None:
        self.ps = project_service
        self.project_id = project_id
        self.ingestion = DocumentIngestionService(project_service, project_id)

    def search(
        self,
        query: str,
        *,
        citation_authority: CitationAuthority = "normative_active_primary",
        match_project_primary_standard_family: bool = True,
        language: str | None = None,
        document_ids: set[str] | None = None,
        topic: str | None = None,
        limit: int = 20,
    ) -> RetrievalResponse:
        """
        Lexical search with filters.

        ``normative_active_primary`` (default): only documents that are approved,
        listed in ``active_code_context.allowed_document_ids``, classified as
        ``primary_standard``, and (when ``match_project_primary_standard_family``)
        whose ``standard_family`` equals the project's primary standard family.
        This excludes unknown/supporting/reference classifications from normative use.

        ``approved_ingested``: any ingested document that is approved (preview /
        audit use; not for normative design authority).
        """
        project = self.ps.load_project(self.project_id)
        scored: list[tuple[float, CitationPayload]] = []

        for doc_id in project.ingested_document_ids:
            doc = self.ingestion.load_document(doc_id)
            if not self._passes_authority_gate(project, doc, citation_authority):
                continue
            if document_ids is not None and doc.id not in document_ids:
                continue
            if language is not None and doc.language != language:
                continue
            if match_project_primary_standard_family and citation_authority == "normative_active_primary":
                if doc.standard_family != project.active_code_context.primary_standard_family:
                    continue
            if topic is not None:
                if topic not in doc.topics:
                    continue

            frags = self.ingestion.load_fragments(doc_id)
            for frag in frags:
                sc = _lexical_score(query, frag.text)
                if sc <= 0:
                    continue
                excerpt = frag.text if len(frag.text) <= 500 else frag.text[:497] + "..."
                cp = CitationPayload(
                    document_title=doc.title,
                    document_id=doc.id,
                    fragment_id=frag.id,
                    chunk_index=frag.chunk_index,
                    content_hash=doc.content_hash,
                    fragment_content_hash=frag.fragment_content_hash,
                    ingestion_method=frag.ingestion_method,
                    page_start=frag.page_start,
                    page_end=frag.page_end,
                    snippet=excerpt,
                    document_approval_status=doc.approval_status.value,
                    normative_classification=doc.normative_classification.value,
                    standard_family=doc.standard_family,
                    score=sc,
                )
                scored.append((sc, cp))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = [p for _, p in scored[:limit]]
        if not top:
            return RetrievalResponse(
                status="insufficient_evidence",
                query=query,
                citation_authority=citation_authority,
                hits=[],
                message=self._refusal_message(citation_authority, query),
            )
        return RetrievalResponse(
            status="ok",
            query=query,
            citation_authority=citation_authority,
            hits=top,
            message="",
        )

    @staticmethod
    def _refusal_message(mode: CitationAuthority, query: str) -> str:
        if mode == "normative_active_primary":
            return (
                "No passages found in the normative active corpus (approved, active for project, "
                f"primary_standard, matching primary standard family) for query: {query!r}."
            )
        return f"No passages found among approved ingested documents for query: {query!r}."

    @staticmethod
    def _passes_authority_gate(project: Project, doc: Document, mode: CitationAuthority) -> bool:
        if mode == "approved_ingested":
            return doc.approval_status == DocumentApprovalStatus.APPROVED

        if doc.approval_status != DocumentApprovalStatus.APPROVED:
            return False
        if doc.id not in project.active_code_context.allowed_document_ids:
            return False
        if doc.normative_classification != NormativeClassification.PRIMARY_STANDARD:
            return False
        return True


__all__ = [
    "CitationPayload",
    "DocumentRetrievalService",
    "RetrievalResponse",
]
