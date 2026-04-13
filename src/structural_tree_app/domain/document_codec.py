from __future__ import annotations

import hashlib
from dataclasses import asdict
from typing import Any

from structural_tree_app.domain.enums import AuthorityLevel, DocumentApprovalStatus, NormativeClassification
from structural_tree_app.domain.models import Document, DocumentFragment


def document_to_dict(doc: Document) -> dict[str, Any]:
    d = asdict(doc)
    d["authority_level"] = doc.authority_level.value if isinstance(doc.authority_level, AuthorityLevel) else str(doc.authority_level)
    d["approval_status"] = (
        doc.approval_status.value if isinstance(doc.approval_status, DocumentApprovalStatus) else str(doc.approval_status)
    )
    d["normative_classification"] = (
        doc.normative_classification.value
        if isinstance(doc.normative_classification, NormativeClassification)
        else str(doc.normative_classification)
    )
    return d


def document_from_dict(data: dict[str, Any]) -> Document:
    al = data["authority_level"]
    if isinstance(al, str):
        al = AuthorityLevel(al)
    ap = data.get("approval_status", DocumentApprovalStatus.PENDING.value)
    if isinstance(ap, str):
        ap = DocumentApprovalStatus(ap)
    nc = data.get("normative_classification", NormativeClassification.UNKNOWN.value)
    if isinstance(nc, str):
        nc = NormativeClassification(nc)
    return Document(
        title=data["title"],
        author=data.get("author", ""),
        edition=data.get("edition", ""),
        version_label=data.get("version_label", ""),
        publication_year=data.get("publication_year"),
        document_type=data.get("document_type", "other"),
        authority_level=al,
        topics=list(data.get("topics", [])),
        language=data["language"],
        file_path=data["file_path"],
        content_hash=data["content_hash"],
        approval_status=ap,
        normative_classification=nc,
        discipline=data.get("discipline"),
        standard_family=data.get("standard_family"),
        id=data["id"],
        created_at=data["created_at"],
    )


def fragment_to_dict(frag: DocumentFragment) -> dict[str, Any]:
    d = asdict(frag)
    d["authority_level"] = frag.authority_level.value if isinstance(frag.authority_level, AuthorityLevel) else str(frag.authority_level)
    d["document_approval_status"] = (
        frag.document_approval_status.value
        if isinstance(frag.document_approval_status, DocumentApprovalStatus)
        else str(frag.document_approval_status)
    )
    d["document_normative_classification"] = (
        frag.document_normative_classification.value
        if isinstance(frag.document_normative_classification, NormativeClassification)
        else str(frag.document_normative_classification)
    )
    return d


def fragment_from_dict(data: dict[str, Any]) -> DocumentFragment:
    al = data["authority_level"]
    if isinstance(al, str):
        al = AuthorityLevel(al)
    das = data.get("document_approval_status", DocumentApprovalStatus.PENDING.value)
    if isinstance(das, str):
        das = DocumentApprovalStatus(das)
    dnc = data.get("document_normative_classification", NormativeClassification.UNKNOWN.value)
    if isinstance(dnc, str):
        dnc = NormativeClassification(dnc)
    text = data.get("text", "")
    frag_hash = data.get("fragment_content_hash") or ""
    if not frag_hash and text:
        frag_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return DocumentFragment(
        document_id=data["document_id"],
        chapter=data.get("chapter", ""),
        section=data.get("section", ""),
        page_start=data.get("page_start"),
        page_end=data.get("page_end"),
        fragment_type=data.get("fragment_type", "chunk"),
        topic_tags=list(data.get("topic_tags", [])),
        authority_level=al,
        text=text,
        chunk_index=int(data.get("chunk_index", 0)),
        char_start=data.get("char_start"),
        char_end=data.get("char_end"),
        fragment_content_hash=frag_hash,
        material_content_hash=data.get("material_content_hash", ""),
        ingestion_method=data.get("ingestion_method", "file"),
        document_approval_status=das,
        document_normative_classification=dnc,
        id=data["id"],
        sibling_fragment_ids=list(data.get("sibling_fragment_ids", [])),
        linked_fragment_ids=list(data.get("linked_fragment_ids", [])),
    )


__all__ = [
    "document_from_dict",
    "document_to_dict",
    "fragment_from_dict",
    "fragment_to_dict",
]
