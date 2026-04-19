"""
G5 — Deterministic derived knowledge generation from the governed active corpus.

Does not replace retrieval or citations: artifacts are subordinate and regenerable.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import replace
from typing import Any, Literal

from structural_tree_app.domain.derived_knowledge_codec import derived_knowledge_bundle_to_dict
from structural_tree_app.domain.derived_knowledge_models import (
    DerivedArtifacts,
    DerivedKnowledgeBundle,
    DocumentDigestEntry,
    FormulaRegistryEntry,
    GovernanceSignalEntry,
    NavigationHintEntry,
    SourceAnchorRef,
    TopicDigestEntry,
)
from structural_tree_app.domain.enums import DocumentApprovalStatus, NormativeClassification
from structural_tree_app.domain.governance_enums import DocumentGovernanceDisposition, GovernanceRetrievalBinding
from structural_tree_app.domain.governance_models import ActiveKnowledgeProjection, DocumentGovernanceIndex
from structural_tree_app.domain.governance_codec import active_knowledge_projection_to_dict
from structural_tree_app.domain.models import Document, Project, utc_now
from structural_tree_app.domain.tree_codec import canonicalize_json
from structural_tree_app.services.document_service import DocumentIngestionService
from structural_tree_app.services.project_service import ProjectService
from structural_tree_app.services.retrieval_service import (
    _authoritative_set_has_unresolved_conflict,
    _effective_authoritative_document_ids,
    _filter_authoritative_ids_against_index,
)
from structural_tree_app.services.simple_span_m5_service import METHOD_LABEL as M5_METHOD_LABEL
from structural_tree_app.storage.derived_knowledge_store import DerivedKnowledgeStore

GovernanceNormativeBlock = Literal["conflict", "missing_index", "empty_authoritative"]

_FORMULA_HINT = re.compile(
    r"(?is)\b(equation|eq\.|formula|capacity|demand|check|verify|resistance\s+factor|limit\s+state|phi\b|φ)\b"
)


def _passes_normative_derived_corpus(
    project: Project,
    doc: Document,
    *,
    explicit_authoritative_ids: frozenset[str] | None,
) -> bool:
    if doc.approval_status != DocumentApprovalStatus.APPROVED:
        return False
    if doc.normative_classification != NormativeClassification.PRIMARY_STANDARD:
        return False
    if doc.standard_family != project.active_code_context.primary_standard_family:
        return False
    if explicit_authoritative_ids is not None:
        return doc.id in explicit_authoritative_ids
    return doc.id in project.active_code_context.allowed_document_ids


def _normative_block_and_explicit_ids(
    project: Project,
    gproj: ActiveKnowledgeProjection | None,
    gindex: DocumentGovernanceIndex | None,
) -> tuple[
    GovernanceNormativeBlock | None,
    str,
    frozenset[str] | None,
    tuple[str, ...],
]:
    """
    Mirror ``DocumentRetrievalService.search`` early governance gate (no document loop).

    Returns (block_kind, normative_source, explicit_authoritative_ids_or_none, warnings).
    """
    warnings: list[str] = []
    use_explicit = (
        gproj is not None
        and gproj.retrieval_binding == GovernanceRetrievalBinding.EXPLICIT_PROJECTION
    )
    if not use_explicit:
        return None, "legacy_allowed_documents", None, tuple(warnings)

    if gindex is None:
        return (
            "missing_index",
            "explicit_projection",
            None,
            (
                "explicit_projection binding requires a document governance index for this project.",
            ),
        )

    raw_auth = _effective_authoritative_document_ids(gproj)
    explicit_authoritative_ids, widx = _filter_authoritative_ids_against_index(raw_auth, gindex)
    warnings.extend(widx)
    if not explicit_authoritative_ids:
        return (
            "empty_authoritative",
            "explicit_projection",
            explicit_authoritative_ids,
            tuple(warnings)
            + (
                "Normative retrieval is unavailable: explicit active knowledge projection has "
                "no authoritative document ids that resolve against the governance index.",
            ),
        )
    if _authoritative_set_has_unresolved_conflict(gindex, explicit_authoritative_ids):
        warnings.append("governance_conflict_blocks_normative")
        return "conflict", "explicit_projection", explicit_authoritative_ids, tuple(warnings)

    return None, "explicit_projection", explicit_authoritative_ids, tuple(warnings)


def _governance_note_for_doc(
    disposition: DocumentGovernanceDisposition | None,
) -> str:
    if disposition == DocumentGovernanceDisposition.CONFLICTING_UNRESOLVED:
        return (
            "Governance disposition is conflicting_unresolved; normative retrieval may be refused "
            "while this remains unresolved."
        )
    if disposition == DocumentGovernanceDisposition.SUPERSEDED:
        return "Governance disposition is superseded; verify active truth and supporting assessments."
    return ""


def _coverage_bullets(doc: Document, fragments: list[Any]) -> tuple[str, ...]:
    meta = f"Title={doc.title}; topics={','.join(sorted(doc.topics))}; standard_family={doc.standard_family!s}"
    lines: list[str] = [meta]
    for frag in sorted(fragments, key=lambda f: (f.chunk_index, f.id)):
        t = " ".join(frag.text.split())
        excerpt = t if len(t) <= 160 else t[:157] + "..."
        lines.append(f"chunk {frag.chunk_index}: {excerpt}")
    return tuple(lines)


def _topic_key_for_doc(doc: Document, rec: Any | None) -> str:
    fam = doc.standard_family or "unknown_family"
    tags: list[str] = []
    if rec is not None and rec.classification is not None:
        tags.extend(rec.classification.topic_scope_tags)
    if not tags:
        tags = list(doc.topics)
    tag_part = "|".join(sorted({t.strip().lower() for t in tags if t}))
    return f"{fam}::{tag_part or 'untagged'}"


def _stable_id(prefix: str, parts: tuple[str, ...]) -> str:
    h = hashlib.sha256(json.dumps(parts, sort_keys=True).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{h}"


def _build_fingerprint(
    project: Project,
    gproj: ActiveKnowledgeProjection | None,
    corpus_doc_ids: list[str],
    ingestion: DocumentIngestionService,
    gindex: DocumentGovernanceIndex | None,
) -> tuple[str, dict[str, Any]]:
    proj_payload = {
        "allowed_document_ids": sorted(project.active_code_context.allowed_document_ids),
        "ingested_document_ids": sorted(project.ingested_document_ids),
        "primary_standard_family": project.active_code_context.primary_standard_family,
        "updated_at": project.updated_at,
    }
    proj_dict = active_knowledge_projection_to_dict(gproj) if gproj is not None else None
    mat: dict[str, Any] = {}
    for did in sorted(corpus_doc_ids):
        doc = ingestion.load_document(did)
        frags = ingestion.load_fragments(did)
        mat[did] = {
            "content_hash": doc.content_hash,
            "fragments": [
                {
                    "fragment_content_hash": f.fragment_content_hash,
                    "id": f.id,
                }
                for f in sorted(frags, key=lambda x: (x.chunk_index, x.id))
            ],
        }
        if gindex is not None and did in gindex.by_document_id:
            r = gindex.by_document_id[did]
            mat[did]["governance"] = {
                "disposition": r.disposition.value,
                "updated_at": r.updated_at,
            }
    payload = canonicalize_json(
        {
            "corpus_documents": mat,
            "governance_projection": proj_dict,
            "project": proj_payload,
            "project_id": project.id,
        }
    )
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    fp = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return fp, payload


class DerivedKnowledgeService:
    """Generate and persist derived knowledge bundles (explicit regeneration)."""

    def __init__(self, project_service: ProjectService) -> None:
        self._ps = project_service
        self._store = DerivedKnowledgeStore(project_service.repository)

    def try_load_bundle(self, project_id: str) -> DerivedKnowledgeBundle | None:
        return self._store.try_load_bundle(project_id)

    def regenerate(self, project_id: str) -> DerivedKnowledgeBundle:
        project = self._ps.load_project(project_id)
        gs = self._ps.governance_store()
        gproj = gs.try_load_active_knowledge_projection(project_id)
        gindex = gs.try_load_document_governance_index(project_id)
        ingestion = DocumentIngestionService(self._ps, project_id)

        block, norm_src, explicit_ids, gw = _normative_block_and_explicit_ids(project, gproj, gindex)
        block_str: str | None = block

        corpus_ids: list[str] = []
        for did in project.ingested_document_ids:
            doc = ingestion.load_document(did)
            if not _passes_normative_derived_corpus(project, doc, explicit_authoritative_ids=explicit_ids):
                continue
            corpus_ids.append(did)
        corpus_ids = sorted(corpus_ids)

        doc_digests: list[DocumentDigestEntry] = []
        formula_entries: list[FormulaRegistryEntry] = []
        gov_signals: list[GovernanceSignalEntry] = []

        for did in corpus_ids:
            doc = ingestion.load_document(did)
            frags = ingestion.load_fragments(did)
            rec = gindex.by_document_id.get(did) if gindex is not None else None
            disp = rec.disposition if rec is not None else None
            disp_s = disp.value if disp is not None else None
            anchors: list[SourceAnchorRef] = []
            for frag in sorted(frags, key=lambda f: (f.chunk_index, f.id)):
                anchors.append(
                    SourceAnchorRef(
                        document_id=doc.id,
                        fragment_id=frag.id,
                        document_content_hash=doc.content_hash,
                        fragment_content_hash=frag.fragment_content_hash,
                        governance_disposition=disp_s,
                        normative_classification=doc.normative_classification.value,
                    )
                )
                if _FORMULA_HINT.search(frag.text):
                    excerpt = " ".join(frag.text.split())
                    if len(excerpt) > 140:
                        excerpt = excerpt[:137] + "..."
                    exec_cap = "deterministic_m5_hook" if M5_METHOD_LABEL in frag.text else "none"
                    formula_entries.append(
                        FormulaRegistryEntry(
                            entry_id=_stable_id("freg", (did, frag.id, "formula_hint")),
                            label=excerpt,
                            recognition_pattern_id="kw:structural_hint",
                            execution_capability=exec_cap,
                            supported_by_anchors=(
                                SourceAnchorRef(
                                    document_id=doc.id,
                                    fragment_id=frag.id,
                                    document_content_hash=doc.content_hash,
                                    fragment_content_hash=frag.fragment_content_hash,
                                    governance_disposition=disp_s,
                                    normative_classification=doc.normative_classification.value,
                                ),
                            ),
                            non_authoritative=True,
                        )
                    )

            note = _governance_note_for_doc(disp)
            doc_digests.append(
                DocumentDigestEntry(
                    document_id=doc.id,
                    document_title=doc.title,
                    standard_family=doc.standard_family,
                    coverage_bullets=_coverage_bullets(doc, frags),
                    fragment_anchors=tuple(anchors),
                    governance_disposition=disp_s,
                    governance_note=note,
                )
            )
            if disp in (
                DocumentGovernanceDisposition.CONFLICTING_UNRESOLVED,
                DocumentGovernanceDisposition.SUPERSEDED,
            ):
                gov_signals.append(
                    GovernanceSignalEntry(
                        signal_id=_stable_id("gsig", (did, disp_s or "")),
                        document_id=did,
                        disposition=disp_s or "",
                        note=note or f"Disposition={disp_s}",
                        related_document_ids=(),
                    )
                )

        # Topic digests (group by topic_key)
        topic_map: dict[str, dict[str, Any]] = {}
        for d in doc_digests:
            rec = gindex.by_document_id.get(d.document_id) if gindex is not None else None
            doc = ingestion.load_document(d.document_id)
            key = _topic_key_for_doc(doc, rec)
            bucket = topic_map.setdefault(
                key,
                {"doc_ids": set(), "anchors": [], "lines": []},
            )
            bucket["doc_ids"].add(d.document_id)
            bucket["lines"].append(f"Document {d.document_title} ({d.document_id})")
            for a in d.fragment_anchors[:3]:
                bucket["anchors"].append(a)
        topic_digests: list[TopicDigestEntry] = []
        for key in sorted(topic_map.keys()):
            b = topic_map[key]
            anchors = tuple(b["anchors"][:8])
            topic_digests.append(
                TopicDigestEntry(
                    topic_key=key,
                    summary_lines=tuple(sorted(set(b["lines"]))),
                    document_ids=tuple(sorted(b["doc_ids"])),
                    fragment_anchors=anchors,
                )
            )

        # Navigation hints: per standard_family
        fam_to_docs: dict[str, list[str]] = {}
        for d in doc_digests:
            fam = d.standard_family or "unknown"
            fam_to_docs.setdefault(fam, []).append(d.document_id)
        nav: list[NavigationHintEntry] = []
        for fam in sorted(fam_to_docs.keys()):
            ids = tuple(sorted(fam_to_docs[fam]))
            frag_ids: list[str] = []
            for did in ids:
                dd = next(x for x in doc_digests if x.document_id == did)
                frag_ids.extend([a.fragment_id for a in dd.fragment_anchors[:2]])
            nav.append(
                NavigationHintEntry(
                    hint_id=_stable_id("nav", (fam,)),
                    label=f"If the query concerns {fam} primary-standard material, consult these governed documents first.",
                    consult_document_ids=ids,
                    consult_fragment_ids=tuple(frag_ids),
                )
            )

        fp, fp_inputs = _build_fingerprint(project, gproj, corpus_ids, ingestion, gindex)

        arts = DerivedArtifacts(
            document_digests=tuple(sorted(doc_digests, key=lambda d: d.document_id)),
            topic_digests=tuple(topic_digests),
            navigation_hints=tuple(sorted(nav, key=lambda n: n.hint_id)),
            formula_registry_entries=tuple(sorted(formula_entries, key=lambda f: f.entry_id)),
            governance_signals=tuple(sorted(gov_signals, key=lambda g: g.signal_id)),
        )

        candidate = DerivedKnowledgeBundle(
            project_id=project_id,
            bundle_version=1,
            generated_at=utc_now(),
            generation_mode="deterministic_v1",
            source_fingerprint=fp,
            normative_retrieval_would_block=block_str,
            normative_retrieval_source=norm_src,
            governance_warnings_snapshot=gw,
            fingerprint_inputs=fp_inputs,
            artifacts=arts,
        )

        old = self._store.try_load_bundle(project_id)
        if old is not None and old.source_fingerprint == candidate.source_fingerprint:
            return old

        version = (old.bundle_version + 1) if old is not None else 1
        to_save = replace(candidate, bundle_version=version, generated_at=utc_now())
        self._store.save_bundle(to_save)
        return to_save

    def bundle_to_canonical_dict(self, bundle: DerivedKnowledgeBundle) -> dict[str, Any]:
        """Deterministic dict for tests (excludes volatile generated_at when comparing content)."""
        d = derived_knowledge_bundle_to_dict(bundle)
        d.pop("generated_at", None)
        return canonicalize_json(d)


__all__ = [
    "DerivedKnowledgeService",
    "_build_fingerprint",
    "_normative_block_and_explicit_ids",
    "_passes_normative_derived_corpus",
]
