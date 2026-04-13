from __future__ import annotations

from dataclasses import asdict
from typing import Any

from structural_tree_app.domain.enums import DocumentCorpusPolicy, SourceType
from structural_tree_app.domain.models import ActiveCodeContext, Assumption, Project, new_id, utc_now


def project_to_dict(project: Project) -> dict[str, Any]:
    d = asdict(project)
    d["active_code_context"] = asdict(project.active_code_context)
    d["document_corpus_policy"] = (
        project.document_corpus_policy.value
        if isinstance(project.document_corpus_policy, DocumentCorpusPolicy)
        else str(project.document_corpus_policy)
    )
    return d


def project_from_dict(data: dict[str, Any]) -> Project:
    acc = data["active_code_context"]
    active = ActiveCodeContext(
        primary_standard_family=acc["primary_standard_family"],
        active_standard_ids=list(acc.get("active_standard_ids", [])),
        complementary_standard_ids=list(acc.get("complementary_standard_ids", [])),
        allowed_document_ids=list(acc.get("allowed_document_ids", [])),
        conflict_policy=acc.get("conflict_policy", "warn_and_block_on_critical"),
    )
    legacy_auth = list(data.get("authorized_document_ids", []))
    ingested = list(data.get("ingested_document_ids", []))
    if not ingested and legacy_auth:
        ingested = list(legacy_auth)
    pol_raw = data.get("document_corpus_policy", DocumentCorpusPolicy.STRICT.value)
    try:
        corpus_policy = DocumentCorpusPolicy(str(pol_raw))
    except ValueError:
        corpus_policy = DocumentCorpusPolicy.STRICT
    return Project(
        name=data["name"],
        description=data.get("description", ""),
        language=data["language"],
        unit_system=data["unit_system"],
        active_code_context=active,
        ingested_document_ids=ingested,
        authorized_document_ids=legacy_auth,
        document_corpus_policy=corpus_policy,
        status=data.get("status", "draft"),
        id=data["id"],
        root_node_id=data.get("root_node_id"),
        branch_ids=list(data.get("branch_ids", [])),
        version_ids=list(data.get("version_ids", [])),
        head_revision_id=data.get("head_revision_id"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
    )


def assumption_from_dict(item: dict[str, Any]) -> Assumption:
    st = item["source_type"]
    if isinstance(st, str):
        st = SourceType(st)
    return Assumption(
        project_id=item["project_id"],
        node_id=item["node_id"],
        label=item["label"],
        value=item["value"],
        unit=item.get("unit"),
        source_type=st,
        confidence=float(item.get("confidence", 1.0)),
        rationale=item.get("rationale", ""),
        id=item.get("id") or new_id("asm"),
        created_at=item.get("created_at") or utc_now(),
    )


def assumptions_from_list(raw: list[dict[str, Any]]) -> list[Assumption]:
    return [assumption_from_dict(x) for x in raw]


def assumptions_to_list(items: list[Assumption]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for a in items:
        d = asdict(a)
        d["source_type"] = a.source_type.value if isinstance(a.source_type, SourceType) else str(a.source_type)
        out.append(d)
    return out
