"""G5 — Derived knowledge layer: subordinate, regenerable artifacts anchored to governed fragments."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from structural_tree_app.domain.models import utc_now

DerivedExecutionCapability = Literal["none", "deterministic_m5_hook"]
DerivedGenerationMode = Literal["deterministic_v1"]


@dataclass(frozen=True)
class SourceAnchorRef:
    """Non-authoritative pointer to governed material; citations must still use original fragments."""

    document_id: str
    fragment_id: str
    document_content_hash: str
    fragment_content_hash: str
    governance_disposition: str | None = None
    normative_classification: str | None = None


@dataclass(frozen=True)
class DocumentDigestEntry:
    """Per-document digest: navigation aid only."""

    document_id: str
    document_title: str
    standard_family: str | None
    coverage_bullets: tuple[str, ...]
    fragment_anchors: tuple[SourceAnchorRef, ...]
    governance_disposition: str | None
    governance_note: str


@dataclass(frozen=True)
class TopicDigestEntry:
    """Topic/problem-family rollup; preserves multiple source anchors."""

    topic_key: str
    summary_lines: tuple[str, ...]
    document_ids: tuple[str, ...]
    fragment_anchors: tuple[SourceAnchorRef, ...]


@dataclass(frozen=True)
class NavigationHintEntry:
    """Structured routing hint — not an answer."""

    hint_id: str
    label: str
    consult_document_ids: tuple[str, ...]
    consult_fragment_ids: tuple[str, ...]


@dataclass(frozen=True)
class FormulaRegistryEntry:
    """Named recognition of formulas/checks; not a solver."""

    entry_id: str
    label: str
    recognition_pattern_id: str
    execution_capability: DerivedExecutionCapability
    supported_by_anchors: tuple[SourceAnchorRef, ...]
    non_authoritative: bool = True


@dataclass(frozen=True)
class GovernanceSignalEntry:
    """Explicit supersession/conflict/supporting context — not flattened."""

    signal_id: str
    document_id: str
    disposition: str
    note: str
    related_document_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class DerivedArtifacts:
    document_digests: tuple[DocumentDigestEntry, ...] = ()
    topic_digests: tuple[TopicDigestEntry, ...] = ()
    navigation_hints: tuple[NavigationHintEntry, ...] = ()
    formula_registry_entries: tuple[FormulaRegistryEntry, ...] = ()
    governance_signals: tuple[GovernanceSignalEntry, ...] = ()


@dataclass(frozen=True)
class DerivedKnowledgeBundle:
    """
    Versioned bundle of derived artifacts.

    This is not a second truth source: final answers must cite governed fragments.
    """

    project_id: str
    schema_version: str = "g5.1"
    bundle_version: int = 1
    generated_at: str = field(default_factory=utc_now)
    generation_mode: DerivedGenerationMode = "deterministic_v1"
    authority_disclaimer: str = (
        "Derived artifacts are navigation and reasoning aids only. "
        "Governed source fragments remain the sole evidence authority."
    )
    source_fingerprint: str = ""
    normative_retrieval_would_block: str | None = None
    normative_retrieval_source: str = "n_a"
    governance_warnings_snapshot: tuple[str, ...] = ()
    fingerprint_inputs: dict[str, Any] = field(default_factory=dict)
    artifacts: DerivedArtifacts = field(default_factory=DerivedArtifacts)


__all__ = [
    "DerivedArtifacts",
    "DerivedGenerationMode",
    "DerivedKnowledgeBundle",
    "DocumentDigestEntry",
    "FormulaRegistryEntry",
    "GovernanceSignalEntry",
    "NavigationHintEntry",
    "SourceAnchorRef",
    "TopicDigestEntry",
]
