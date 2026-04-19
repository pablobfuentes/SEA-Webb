"""Deterministic JSON codecs for derived knowledge bundles (G5)."""

from __future__ import annotations

from typing import Any

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


def _anchor_to_dict(a: SourceAnchorRef) -> dict[str, Any]:
    return {
        "document_id": a.document_id,
        "fragment_id": a.fragment_id,
        "document_content_hash": a.document_content_hash,
        "fragment_content_hash": a.fragment_content_hash,
        "governance_disposition": a.governance_disposition,
        "normative_classification": a.normative_classification,
    }


def _anchor_from_dict(d: dict[str, Any]) -> SourceAnchorRef:
    return SourceAnchorRef(
        document_id=d["document_id"],
        fragment_id=d["fragment_id"],
        document_content_hash=d["document_content_hash"],
        fragment_content_hash=d["fragment_content_hash"],
        governance_disposition=d.get("governance_disposition"),
        normative_classification=d.get("normative_classification"),
    )


def derived_knowledge_bundle_to_dict(b: DerivedKnowledgeBundle) -> dict[str, Any]:
    arts = b.artifacts
    return {
        "authority_disclaimer": b.authority_disclaimer,
        "artifacts": {
            "document_digests": [_doc_digest_to_dict(x) for x in arts.document_digests],
            "formula_registry_entries": [_formula_to_dict(x) for x in arts.formula_registry_entries],
            "governance_signals": [_gov_sig_to_dict(x) for x in arts.governance_signals],
            "navigation_hints": [_nav_to_dict(x) for x in arts.navigation_hints],
            "topic_digests": [_topic_to_dict(x) for x in arts.topic_digests],
        },
        "bundle_version": b.bundle_version,
        "fingerprint_inputs": b.fingerprint_inputs,
        "generated_at": b.generated_at,
        "generation_mode": b.generation_mode,
        "governance_warnings_snapshot": list(b.governance_warnings_snapshot),
        "normative_retrieval_source": b.normative_retrieval_source,
        "normative_retrieval_would_block": b.normative_retrieval_would_block,
        "project_id": b.project_id,
        "schema_version": b.schema_version,
        "source_fingerprint": b.source_fingerprint,
    }


def derived_knowledge_bundle_from_dict(d: dict[str, Any]) -> DerivedKnowledgeBundle:
    raw_a = d.get("artifacts") or {}
    doc_digests = tuple(
        _doc_digest_from_dict(x) for x in raw_a.get("document_digests", []) if isinstance(x, dict)
    )
    topic_digests = tuple(
        _topic_from_dict(x) for x in raw_a.get("topic_digests", []) if isinstance(x, dict)
    )
    nav = tuple(_nav_from_dict(x) for x in raw_a.get("navigation_hints", []) if isinstance(x, dict))
    formulas = tuple(
        _formula_from_dict(x) for x in raw_a.get("formula_registry_entries", []) if isinstance(x, dict)
    )
    gov = tuple(
        _gov_sig_from_dict(x) for x in raw_a.get("governance_signals", []) if isinstance(x, dict)
    )
    arts = DerivedArtifacts(
        document_digests=doc_digests,
        topic_digests=topic_digests,
        navigation_hints=nav,
        formula_registry_entries=formulas,
        governance_signals=gov,
    )
    return DerivedKnowledgeBundle(
        project_id=d["project_id"],
        schema_version=d.get("schema_version", "g5.1"),
        bundle_version=int(d.get("bundle_version", 1)),
        generated_at=d.get("generated_at", ""),
        generation_mode=d.get("generation_mode", "deterministic_v1"),
        authority_disclaimer=d.get(
            "authority_disclaimer",
            (
                "Derived artifacts are navigation and reasoning aids only. "
                "Governed source fragments remain the sole evidence authority."
            ),
        ),
        source_fingerprint=d.get("source_fingerprint", ""),
        normative_retrieval_would_block=d.get("normative_retrieval_would_block"),
        normative_retrieval_source=d.get("normative_retrieval_source", "n_a"),
        governance_warnings_snapshot=tuple(d.get("governance_warnings_snapshot", []) or []),
        fingerprint_inputs=dict(d.get("fingerprint_inputs") or {}),
        artifacts=arts,
    )


def _doc_digest_to_dict(e: DocumentDigestEntry) -> dict[str, Any]:
    return {
        "coverage_bullets": list(e.coverage_bullets),
        "document_id": e.document_id,
        "document_title": e.document_title,
        "fragment_anchors": [_anchor_to_dict(a) for a in e.fragment_anchors],
        "governance_disposition": e.governance_disposition,
        "governance_note": e.governance_note,
        "standard_family": e.standard_family,
    }


def _doc_digest_from_dict(d: dict[str, Any]) -> DocumentDigestEntry:
    anchors = tuple(_anchor_from_dict(x) for x in d.get("fragment_anchors", []) if isinstance(x, dict))
    return DocumentDigestEntry(
        document_id=d["document_id"],
        document_title=d.get("document_title", ""),
        standard_family=d.get("standard_family"),
        coverage_bullets=tuple(d.get("coverage_bullets", []) or []),
        fragment_anchors=anchors,
        governance_disposition=d.get("governance_disposition"),
        governance_note=d.get("governance_note", ""),
    )


def _topic_to_dict(e: TopicDigestEntry) -> dict[str, Any]:
    return {
        "document_ids": list(e.document_ids),
        "fragment_anchors": [_anchor_to_dict(a) for a in e.fragment_anchors],
        "summary_lines": list(e.summary_lines),
        "topic_key": e.topic_key,
    }


def _topic_from_dict(d: dict[str, Any]) -> TopicDigestEntry:
    anchors = tuple(_anchor_from_dict(x) for x in d.get("fragment_anchors", []) if isinstance(x, dict))
    return TopicDigestEntry(
        topic_key=d["topic_key"],
        summary_lines=tuple(d.get("summary_lines", []) or []),
        document_ids=tuple(d.get("document_ids", []) or []),
        fragment_anchors=anchors,
    )


def _nav_to_dict(e: NavigationHintEntry) -> dict[str, Any]:
    return {
        "consult_document_ids": list(e.consult_document_ids),
        "consult_fragment_ids": list(e.consult_fragment_ids),
        "hint_id": e.hint_id,
        "label": e.label,
    }


def _nav_from_dict(d: dict[str, Any]) -> NavigationHintEntry:
    return NavigationHintEntry(
        hint_id=d["hint_id"],
        label=d.get("label", ""),
        consult_document_ids=tuple(d.get("consult_document_ids", []) or []),
        consult_fragment_ids=tuple(d.get("consult_fragment_ids", []) or []),
    )


def _formula_to_dict(e: FormulaRegistryEntry) -> dict[str, Any]:
    return {
        "entry_id": e.entry_id,
        "execution_capability": e.execution_capability,
        "label": e.label,
        "non_authoritative": e.non_authoritative,
        "recognition_pattern_id": e.recognition_pattern_id,
        "supported_by_anchors": [_anchor_to_dict(a) for a in e.supported_by_anchors],
    }


def _formula_from_dict(d: dict[str, Any]) -> FormulaRegistryEntry:
    anchors = tuple(
        _anchor_from_dict(x) for x in d.get("supported_by_anchors", []) if isinstance(x, dict)
    )
    return FormulaRegistryEntry(
        entry_id=d["entry_id"],
        label=d.get("label", ""),
        recognition_pattern_id=d.get("recognition_pattern_id", ""),
        execution_capability=d.get("execution_capability", "none"),
        supported_by_anchors=anchors,
        non_authoritative=bool(d.get("non_authoritative", True)),
    )


def _gov_sig_to_dict(e: GovernanceSignalEntry) -> dict[str, Any]:
    return {
        "disposition": e.disposition,
        "document_id": e.document_id,
        "note": e.note,
        "related_document_ids": list(e.related_document_ids),
        "signal_id": e.signal_id,
    }


def _gov_sig_from_dict(d: dict[str, Any]) -> GovernanceSignalEntry:
    return GovernanceSignalEntry(
        signal_id=d["signal_id"],
        document_id=d["document_id"],
        disposition=d.get("disposition", ""),
        note=d.get("note", ""),
        related_document_ids=tuple(d.get("related_document_ids", []) or []),
    )


__all__ = [
    "derived_knowledge_bundle_from_dict",
    "derived_knowledge_bundle_to_dict",
]
