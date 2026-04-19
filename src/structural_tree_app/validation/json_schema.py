from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from structural_tree_app.paths import schemas_dir


@lru_cache
def _validator(schema_name: str) -> Draft202012Validator:
    path = schemas_dir() / schema_name
    with path.open(encoding="utf-8") as f:
        schema = json.load(f)
    return Draft202012Validator(schema)


def validate_project_payload(data: dict[str, Any]) -> None:
    _validator("project.schema.json").validate(data)


def validate_revision_meta_payload(data: dict[str, Any]) -> None:
    _validator("revision.schema.json").validate(data)


def validate_assumption_record(data: dict[str, Any]) -> None:
    _validator("assumption_record.schema.json").validate(data)


def validate_assumptions_list_payload(data: list[Any]) -> None:
    if not isinstance(data, list):
        raise ValidationError("Assumptions root must be an array")
    v = _validator("assumption_record.schema.json")
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValidationError(f"Assumptions[{i}] must be an object")
        v.validate(item)


def validate_branch_payload(data: dict[str, Any]) -> None:
    _validator("branch.schema.json").validate(data)


def validate_node_payload(data: dict[str, Any]) -> None:
    _validator("node.schema.json").validate(data)


def validate_decision_payload(data: dict[str, Any]) -> None:
    _validator("decision.schema.json").validate(data)


def validate_alternative_payload(data: dict[str, Any]) -> None:
    _validator("alternative.schema.json").validate(data)


def validate_calculation_payload(data: dict[str, Any]) -> None:
    _validator("calculation.schema.json").validate(data)


def validate_check_payload(data: dict[str, Any]) -> None:
    _validator("check.schema.json").validate(data)


def validate_reference_payload(data: dict[str, Any]) -> None:
    _validator("reference.schema.json").validate(data)


def validate_simple_span_workflow_input_payload(data: dict[str, Any]) -> None:
    _validator("simple_span_workflow_input.schema.json").validate(data)


def validate_document_payload(data: dict[str, Any]) -> None:
    _validator("document.schema.json").validate(data)


def validate_document_fragment_payload(data: dict[str, Any]) -> None:
    _validator("document_fragment.schema.json").validate(data)


def validate_active_knowledge_projection_payload(data: dict[str, Any]) -> None:
    _validator("active_knowledge_projection.schema.json").validate(data)


def validate_document_governance_record_payload(data: dict[str, Any]) -> None:
    _validator("document_governance_record.schema.json").validate(data)


def validate_document_governance_index_payload(data: dict[str, Any]) -> None:
    _validator("document_governance_index.schema.json").validate(data)


def validate_governance_event_payload(data: dict[str, Any]) -> None:
    _validator("governance_event.schema.json").validate(data)


def validate_governance_event_log_payload(data: dict[str, Any]) -> None:
    _validator("governance_event_log.schema.json").validate(data)


def validate_document_corpus_assessment_payload(data: dict[str, Any]) -> None:
    _validator("document_corpus_assessment.schema.json").validate(data)


def validate_truth_proposal_payload(data: dict[str, Any]) -> None:
    _validator("truth_proposal.schema.json").validate(data)


def validate_derived_knowledge_bundle_payload(data: dict[str, Any]) -> None:
    _validator("derived_knowledge_bundle.schema.json").validate(data)


def validate_reasoning_bridge_result_payload(data: dict[str, Any]) -> None:
    _validator("reasoning_bridge_result.schema.json").validate(data)


__all__ = [
    "ValidationError",
    "validate_active_knowledge_projection_payload",
    "validate_alternative_payload",
    "validate_calculation_payload",
    "validate_check_payload",
    "validate_document_fragment_payload",
    "validate_document_payload",
    "validate_document_corpus_assessment_payload",
    "validate_document_governance_index_payload",
    "validate_derived_knowledge_bundle_payload",
    "validate_document_governance_record_payload",
    "validate_assumption_record",
    "validate_assumptions_list_payload",
    "validate_branch_payload",
    "validate_decision_payload",
    "validate_governance_event_log_payload",
    "validate_governance_event_payload",
    "validate_node_payload",
    "validate_project_payload",
    "validate_reference_payload",
    "validate_reasoning_bridge_result_payload",
    "validate_revision_meta_payload",
    "validate_simple_span_workflow_input_payload",
    "validate_truth_proposal_payload",
]
