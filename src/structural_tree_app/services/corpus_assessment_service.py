"""G2: deterministic candidate-level corpus comparison for governed documents (not final truth)."""

from __future__ import annotations

import re
from pathlib import Path

from structural_tree_app.domain.enums import NormativeClassification
from structural_tree_app.domain.governance_enums import CorpusAssessmentCandidateRelation
from structural_tree_app.domain.governance_models import CorpusAssessmentCandidate, DocumentCorpusAssessment
from structural_tree_app.domain.models import Document, DocumentFragment, utc_now
from structural_tree_app.services.document_service import DocumentIngestionService
from structural_tree_app.services.governance_store import GovernanceStore

# Narrow deterministic thresholds (tunable in later phases; keep tests aligned).
_JACCARD_OVERLAP_MIN = 0.06
_JACCARD_CONTRADICTION_MIN = 0.11
_TITLE_JACCARD_SUPERSESSION_MIN = 0.28
_MAX_FRAGMENTS_FOR_FINGERPRINT = 14
_MAX_CHARS_PER_FRAG = 2400

_TOKEN_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)


def _tokens(text: str) -> frozenset[str]:
    words = _TOKEN_RE.findall(text.lower())
    return frozenset(w for w in words if len(w) >= 3)


def _jaccard(a: frozenset[str], b: frozenset[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 0.0
    return len(a & b) / len(union)


def _fingerprint_words(doc: Document, frags: list[DocumentFragment]) -> frozenset[str]:
    stem = Path(doc.file_path).stem
    parts: list[str] = [doc.title or "", stem]
    ordered = sorted(frags, key=lambda f: f.chunk_index)[:_MAX_FRAGMENTS_FOR_FINGERPRINT]
    for f in ordered:
        parts.append((f.text or "")[:_MAX_CHARS_PER_FRAG])
    return _tokens("\n".join(parts))


def _title_jaccard(a: Document, b: Document) -> float:
    return _jaccard(_tokens(a.title or ""), _tokens(b.title or ""))


def _same_standard_family(a: Document, b: Document) -> bool:
    sa = (a.standard_family or "").strip()
    sb = (b.standard_family or "").strip()
    return bool(sa) and sa == sb


def _both_primary(a: Document, b: Document) -> bool:
    return (
        a.normative_classification == NormativeClassification.PRIMARY_STANDARD
        and b.normative_classification == NormativeClassification.PRIMARY_STANDARD
    )


def _supersession_meta_signal(subject: Document, other: Document) -> tuple[bool, list[str]]:
    signals: list[str] = []
    sy = subject.publication_year
    oy = other.publication_year
    if isinstance(sy, int) and isinstance(oy, int) and sy > oy:
        signals.append("publication_year_increased")
        return True, signals
    sv = (subject.version_label or "").strip()
    ov = (other.version_label or "").strip()
    if sv and ov and sv != ov:
        signals.append("version_label_differs")
        return True, signals
    se = (subject.edition or "").strip()
    oe = (other.edition or "").strip()
    if se and oe and se != oe:
        signals.append("edition_differs")
        return True, signals
    return False, signals


def _collect_pair_candidates(
    subject: Document,
    subject_frags: list[DocumentFragment],
    other: Document,
    other_frags: list[DocumentFragment],
) -> list[CorpusAssessmentCandidate]:
    out: list[CorpusAssessmentCandidate] = []
    if other.id == subject.id:
        return out

    sub_fp = _fingerprint_words(subject, subject_frags)
    oth_fp = _fingerprint_words(other, other_frags)
    fp_j = round(_jaccard(sub_fp, oth_fp), 6)
    tj = round(_title_jaccard(subject, other), 6)

    if subject.content_hash == other.content_hash:
        out.append(
            CorpusAssessmentCandidate(
                other_document_id=other.id,
                relation=CorpusAssessmentCandidateRelation.DUPLICATE_CANDIDATE,
                confidence="high",
                signals=tuple(
                    sorted(
                        (
                            "content_hash_match",
                            "material_identity_same_sha256",
                        )
                    )
                ),
                details={"content_hash": subject.content_hash},
            )
        )
        return out

    fam = _same_standard_family(subject, other)
    prim = _both_primary(subject, other)

    # Supporting / complementary role (subject is non-primary reference/support vs primary other).
    if fam and other.normative_classification == NormativeClassification.PRIMARY_STANDARD:
        if subject.normative_classification in (
            NormativeClassification.SUPPORTING_DOCUMENT,
            NormativeClassification.REFERENCE_DOCUMENT,
        ):
            out.append(
                CorpusAssessmentCandidate(
                    other_document_id=other.id,
                    relation=CorpusAssessmentCandidateRelation.SUPPORTING_CANDIDATE,
                    confidence="medium",
                    signals=tuple(
                        sorted(
                            (
                                "same_standard_family",
                                "subject_normative_role_supporting_or_reference",
                                "other_normative_role_primary_standard",
                            )
                        )
                    ),
                    details={
                        "subject_normative_classification": subject.normative_classification.value,
                        "other_normative_classification": other.normative_classification.value,
                        "standard_family": (subject.standard_family or "").strip(),
                    },
                )
            )

    # Primary vs primary: supersession and contradiction heuristics.
    supersession_emitted = False
    sup_details: dict[str, object] = {
        "fingerprint_jaccard": fp_j,
        "title_jaccard": tj,
    }
    sup_signals: list[str] = []
    if fam and prim:
        meta_ok, meta_sigs = _supersession_meta_signal(subject, other)
        sup_signals.extend(meta_sigs)
        title_ok = tj >= _TITLE_JACCARD_SUPERSESSION_MIN
        if title_ok:
            sup_signals.append("title_similarity_above_threshold")
        supersession_ok = meta_ok and title_ok
        if supersession_ok:
            supersession_emitted = True
            conf = "high" if "publication_year_increased" in sup_signals else "medium"
            out.append(
                CorpusAssessmentCandidate(
                    other_document_id=other.id,
                    relation=CorpusAssessmentCandidateRelation.SUPERSESSION_CANDIDATE,
                    confidence=conf,
                    signals=tuple(sorted(set(sup_signals))),
                    details={
                        **sup_details,
                        "subject_publication_year": subject.publication_year,
                        "other_publication_year": other.publication_year,
                        "subject_version_label": subject.version_label,
                        "other_version_label": other.version_label,
                    },
                )
            )

    if fam and prim and not supersession_emitted and fp_j >= _JACCARD_CONTRADICTION_MIN:
        out.append(
            CorpusAssessmentCandidate(
                other_document_id=other.id,
                relation=CorpusAssessmentCandidateRelation.CONTRADICTION_CANDIDATE,
                confidence="medium",
                signals=tuple(
                    sorted(
                        (
                            "same_standard_family",
                            "both_primary_standard",
                            "content_hash_differs",
                            "fingerprint_similarity_above_contradiction_threshold",
                        )
                    )
                ),
                details={
                    "fingerprint_jaccard": fp_j,
                    "title_jaccard": tj,
                },
            )
        )

    if fp_j >= _JACCARD_OVERLAP_MIN and not supersession_emitted:
        out.append(
            CorpusAssessmentCandidate(
                other_document_id=other.id,
                relation=CorpusAssessmentCandidateRelation.OVERLAP_CANDIDATE,
                confidence="low" if fp_j < 0.12 else "medium",
                signals=tuple(
                    sorted(
                        (
                            "fingerprint_text_jaccard_above_overlap_threshold",
                            "title_or_filename_or_fragment_text_overlap",
                        )
                    )
                ),
                details={"fingerprint_jaccard": fp_j, "title_jaccard": tj},
            )
        )

    # Dedup exact (other_id, relation) — last wins; build dict
    by_key: dict[tuple[str, str], CorpusAssessmentCandidate] = {}
    for c in out:
        by_key[(c.other_document_id, c.relation.value)] = c
    return list(by_key.values())


def build_document_corpus_assessment(
    store: GovernanceStore,
    *,
    project_id: str,
    subject_document_id: str,
    ingestion: DocumentIngestionService,
) -> DocumentCorpusAssessment:
    """Compute assessment for one subject document (used by tests and persistence path)."""
    index = store.try_load_document_governance_index(project_id)
    if index is None:
        raise ValueError("Governance index missing; initialize governance baseline first.")

    subject = ingestion.load_document(subject_document_id)
    sub_frags = ingestion.load_fragments(subject_document_id)

    collected: list[CorpusAssessmentCandidate] = []
    for other_id in sorted(index.by_document_id.keys()):
        if other_id == subject_document_id:
            continue
        other = ingestion.load_document(other_id)
        o_frags = ingestion.load_fragments(other_id)
        collected.extend(_collect_pair_candidates(subject, sub_frags, other, o_frags))

    # Stable ordering for serialization (lexicographic relation tie-break).
    collected.sort(key=lambda c: (c.other_document_id, c.relation.value, c.confidence, c.signals))
    now = utc_now()
    return DocumentCorpusAssessment(
        project_id=project_id,
        subject_document_id=subject_document_id,
        schema_version="g2.1",
        assessed_at=now,
        assessment_framing="candidate_assessment_not_governance_decision",
        candidates=tuple(collected),
        notes="G2 heuristic assessment only; not an active-truth or approval decision.",
    )


def assess_and_persist_document_corpus_assessment(
    store: GovernanceStore,
    ingestion: DocumentIngestionService,
    project_id: str,
    subject_document_id: str,
) -> DocumentCorpusAssessment:
    """Run G2 assessment for one subject document and persist under governance/assessments/."""
    assessment = build_document_corpus_assessment(
        store,
        project_id=project_id,
        subject_document_id=subject_document_id,
        ingestion=ingestion,
    )
    store.save_document_corpus_assessment(assessment)
    return assessment


__all__ = [
    "assess_and_persist_document_corpus_assessment",
    "build_document_corpus_assessment",
]
