"""Persistence for G5 derived knowledge bundles under ``{project_id}/derived_knowledge/``."""

from __future__ import annotations

from pathlib import Path

from jsonschema.exceptions import ValidationError

from structural_tree_app.domain.derived_knowledge_codec import (
    derived_knowledge_bundle_from_dict,
    derived_knowledge_bundle_to_dict,
)
from structural_tree_app.domain.derived_knowledge_models import DerivedKnowledgeBundle
from structural_tree_app.storage.json_repository import JsonRepository
from structural_tree_app.validation.json_schema import validate_derived_knowledge_bundle_payload


class DerivedKnowledgeStoreError(Exception):
    """Invalid derived knowledge persistence."""


class DerivedKnowledgeStore:
    """Read/write ``derived_knowledge/bundle.json`` with schema validation."""

    SUBDIR = "derived_knowledge"
    BUNDLE_JSON = "bundle.json"

    def __init__(self, repository: JsonRepository) -> None:
        self._repo = repository

    def _rel(self, project_id: str) -> str:
        return str(Path(project_id, self.SUBDIR, self.BUNDLE_JSON))

    def try_load_bundle(self, project_id: str) -> DerivedKnowledgeBundle | None:
        rel = self._rel(project_id)
        if not self._repo.exists(rel):
            return None
        try:
            raw = self._repo.read(rel)
        except ValueError as e:
            raise DerivedKnowledgeStoreError(str(e)) from e
        try:
            validate_derived_knowledge_bundle_payload(raw)
        except ValidationError as e:
            raise DerivedKnowledgeStoreError(f"Invalid derived knowledge bundle: {e.message}") from e
        return derived_knowledge_bundle_from_dict(raw)

    def save_bundle(self, bundle: DerivedKnowledgeBundle) -> None:
        payload = derived_knowledge_bundle_to_dict(bundle)
        validate_derived_knowledge_bundle_payload(payload)
        self._repo.write(self._rel(bundle.project_id), payload)


__all__ = ["DerivedKnowledgeStore", "DerivedKnowledgeStoreError"]
