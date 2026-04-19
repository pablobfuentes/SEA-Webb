"""
Persist / load ``SimpleSpanWorkflowInput`` JSON alongside the project (M3 setup).

Enables M5 and other consumers to recover exact SI inputs without re-parsing problem text.
"""

from __future__ import annotations

from dataclasses import asdict

from structural_tree_app.domain.simple_span_workflow import SimpleSpanWorkflowInput
from structural_tree_app.services.project_service import ProjectPersistenceError, ProjectService
from structural_tree_app.validation.json_schema import validate_simple_span_workflow_input_payload

SIMPLE_SPAN_WORKFLOW_INPUT_JSON = "simple_span_workflow_input.json"


def save_simple_span_workflow_input(
    project_service: ProjectService, project_id: str, inp: SimpleSpanWorkflowInput
) -> None:
    payload = asdict(inp)
    validate_simple_span_workflow_input_payload(payload)
    project_service.repository.write(
        _rel(project_id, SIMPLE_SPAN_WORKFLOW_INPUT_JSON),
        payload,
    )


def load_simple_span_workflow_input(
    project_service: ProjectService, project_id: str
) -> SimpleSpanWorkflowInput | None:
    rel = _rel(project_id, SIMPLE_SPAN_WORKFLOW_INPUT_JSON)
    if not project_service.repository.exists(rel):
        return None
    try:
        raw = project_service.repository.read(rel)
    except ValueError as e:
        raise ProjectPersistenceError(f"Invalid workflow input file: {e}") from e
    validate_simple_span_workflow_input_payload(raw)
    return SimpleSpanWorkflowInput(**raw)


def _rel(project_id: str, name: str) -> str:
    return f"{project_id}/{name}"


__all__ = [
    "SIMPLE_SPAN_WORKFLOW_INPUT_JSON",
    "load_simple_span_workflow_input",
    "save_simple_span_workflow_input",
]
