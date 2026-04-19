from __future__ import annotations

import hashlib
import shutil
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from structural_tree_app.domain.document_codec import document_to_dict, fragment_to_dict
from structural_tree_app.domain.enums import (
    AuthorityLevel,
    DocumentApprovalStatus,
    DocumentCorpusPolicy,
    NormativeClassification,
)
from structural_tree_app.domain.models import Document, DocumentFragment, Project
from structural_tree_app.services.project_service import ProjectPersistenceError, ProjectService
from structural_tree_app.validation.json_schema import validate_document_fragment_payload, validate_document_payload


IngestionStatus = Literal[
    "ingested",
    "duplicate_skipped",
    "unsupported_document_for_ingestion",
    "ocr_deferred",
]


@dataclass
class IngestionResult:
    status: IngestionStatus
    document: Document | None
    fragment_count: int
    message: str
    fragments: list[DocumentFragment] | None = None


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_document_file_bytes(doc: Document) -> bool:
    """True if ``doc.file_path`` exists on disk and matches ``doc.content_hash`` (safe to serve)."""
    try:
        p = Path(doc.file_path)
    except (TypeError, ValueError):
        return False
    if not p.is_file():
        return False
    try:
        return _sha256_file(p) == doc.content_hash
    except OSError:
        return False


def _sha256_utf8(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_text(text: str) -> str:
    t = unicodedata.normalize("NFKC", text)
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    return t.strip()


def _extract_pages_raw(path: Path) -> tuple[list[tuple[int, str]], str]:
    """Return (list of (1-based page number, raw page text), kind)."""
    suf = path.suffix.lower()
    if suf == ".txt":
        return [(1, path.read_text(encoding="utf-8"))], "txt"
    if suf == ".pdf":
        try:
            from pypdf import PdfReader
        except ImportError as e:
            raise RuntimeError(
                "PDF ingestion requires the 'pypdf' package. Install project dependencies."
            ) from e
        reader = PdfReader(str(path))
        pages: list[tuple[int, str]] = []
        for i, page in enumerate(reader.pages, start=1):
            pages.append((i, page.extract_text() or ""))
        return pages, "pdf"
    raise ValueError(f"Unsupported file type for ingestion: {suf}")


def _join_normalized_pages(pages: list[tuple[int, str]]) -> tuple[str, list[tuple[int, int, int]]]:
    """Build normalized full text and char spans (start, end_exclusive, page_1based) per page."""
    parts: list[str] = []
    spans: list[tuple[int, int, int]] = []
    offset = 0
    for i, (page_num, raw) in enumerate(pages):
        n = _normalize_text(raw)
        if i > 0:
            parts.append("\n\n")
            offset += 2
        start = offset
        parts.append(n)
        offset += len(n)
        spans.append((start, offset, page_num))
    return "".join(parts), spans


def _pages_for_char_range(
    spans: list[tuple[int, int, int]], cstart: int, cend: int
) -> tuple[int | None, int | None]:
    hit_pages = [pn for s, e, pn in spans if cend > s and cstart < e]
    if not hit_pages:
        return None, None
    return min(hit_pages), max(hit_pages)


def _segment_text(text: str, max_chars: int = 2000) -> list[str]:
    if not text:
        return []
    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    buf: list[str] = []
    size = 0
    for p in paragraphs:
        plen = len(p) + (2 if buf else 0)
        if buf and size + plen > max_chars:
            chunks.append("\n\n".join(buf))
            buf = [p]
            size = len(p)
        else:
            buf.append(p)
            size += plen
    if buf:
        chunks.append("\n\n".join(buf))
    out: list[str] = []
    for c in chunks:
        if len(c) <= max_chars:
            out.append(c)
        else:
            for i in range(0, len(c), max_chars):
                out.append(c[i : i + max_chars])
    return out


def stable_fragment_id(document_id: str, chunk_index: int, text: str) -> str:
    h = hashlib.sha256(f"{document_id}|{chunk_index}|{text}".encode("utf-8")).hexdigest()[:12]
    return f"frag_{h}"


class DocumentIngestionService:
    """
    Local-first pipeline: import → normalize → segment → persist.
    Successful ingestion records the document as ingested only; it does not
    promote it into the normative (active) corpus unless project policy or
    explicit activation says so.
    """

    def __init__(self, project_service: ProjectService, project_id: str) -> None:
        self.ps = project_service
        self.project_id = project_id
        self._base = project_service.repository.base_path / project_id / "documents"
        self._base.mkdir(parents=True, exist_ok=True)

    def _rel(self, *parts: str) -> str:
        return str(Path(self.project_id, "documents", *parts))

    def _find_document_by_content_hash(self, content_hash: str) -> str | None:
        if not self._base.is_dir():
            return None
        for doc_dir in self._base.iterdir():
            if not doc_dir.is_dir():
                continue
            p = doc_dir / "document.json"
            if not p.is_file():
                continue
            rel = self._rel(doc_dir.name, "document.json")
            if not self.ps.repository.exists(rel):
                continue
            try:
                raw = self.ps.repository.read(rel)
            except (ValueError, OSError):
                continue
            if raw.get("content_hash") == content_hash:
                return str(raw.get("id"))
        return None

    def load_document(self, document_id: str) -> Document:
        rel = self._rel(document_id, "document.json")
        if not self.ps.repository.exists(rel):
            raise ProjectPersistenceError(f"Missing document: {document_id}")
        raw = self.ps.repository.read(rel)
        validate_document_payload(raw)
        from structural_tree_app.domain.document_codec import document_from_dict

        return document_from_dict(raw)

    def load_fragments(self, document_id: str) -> list[DocumentFragment]:
        rel = self._rel(document_id, "fragments.json")
        if not self.ps.repository.exists(rel):
            return []
        data = self.ps.repository.read_json(rel)
        if not isinstance(data, list):
            raise ProjectPersistenceError("fragments.json must be an array")
        from structural_tree_app.domain.document_codec import fragment_from_dict

        out: list[DocumentFragment] = []
        for i, item in enumerate(data):
            if not isinstance(item, dict):
                raise ProjectPersistenceError(f"fragments.json[{i}] must be an object")
            validate_document_fragment_payload(item)
            out.append(fragment_from_dict(item))
        return sorted(out, key=lambda f: f.chunk_index)

    def save_document(self, doc: Document) -> None:
        """Persist document.json only (metadata update)."""
        d_payload = document_to_dict(doc)
        validate_document_payload(d_payload)
        self.ps.repository.write(self._rel(doc.id, "document.json"), d_payload)

    def approve_document(self, document_id: str) -> None:
        doc = self.load_document(document_id)
        doc.approval_status = DocumentApprovalStatus.APPROVED
        self.save_document(doc)
        project = self.ps.load_project(self.project_id)
        if project.document_corpus_policy == DocumentCorpusPolicy.APPROVE_ALSO_ACTIVATES:
            self._add_to_allowed(project, document_id)
            self.ps.save_project(project)

    def reject_document(self, document_id: str) -> None:
        doc = self.load_document(document_id)
        doc.approval_status = DocumentApprovalStatus.REJECTED
        self.save_document(doc)

    def activate_for_normative_corpus(self, document_id: str) -> None:
        doc = self.load_document(document_id)
        if doc.approval_status != DocumentApprovalStatus.APPROVED:
            raise ValueError("Document must be approved before it can be active for the normative corpus.")
        project = self.ps.load_project(self.project_id)
        self._add_to_allowed(project, document_id)
        self.ps.save_project(project)

    def deactivate_from_normative_corpus(self, document_id: str) -> None:
        project = self.ps.load_project(self.project_id)
        acc = project.active_code_context
        acc.allowed_document_ids = [x for x in acc.allowed_document_ids if x != document_id]
        self.ps.save_project(project)

    @staticmethod
    def _add_to_allowed(project: Project, document_id: str) -> None:
        acc = project.active_code_context
        if document_id not in acc.allowed_document_ids:
            acc.allowed_document_ids = [*acc.allowed_document_ids, document_id]

    def ingest_local_file(
        self,
        source_path: str | Path,
        *,
        title: str | None = None,
        author: str = "",
        edition: str = "",
        version_label: str = "1",
        document_type: str = "corpus",
        topics: list[str] | None = None,
        language: str = "es",
        authority_level: AuthorityLevel = AuthorityLevel.PRIMARY,
        publication_year: int | None = None,
        discipline: str | None = None,
        standard_family: str | None = None,
        normative_classification: NormativeClassification = NormativeClassification.UNKNOWN,
        ingestion_method: str = "file",
        duplicate_policy: Literal["skip", "reingest"] = "skip",
    ) -> IngestionResult:
        path = Path(source_path).resolve()
        if not path.is_file():
            return IngestionResult(
                status="unsupported_document_for_ingestion",
                document=None,
                fragment_count=0,
                message=f"Not a file: {path}",
            )

        topics = topics or []
        content_hash = _sha256_file(path)

        existing_id = self._find_document_by_content_hash(content_hash)
        if existing_id is not None and duplicate_policy == "skip":
            doc = self.load_document(existing_id)
            n = len(self.load_fragments(existing_id))
            return IngestionResult(
                status="duplicate_skipped",
                document=doc,
                fragment_count=n,
                message="Duplicate content_hash; existing document returned.",
                fragments=None,
            )

        try:
            raw_pages, kind = _extract_pages_raw(path)
        except ValueError as e:
            return IngestionResult(
                status="unsupported_document_for_ingestion",
                document=None,
                fragment_count=0,
                message=str(e),
            )
        except OSError as e:
            return IngestionResult(
                status="unsupported_document_for_ingestion",
                document=None,
                fragment_count=0,
                message=str(e),
            )
        except RuntimeError as e:
            return IngestionResult(
                status="unsupported_document_for_ingestion",
                document=None,
                fragment_count=0,
                message=str(e),
            )

        normalized, page_spans = _join_normalized_pages(raw_pages)
        if not normalized:
            if kind == "pdf":
                return IngestionResult(
                    status="ocr_deferred",
                    document=None,
                    fragment_count=0,
                    message="No extractable text layer on PDF; OCR is out of scope for Block 2 (deferred).",
                )
            return IngestionResult(
                status="unsupported_document_for_ingestion",
                document=None,
                fragment_count=0,
                message="No extractable text content.",
            )

        doc = Document(
            title=title or path.stem,
            author=author,
            edition=edition,
            version_label=version_label,
            publication_year=publication_year,
            document_type=document_type,
            authority_level=authority_level,
            topics=topics,
            language=language,
            file_path=str(path),
            content_hash=content_hash,
            approval_status=DocumentApprovalStatus.PENDING,
            normative_classification=normative_classification,
            discipline=discipline,
            standard_family=standard_family,
        )

        # Persist a durable copy for original-source viewing (upload paths may be temporary).
        try:
            doc_dir = self._base / doc.id
            doc_dir.mkdir(parents=True, exist_ok=True)
            ext = path.suffix.lower() or ".bin"
            dest = doc_dir / f"original{ext}"
            shutil.copy2(path, dest)
            doc.file_path = str(dest.resolve())
        except OSError:
            pass

        chunks = _segment_text(normalized)
        fragments: list[DocumentFragment] = []
        offset = 0
        for i, chunk in enumerate(chunks):
            start = offset
            end = offset + len(chunk)
            ps, pe = _pages_for_char_range(page_spans, start, end)
            if kind == "txt":
                ps, pe = None, None
            fid = stable_fragment_id(doc.id, i, chunk)
            fhash = _sha256_utf8(chunk)
            fragments.append(
                DocumentFragment(
                    document_id=doc.id,
                    chapter="",
                    section="",
                    page_start=ps,
                    page_end=pe,
                    fragment_type="chunk",
                    topic_tags=list(topics),
                    authority_level=authority_level,
                    text=chunk,
                    chunk_index=i,
                    char_start=start,
                    char_end=end,
                    fragment_content_hash=fhash,
                    material_content_hash=content_hash,
                    ingestion_method=ingestion_method,
                    document_approval_status=doc.approval_status,
                    document_normative_classification=doc.normative_classification,
                    id=fid,
                )
            )
            offset = end

        self._persist_document_bundle(doc, fragments)
        self._register_ingested_only(doc.id)
        self._g1_apply_governance_post_ingest(doc, len(fragments), len(normalized))
        self._g2_assess_corpus_post_g1(doc)

        return IngestionResult(
            status="ingested",
            document=doc,
            fragment_count=len(fragments),
            message="OK",
            fragments=fragments,
        )

    def _persist_document_bundle(self, doc: Document, fragments: list[DocumentFragment]) -> None:
        d_payload = document_to_dict(doc)
        validate_document_payload(d_payload)
        self.ps.repository.write(self._rel(doc.id, "document.json"), d_payload)
        frag_payload: list[dict[str, Any]] = []
        for f in fragments:
            fp = fragment_to_dict(f)
            validate_document_fragment_payload(fp)
            frag_payload.append(fp)
        self.ps.repository.write(self._rel(doc.id, "fragments.json"), frag_payload)

    def _register_ingested_only(self, document_id: str) -> None:
        project = self.ps.load_project(self.project_id)
        if document_id not in project.ingested_document_ids:
            project.ingested_document_ids = [*project.ingested_document_ids, document_id]
        self.ps.save_project(project)

    def _g1_apply_governance_post_ingest(
        self, doc: Document, fragment_count: int, normalized_char_count: int
    ) -> None:
        from structural_tree_app.services.governance_document_pipeline import (
            apply_governance_after_successful_ingestion,
        )

        apply_governance_after_successful_ingestion(
            self.ps.governance_store(),
            self.project_id,
            doc,
            fragment_count=fragment_count,
            normalized_char_count=normalized_char_count,
        )

    def _g2_assess_corpus_post_g1(self, doc: Document) -> None:
        from structural_tree_app.services.corpus_assessment_service import (
            assess_and_persist_document_corpus_assessment,
        )

        assess_and_persist_document_corpus_assessment(
            self.ps.governance_store(),
            self,
            self.project_id,
            doc.id,
        )


def register_document_metadata_only(
    file_path: str | Path,
    title: str,
    author: str,
    edition: str,
    version_label: str,
    document_type: str,
    topics: list[str],
    language: str,
    authority_level: AuthorityLevel = AuthorityLevel.PRIMARY,
    publication_year: int | None = None,
) -> Document:
    path = Path(file_path)
    content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    return Document(
        title=title,
        author=author,
        edition=edition,
        version_label=version_label,
        publication_year=publication_year,
        document_type=document_type,
        authority_level=authority_level,
        topics=topics,
        language=language,
        file_path=str(path),
        content_hash=content_hash,
        approval_status=DocumentApprovalStatus.PENDING,
        normative_classification=NormativeClassification.UNKNOWN,
    )


__all__ = [
    "DocumentIngestionService",
    "IngestionResult",
    "register_document_metadata_only",
    "stable_fragment_id",
]
