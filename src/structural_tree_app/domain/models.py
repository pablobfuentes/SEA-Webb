from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from .enums import (
    AuthorityLevel,
    BranchState,
    DocumentApprovalStatus,
    DocumentCorpusPolicy,
    NormativeClassification,
    NodeState,
    NodeType,
    SourceType,
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


@dataclass
class ActiveCodeContext:
    primary_standard_family: str
    active_standard_ids: list[str] = field(default_factory=list)
    complementary_standard_ids: list[str] = field(default_factory=list)
    allowed_document_ids: list[str] = field(default_factory=list)
    conflict_policy: str = "warn_and_block_on_critical"


@dataclass
class Project:
    name: str
    description: str
    language: str
    unit_system: str
    active_code_context: ActiveCodeContext
    """Documents that completed ingestion (catalog); not necessarily normative."""
    ingested_document_ids: list[str] = field(default_factory=list)
    """Legacy catalog field; kept for migration. Prefer `ingested_document_ids`."""
    authorized_document_ids: list[str] = field(default_factory=list)
    document_corpus_policy: DocumentCorpusPolicy = DocumentCorpusPolicy.STRICT
    status: str = "draft"
    id: str = field(default_factory=lambda: new_id("proj"))
    root_node_id: str | None = None
    branch_ids: list[str] = field(default_factory=list)
    version_ids: list[str] = field(default_factory=list)
    head_revision_id: str | None = None
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)


@dataclass
class RevisionMetadata:
    """Points to an on-disk snapshot; separate id from `Project.id`."""

    id: str
    project_id: str
    created_at: str
    rationale: str
    parent_revision_id: str | None = None


@dataclass
class Document:
    title: str
    author: str
    edition: str
    version_label: str
    publication_year: int | None
    document_type: str
    authority_level: AuthorityLevel
    topics: list[str]
    language: str
    file_path: str
    content_hash: str
    """SHA-256 hex of raw file bytes (reproducible material identity for dedup/traceability)."""
    approval_status: DocumentApprovalStatus = DocumentApprovalStatus.PENDING
    normative_classification: NormativeClassification = NormativeClassification.UNKNOWN
    discipline: str | None = None
    standard_family: str | None = None
    """When unknown, leave None; do not infer from project primary standard."""
    id: str = field(default_factory=lambda: new_id("doc"))
    created_at: str = field(default_factory=utc_now)


@dataclass
class DocumentFragment:
    document_id: str
    chapter: str
    section: str
    page_start: int | None  # PDF: 1-based physical page index (first page of file = 1); None for non-paged text
    page_end: int | None
    fragment_type: str
    topic_tags: list[str]
    authority_level: AuthorityLevel
    text: str
    chunk_index: int = 0
    char_start: int | None = None
    char_end: int | None = None
    fragment_content_hash: str = ""
    """SHA-256 hex of normalized fragment text (chunk identity for citation)."""
    material_content_hash: str = ""
    """Same as parent document `content_hash` when available (byte-identity traceability)."""
    ingestion_method: str = "file"
    document_approval_status: DocumentApprovalStatus = DocumentApprovalStatus.PENDING
    document_normative_classification: NormativeClassification = NormativeClassification.UNKNOWN
    id: str = field(default_factory=lambda: new_id("frag"))
    sibling_fragment_ids: list[str] = field(default_factory=list)
    linked_fragment_ids: list[str] = field(default_factory=list)


@dataclass
class Branch:
    project_id: str
    title: str
    description: str
    origin_decision_node_id: str | None
    origin_alternative_id: str | None = None
    root_node_id: str | None = None
    state: BranchState = BranchState.PENDING
    parent_branch_id: str | None = None
    cloned_from_branch_id: str | None = None
    reactivated_from_branch_id: str | None = None
    comparison_tags: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: new_id("branch"))
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)


@dataclass
class Node:
    project_id: str
    branch_id: str
    node_type: NodeType
    title: str
    description: str
    parent_node_id: str | None = None
    state: NodeState = NodeState.OPEN
    order_index: int = 0
    depth: int = 0
    id: str = field(default_factory=lambda: new_id("node"))
    child_node_ids: list[str] = field(default_factory=list)
    linked_reference_ids: list[str] = field(default_factory=list)
    linked_calculation_ids: list[str] = field(default_factory=list)
    linked_assumption_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)


@dataclass
class Alternative:
    # M4+: characterization_items holds structured claims; legacy pros/cons may remain empty.
    decision_id: str
    title: str
    description: str
    catalog_key: str = ""
    characterization_items: list[dict[str, Any]] = field(default_factory=list)
    pros: list[str] = field(default_factory=list)
    cons: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    next_expected_decisions: list[str] = field(default_factory=list)
    suggested: bool = False
    suggestion_rank: int | None = None
    suggestion_score: float | None = None
    suggestion_provenance: str = "workflow_heuristic"
    status: str = "candidate"
    reactivatable: bool = True
    id: str = field(default_factory=lambda: new_id("alt"))


@dataclass
class Decision:
    project_id: str
    decision_node_id: str
    prompt: str
    criterion_ids: list[str] = field(default_factory=list)
    alternative_ids: list[str] = field(default_factory=list)
    selected_alternative_id: str | None = None
    status: str = "open"
    rationale: str = ""
    id: str = field(default_factory=lambda: new_id("dec"))
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)


@dataclass
class Assumption:
    project_id: str
    node_id: str
    label: str
    value: Any
    unit: str | None
    source_type: SourceType
    confidence: float = 1.0
    rationale: str = ""
    id: str = field(default_factory=lambda: new_id("asm"))
    created_at: str = field(default_factory=utc_now)


@dataclass
class Calculation:
    project_id: str
    node_id: str
    objective: str
    method_label: str
    formula_text: str
    inputs: dict[str, Any]
    substitutions: dict[str, Any]
    result: dict[str, Any]
    formula_id: str | None = None
    dimensional_validation: dict[str, Any] | None = None
    reference_ids: list[str] = field(default_factory=list)
    status: str = "draft"
    id: str = field(default_factory=lambda: new_id("calc"))
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)


@dataclass
class Check:
    project_id: str
    node_id: str
    calculation_id: str
    check_type: str
    demand: dict[str, Any]
    capacity: dict[str, Any]
    utilization_ratio: float
    status: str
    message: str
    reference_ids: list[str] = field(default_factory=list)
    id: str = field(default_factory=lambda: new_id("chk"))


@dataclass
class Reference:
    project_id: str
    document_id: str
    fragment_id: str
    usage_type: str
    citation_short: str
    citation_long: str
    quoted_context: str
    id: str = field(default_factory=lambda: new_id("ref"))


@dataclass
class Report:
    project_id: str
    title: str
    report_type: str
    included_branch_ids: list[str]
    included_node_ids: list[str]
    included_calculation_ids: list[str]
    included_reference_ids: list[str]
    export_path: str
    version_id: str | None = None
    id: str = field(default_factory=lambda: new_id("report"))
    created_at: str = field(default_factory=utc_now)


@dataclass
class VersionRecord:
    entity_type: str
    entity_id: str
    project_id: str
    change_type: str
    snapshot_path: str
    rationale: str
    id: str = field(default_factory=lambda: new_id("ver"))
    created_at: str = field(default_factory=utc_now)
