from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from structural_tree_app.domain.enums import DocumentApprovalStatus, NormativeClassification
from structural_tree_app.domain.governance_enums import DocumentGovernanceDisposition, GovernanceRetrievalBinding
from structural_tree_app.domain.governance_models import (
    ActiveKnowledgeProjection,
    DocumentGovernanceIndex,
)
from structural_tree_app.domain.models import Document, Project
from structural_tree_app.services.document_service import DocumentIngestionService
from structural_tree_app.services.project_service import ProjectService

CitationAuthority = Literal["normative_active_primary", "approved_ingested"]

NormativeRetrievalSource = Literal["n_a", "legacy_allowed_documents", "explicit_projection"]

GovernanceNormativeBlock = Literal["conflict", "missing_index", "empty_authoritative"]


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
    """When normative retrieval was refused or narrowed by governance (G4)."""
    normative_retrieval_source: NormativeRetrievalSource = "n_a"
    governance_warnings: tuple[str, ...] = ()
    governance_normative_block: GovernanceNormativeBlock | None = None


def _lexical_score(query: str, text: str) -> float:
    qtok = [t for t in query.lower().split() if t]
    if not qtok:
        return 0.0
    tlow = text.lower()
    hits = sum(1 for t in qtok if t in tlow)
    return hits / len(qtok)


def _effective_authoritative_document_ids(projection: ActiveKnowledgeProjection) -> frozenset[str]:
    s = set(projection.authoritative_document_ids)
    s -= set(projection.excluded_from_authoritative_document_ids)
    return frozenset(sorted(s))


def _filter_authoritative_ids_against_index(
    authoritative_ids: frozenset[str],
    index: DocumentGovernanceIndex,
) -> tuple[frozenset[str], tuple[str, ...]]:
    """Drop ids missing from the index; deterministic warnings."""
    kept: list[str] = []
    warnings: list[str] = []
    for did in sorted(authoritative_ids):
        if did not in index.by_document_id:
            warnings.append(
                f"authoritative_document_id {did} not present in governance index; excluded from normative retrieval."
            )
            continue
        kept.append(did)
    return frozenset(kept), tuple(warnings)


def _authoritative_set_has_unresolved_conflict(
    index: DocumentGovernanceIndex, authoritative_ids: frozenset[str]
) -> bool:
    for did in sorted(authoritative_ids):
        rec = index.by_document_id.get(did)
        if rec is None:
            continue
        if rec.disposition == DocumentGovernanceDisposition.CONFLICTING_UNRESOLVED:
            return True
    return False


class DocumentRetrievalService:
    """
    Local lexical retrieval over project documents with explicit citation payloads.
    Does not fabricate answers: returns structured insufficient-evidence when the
    filtered corpus yields no support.

    **G4:** When ``active_knowledge_projection.retrieval_binding`` is
    ``explicit_projection``, normative-active-primary search uses only
    ``authoritative_document_ids`` (minus exclusions), validated against the
    governance index; legacy ``allowed_document_ids`` is not used for that path.
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

        ``normative_active_primary`` (default): behavior depends on governance
        **retrieval binding** (see ``active_knowledge_projection.json``):

        - ``legacy_allowed_documents`` (default): approved, primary-standard documents in
          ``active_code_context.allowed_document_ids``, with optional primary-standard-family match.
        - ``explicit_projection``: approved, primary-standard documents whose ids appear in the
          projection's effective authoritative set only; **not** ``allowed_document_ids``.
          Unresolved conflicting governance on any authoritative row refuses normative retrieval.

        ``approved_ingested``: any ingested approved document (audit / preview); not governed
        by explicit authoritative projection lists.
        """
        project = self.ps.load_project(self.project_id)
        gs = self.ps.governance_store()
        gproj = gs.try_load_active_knowledge_projection(self.project_id)
        gindex = gs.try_load_document_governance_index(self.project_id)

        normative_source: NormativeRetrievalSource = "n_a"
        gov_warnings: list[str] = []
        explicit_authoritative_ids: frozenset[str] | None = None
        block: tuple[GovernanceNormativeBlock, str] | None = None

        use_explicit_normative = (
            citation_authority == "normative_active_primary"
            and gproj is not None
            and gproj.retrieval_binding == GovernanceRetrievalBinding.EXPLICIT_PROJECTION
        )

        if citation_authority == "normative_active_primary":
            if use_explicit_normative:
                normative_source = "explicit_projection"
                if gindex is None:
                    block = (
                        "missing_index",
                        "Normative retrieval is unavailable: explicit_projection binding requires a "
                        "document governance index for this project.",
                    )
                else:
                    raw_auth = _effective_authoritative_document_ids(gproj)
                    explicit_authoritative_ids, widx = _filter_authoritative_ids_against_index(
                        raw_auth, gindex
                    )
                    gov_warnings.extend(widx)
                    if not explicit_authoritative_ids:
                        block = (
                            "empty_authoritative",
                            "Normative retrieval is unavailable: explicit active knowledge projection has "
                            "no authoritative document ids that resolve against the governance index.",
                        )
                    elif _authoritative_set_has_unresolved_conflict(gindex, explicit_authoritative_ids):
                        block = (
                            "conflict",
                            "Normative retrieval refused: at least one authoritative document has "
                            "conflicting_unresolved governance disposition.",
                        )
                        gov_warnings.append("governance_conflict_blocks_normative")
            else:
                normative_source = "legacy_allowed_documents"

        if block is not None:
            kind, msg = block
            return RetrievalResponse(
                status="insufficient_evidence",
                query=query,
                citation_authority=citation_authority,
                hits=[],
                message=msg,
                normative_retrieval_source=normative_source,
                governance_warnings=tuple(gov_warnings),
                governance_normative_block=kind,
            )

        scored: list[tuple[float, CitationPayload]] = []

        for doc_id in project.ingested_document_ids:
            doc = self.ingestion.load_document(doc_id)
            if not self._passes_authority_gate(
                project,
                doc,
                citation_authority,
                explicit_authoritative_ids=explicit_authoritative_ids,
            ):
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

        success_warnings = list(gov_warnings)
        if normative_source == "explicit_projection" and citation_authority == "normative_active_primary":
            success_warnings.insert(
                0,
                "Normative retrieval used explicit active knowledge projection (governed authoritative set).",
            )

        if not top:
            return RetrievalResponse(
                status="insufficient_evidence",
                query=query,
                citation_authority=citation_authority,
                hits=[],
                message=self._refusal_message(citation_authority, query),
                normative_retrieval_source=normative_source,
                governance_warnings=tuple(success_warnings),
            )
        return RetrievalResponse(
            status="ok",
            query=query,
            citation_authority=citation_authority,
            hits=top,
            message="",
            normative_retrieval_source=normative_source,
            governance_warnings=tuple(success_warnings),
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
    def _passes_authority_gate(
        project: Project,
        doc: Document,
        mode: CitationAuthority,
        *,
        explicit_authoritative_ids: frozenset[str] | None,
    ) -> bool:
        if mode == "approved_ingested":
            return doc.approval_status == DocumentApprovalStatus.APPROVED

        if doc.approval_status != DocumentApprovalStatus.APPROVED:
            return False
        if doc.normative_classification != NormativeClassification.PRIMARY_STANDARD:
            return False

        if explicit_authoritative_ids is not None:
            return doc.id in explicit_authoritative_ids

        if doc.id not in project.active_code_context.allowed_document_ids:
            return False
        return True


__all__ = [
    "CitationPayload",
    "DocumentRetrievalService",
    "GovernanceNormativeBlock",
    "NormativeRetrievalSource",
    "RetrievalResponse",
]
