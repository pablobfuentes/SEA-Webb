from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from jsonschema.exceptions import ValidationError

from structural_tree_app.domain.enums import DocumentCorpusPolicy
from structural_tree_app.domain.models import ActiveCodeContext, Project, RevisionMetadata, new_id, utc_now
from structural_tree_app.domain.project_codec import (
    assumptions_from_list,
    assumptions_to_list,
    project_from_dict,
    project_to_dict,
)
from structural_tree_app.storage.json_repository import JsonRepository
from structural_tree_app.storage.tree_store import TreeStore, copy_tree_directory
from structural_tree_app.validation.json_schema import (
    validate_assumptions_list_payload,
    validate_project_payload,
    validate_revision_meta_payload,
)


class ProjectPersistenceError(Exception):
    """Raised when project files are missing, invalid, or fail validation."""


def _ensure_project_json_migrations(raw: dict[str, Any]) -> None:
    if "ingested_document_ids" not in raw:
        raw["ingested_document_ids"] = list(raw.get("authorized_document_ids", []))
    if "document_corpus_policy" not in raw:
        raw["document_corpus_policy"] = DocumentCorpusPolicy.STRICT.value


@dataclass(frozen=True)
class RevisionBundle:
    """Revision state reconstructed only from snapshot files (no live project leakage)."""

    project: Project
    assumptions: list[Any]
    tree_store: TreeStore


class ProjectService:
    """Create, load, save, and revision local projects under a single workspace root."""

    PROJECT_JSON = "project.json"
    ASSUMPTIONS_JSON = "assumptions.json"
    ASSUMPTIONS_SNAPSHOT_JSON = "assumptions_snapshot.json"

    def __init__(self, workspace_path: str | Path) -> None:
        self.repository = JsonRepository(workspace_path)

    def _project_dir(self, project_id: str) -> Path:
        return self.repository.base_path / project_id

    def _rel(self, project_id: str, *parts: str) -> str:
        return str(Path(project_id, *parts))

    def _ensure_layout(self, project_id: str) -> None:
        root = self._project_dir(project_id)
        for sub in ("revisions", "tree", "documents", "exports"):
            (root / sub).mkdir(parents=True, exist_ok=True)
        for sub in ("branches", "nodes", "decisions", "alternatives", "calculations", "checks", "references"):
            (root / "tree" / sub).mkdir(parents=True, exist_ok=True)

    def create_project(
        self,
        name: str,
        description: str,
        language: str,
        unit_system: str,
        primary_standard_family: str,
    ) -> Project:
        project = Project(
            name=name,
            description=description,
            language=language,
            unit_system=unit_system,
            active_code_context=ActiveCodeContext(primary_standard_family=primary_standard_family),
            ingested_document_ids=[],
            document_corpus_policy=DocumentCorpusPolicy.STRICT,
        )
        self._ensure_layout(project.id)
        self._write_assumptions(project.id, [])
        rev_id = new_id("rev")
        project.version_ids = [rev_id]
        project.head_revision_id = rev_id
        now = utc_now()
        project.updated_at = now
        self._write_project_json(project)
        self._write_revision_snapshot(
            project.id,
            rev_id,
            project,
            rationale="initial",
            parent_revision_id=None,
            created_at=now,
        )
        return project

    def load_project(self, project_id: str) -> Project:
        rel = self._rel(project_id, self.PROJECT_JSON)
        if not self.repository.exists(rel):
            raise ProjectPersistenceError(f"Missing project file: {rel}")
        try:
            raw = self.repository.read(rel)
        except ValueError as e:
            raise ProjectPersistenceError(str(e)) from e
        _ensure_project_json_migrations(raw)
        try:
            validate_project_payload(raw)
        except ValidationError as e:
            raise ProjectPersistenceError(f"Invalid project.json: {e.message}") from e
        return project_from_dict(raw)

    def load_assumptions(self, project_id: str) -> list:
        rel = self._rel(project_id, self.ASSUMPTIONS_JSON)
        if not self.repository.exists(rel):
            return []
        try:
            data = self.repository.read_json(rel)
        except ValueError as e:
            raise ProjectPersistenceError(str(e)) from e
        try:
            validate_assumptions_list_payload(data)
        except ValidationError as e:
            raise ProjectPersistenceError(f"Invalid assumptions.json: {e.message}") from e
        return assumptions_from_list(data)

    def save_project(self, project: Project) -> None:
        project.updated_at = utc_now()
        self._write_project_json(project)

    def save_assumptions(self, project_id: str, assumptions: list) -> None:
        self._write_assumptions(project_id, assumptions)

    def _write_project_json(self, project: Project) -> None:
        payload = project_to_dict(project)
        try:
            validate_project_payload(payload)
        except ValidationError as e:
            raise ProjectPersistenceError(f"Project failed schema validation: {e.message}") from e
        self.repository.write(self._rel(project.id, self.PROJECT_JSON), payload)

    def _write_assumptions(self, project_id: str, assumptions: list) -> None:
        payload = assumptions_to_list(assumptions)
        try:
            validate_assumptions_list_payload(payload)
        except ValidationError as e:
            raise ProjectPersistenceError(f"Assumptions failed schema validation: {e.message}") from e
        self.repository.write(self._rel(project_id, self.ASSUMPTIONS_JSON), payload)

    def _snapshot_assumptions_payload(self, project_id: str) -> list:
        """Current assumptions as validated JSON-serializable list."""
        rel = self._rel(project_id, self.ASSUMPTIONS_JSON)
        if not self.repository.exists(rel):
            return []
        data = self.repository.read_json(rel)
        validate_assumptions_list_payload(data)
        return data

    def _write_revision_snapshot(
        self,
        project_id: str,
        revision_id: str,
        project: Project,
        rationale: str,
        parent_revision_id: str | None,
        created_at: str | None = None,
    ) -> None:
        rev_meta = self._project_dir(project_id) / "revisions" / revision_id / "meta.json"
        if rev_meta.exists():
            raise ProjectPersistenceError(
                f"Revision {revision_id} already exists; revisions are write-once (immutable)."
            )
        ts = created_at or utc_now()
        meta = RevisionMetadata(
            id=revision_id,
            project_id=project_id,
            created_at=ts,
            rationale=rationale,
            parent_revision_id=parent_revision_id,
        )
        meta_dict = asdict(meta)
        validate_revision_meta_payload(meta_dict)
        self.repository.write(
            self._rel(project_id, "revisions", revision_id, "meta.json"),
            meta_dict,
        )
        snap = project_to_dict(project)
        validate_project_payload(snap)
        self.repository.write(
            self._rel(project_id, "revisions", revision_id, "project_snapshot.json"),
            snap,
        )
        assumptions_payload = self._snapshot_assumptions_payload(project_id)
        self.repository.write(
            self._rel(project_id, "revisions", revision_id, self.ASSUMPTIONS_SNAPSHOT_JSON),
            assumptions_payload,
        )
        src_tree = self._project_dir(project_id) / "tree"
        dst_tree = self._project_dir(project_id) / "revisions" / revision_id / "tree"
        copy_tree_directory(src_tree, dst_tree)

    def create_revision(self, project_id: str, rationale: str) -> RevisionMetadata:
        project = self.load_project(project_id)
        parent = project.head_revision_id
        rev_id = new_id("rev")
        now = utc_now()
        project.version_ids = [*project.version_ids, rev_id]
        project.head_revision_id = rev_id
        project.updated_at = now
        self._write_revision_snapshot(
            project_id, rev_id, project, rationale=rationale, parent_revision_id=parent, created_at=now
        )
        self._write_project_json(project)
        return RevisionMetadata(
            id=rev_id,
            project_id=project_id,
            created_at=now,
            rationale=rationale,
            parent_revision_id=parent,
        )

    def list_revisions(self, project_id: str) -> list[RevisionMetadata]:
        project = self.load_project(project_id)
        out: list[RevisionMetadata] = []
        for rev_id in project.version_ids:
            rel = self._rel(project_id, "revisions", rev_id, "meta.json")
            if not self.repository.exists(rel):
                raise ProjectPersistenceError(f"Missing revision meta: {rel}")
            raw = self.repository.read(rel)
            validate_revision_meta_payload(raw)
            out.append(
                RevisionMetadata(
                    id=raw["id"],
                    project_id=raw["project_id"],
                    created_at=raw["created_at"],
                    rationale=raw["rationale"],
                    parent_revision_id=raw.get("parent_revision_id"),
                )
            )
        return out

    def load_revision_snapshot_project(self, project_id: str, revision_id: str) -> Project:
        rel = self._rel(project_id, "revisions", revision_id, "project_snapshot.json")
        if not self.repository.exists(rel):
            raise ProjectPersistenceError(f"Missing snapshot: {rel}")
        raw = self.repository.read(rel)
        _ensure_project_json_migrations(raw)
        validate_project_payload(raw)
        return project_from_dict(raw)

    def load_revision_snapshot_assumptions(self, project_id: str, revision_id: str) -> list:
        rel = self._rel(project_id, "revisions", revision_id, self.ASSUMPTIONS_SNAPSHOT_JSON)
        if not self.repository.exists(rel):
            raise ProjectPersistenceError(f"Missing assumptions snapshot: {rel}")
        data = self.repository.read_json(rel)
        validate_assumptions_list_payload(data)
        return assumptions_from_list(data)

    def load_revision_bundle(self, project_id: str, revision_id: str) -> RevisionBundle:
        """Load project + assumptions + tree **only** from the revision snapshot (isolated from live files)."""
        project = self.load_revision_snapshot_project(project_id, revision_id)
        assumptions = self.load_revision_snapshot_assumptions(project_id, revision_id)
        tree_store = TreeStore.for_revision_snapshot(self.repository, project_id, revision_id)
        return RevisionBundle(project=project, assumptions=assumptions, tree_store=tree_store)
