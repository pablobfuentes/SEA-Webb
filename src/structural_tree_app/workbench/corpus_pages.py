"""G1.5 / U0 — corpus bootstrap: upload, list, detail, manual disposition, projection controls."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.datastructures import UploadFile

from structural_tree_app.domain.enums import NormativeClassification
from structural_tree_app.domain.governance_enums import GovernanceRetrievalBinding
from structural_tree_app.services.corpus_bootstrap_service import (
    CorpusBootstrapError,
    apply_manual_corpus_bootstrap,
    set_projection_retrieval_binding,
    sync_legacy_allowed_documents_from_authoritative,
)
from structural_tree_app.services.corpus_readiness import evaluate_document_readiness
from structural_tree_app.services.document_service import DocumentIngestionService, IngestionResult
from structural_tree_app.services.project_service import ProjectPersistenceError, ProjectService
from structural_tree_app.workbench.config import ENV_SESSION_SECRET, ENV_WORKSPACE, get_templates_dir, get_workspace_path
from structural_tree_app.workbench.deps import SESSION_PROJECT_KEY, ProjectServiceDep, SessionProjectIdDep

router = APIRouter(tags=["ui"])
_templates = Jinja2Templates(directory=str(get_templates_dir()))


def _redirect_corpus(msg: str | None = None, err: str | None = None) -> RedirectResponse:
    q: list[str] = []
    if msg:
        q.append(f"msg={quote(msg)}")
    if err:
        q.append(f"err={quote(err)}")
    suffix = ("?" + "&".join(q)) if q else ""
    return RedirectResponse(url=f"/workbench/project/corpus{suffix}", status_code=303)


def _redirect_doc(document_id: str, msg: str | None = None, err: str | None = None) -> RedirectResponse:
    q: list[str] = []
    if msg:
        q.append(f"msg={quote(msg)}")
    if err:
        q.append(f"err={quote(err)}")
    suffix = ("?" + "&".join(q)) if q else ""
    return RedirectResponse(
        url=f"/workbench/project/corpus/document/{document_id}{suffix}",
        status_code=303,
    )


def _ingestion_status_label(status: str) -> str:
    return {
        "ingested": "ingested",
        "duplicate_skipped": "duplicate_skipped",
        "unsupported_document_for_ingestion": "unsupported_document_for_ingestion",
        "ocr_deferred": "ocr_deferred",
    }.get(status, status)


def _build_corpus_rows(
    ps: ProjectService,
    project_id: str,
) -> list[dict[str, object]]:
    """Join project ingested ids with governance records when present."""
    project = ps.load_project(project_id)
    gstore = ps.governance_store()
    index = gstore.try_load_document_governance_index(project_id)
    ing = DocumentIngestionService(ps, project_id)
    gproj = gstore.try_load_active_knowledge_projection(project_id)
    rows: list[dict[str, object]] = []
    for doc_id in project.ingested_document_ids:
        try:
            doc = ing.load_document(doc_id)
        except ProjectPersistenceError:
            continue
        rec = index.by_document_id.get(doc_id) if index else None
        n_frag = len(ing.load_fragments(doc_id))
        readiness = evaluate_document_readiness(
            document=doc,
            project=project,
            governance_record=rec,
            projection=gproj,
            governance_index=index,
        )
        rows.append(
            {
                "document_id": doc_id,
                "title": doc.title,
                "language": doc.language,
                "content_hash": doc.content_hash[:16] + "…",
                "standard_family": doc.standard_family,
                "pipeline_stage": rec.pipeline_stage.value if rec else "—",
                "disposition": rec.disposition.value if rec else "—",
                "fragment_count": n_frag,
                "readiness_label": readiness.readiness_label,
            }
        )
    return rows


@router.get("/workbench/project/corpus", response_class=HTMLResponse, response_model=None)
def corpus_bootstrap_page(
    request: Request,
    ps: ProjectServiceDep,
    session_pid: SessionProjectIdDep,
    msg: str | None = Query(None),
    err: str | None = Query(None),
) -> HTMLResponse | RedirectResponse:
    if not session_pid:
        return RedirectResponse(url="/workbench?err=" + quote("Select or create a project first."), status_code=303)
    try:
        ps.load_project(session_pid)
    except ProjectPersistenceError as e:
        request.session.pop(SESSION_PROJECT_KEY, None)
        return RedirectResponse(url="/workbench?err=" + quote(str(e)), status_code=303)

    gstore = ps.governance_store()
    proj = gstore.try_load_active_knowledge_projection(session_pid)
    rows = _build_corpus_rows(ps, session_pid)
    ws = get_workspace_path()

    return _templates.TemplateResponse(
        request,
        "corpus_bootstrap.html",
        {
            "workspace_path": str(ws),
            "workspace_env": ENV_WORKSPACE,
            "session_secret_env": ENV_SESSION_SECRET,
            "project_id": session_pid,
            "corpus_rows": rows,
            "projection": proj,
            "msg": msg,
            "err": err,
            "binding_explicit": proj.retrieval_binding == GovernanceRetrievalBinding.EXPLICIT_PROJECTION
            if proj
            else False,
        },
    )


@router.post("/workbench/project/corpus/upload")
async def corpus_upload(
    request: Request,
    ps: ProjectServiceDep,
    session_pid: SessionProjectIdDep,
) -> RedirectResponse:
    if not session_pid:
        return _redirect_corpus(err="No project in session")
    try:
        ps.load_project(session_pid)
    except ProjectPersistenceError as e:
        request.session.pop(SESSION_PROJECT_KEY, None)
        return _redirect_corpus(err=str(e))

    form = await request.form()
    raw_files = form.getlist("files")
    uploadables: list[UploadFile] = [x for x in raw_files if hasattr(x, "read")]
    if not uploadables:
        return _redirect_corpus(err="No files uploaded")

    ing = DocumentIngestionService(ps, session_pid)
    summaries: list[str] = []
    for uf in uploadables:
        if not uf.filename:
            continue
        data = await uf.read()
        suffix = Path(uf.filename).suffix or ".bin"
        fd, tmp_path = tempfile.mkstemp(suffix=suffix)
        try:
            os.write(fd, data)
            os.close(fd)
            fd = -1
            result: IngestionResult = ing.ingest_local_file(
                tmp_path,
                title=Path(uf.filename).stem,
                language="es",
            )
            st = _ingestion_status_label(result.status)
            did = result.document.id if result.document else "—"
            summaries.append(f"{uf.filename}: {st} (doc_id={did}, fragments={result.fragment_count}) — {result.message}")
        finally:
            if fd >= 0:
                try:
                    os.close(fd)
                except OSError:
                    pass
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    msg = "Upload complete. " + " | ".join(summaries) if summaries else "Nothing processed."
    return _redirect_corpus(msg=msg[:2000])


@router.get(
    "/workbench/project/corpus/document/{document_id}",
    response_class=HTMLResponse,
    response_model=None,
)
def corpus_document_detail(
    request: Request,
    ps: ProjectServiceDep,
    session_pid: SessionProjectIdDep,
    document_id: str,
    msg: str | None = Query(None),
    err: str | None = Query(None),
) -> HTMLResponse | RedirectResponse:
    if not session_pid:
        return RedirectResponse(url="/workbench?err=" + quote("No project in session."), status_code=303)
    try:
        ps.load_project(session_pid)
    except ProjectPersistenceError as e:
        request.session.pop(SESSION_PROJECT_KEY, None)
        return RedirectResponse(url="/workbench?err=" + quote(str(e)), status_code=303)

    if document_id not in ps.load_project(session_pid).ingested_document_ids:
        return _redirect_corpus(err=f"Unknown document_id: {document_id}")

    ing = DocumentIngestionService(ps, session_pid)
    doc = ing.load_document(document_id)
    frags = ing.load_fragments(document_id)
    gstore = ps.governance_store()
    idx = gstore.try_load_document_governance_index(session_pid)
    rec = idx.by_document_id.get(document_id) if idx else None
    assessment = gstore.try_load_document_corpus_assessment(session_pid, document_id)
    proj = gstore.try_load_active_knowledge_projection(session_pid)
    readiness = evaluate_document_readiness(
        document=doc,
        project=ps.load_project(session_pid),
        governance_record=rec,
        projection=proj,
        governance_index=idx,
    )
    nc_values = [e.value for e in NormativeClassification]

    return _templates.TemplateResponse(
        request,
        "corpus_document.html",
        {
            "project_id": session_pid,
            "document": doc,
            "document_id": document_id,
            "fragments": frags,
            "governance_record": rec,
            "assessment": assessment,
            "projection": proj,
            "readiness": readiness,
            "normative_classification_values": nc_values,
            "msg": msg,
            "err": err,
        },
    )


@router.post("/workbench/project/corpus/document/{document_id}/bootstrap")
def corpus_bootstrap_action(
    request: Request,
    ps: ProjectServiceDep,
    session_pid: SessionProjectIdDep,
    document_id: str,
    bootstrap_role: str = Form(...),
) -> RedirectResponse:
    if not session_pid:
        return _redirect_doc(document_id, err="No project in session")
    try:
        ps.load_project(session_pid)
    except ProjectPersistenceError as e:
        request.session.pop(SESSION_PROJECT_KEY, None)
        return _redirect_corpus(err=str(e))

    role = bootstrap_role.strip()
    if role not in ("authoritative_active", "supporting", "pending_review"):
        return _redirect_doc(document_id, err="Invalid bootstrap_role")

    try:
        apply_manual_corpus_bootstrap(
            ps.governance_store(),
            session_pid,
            document_id,
            role,  # type: ignore[arg-type]
            actor="workbench_user",
            rationale="Workbench corpus bootstrap form",
        )
    except CorpusBootstrapError as e:
        return _redirect_doc(document_id, err=str(e))

    return _redirect_doc(document_id, msg=f"Bootstrap applied: {role}")


@router.post("/workbench/project/corpus/document/{document_id}/approve")
def corpus_document_approve(
    ps: ProjectServiceDep,
    session_pid: SessionProjectIdDep,
    document_id: str,
) -> RedirectResponse:
    if not session_pid:
        return _redirect_doc(document_id, err="No project in session")
    try:
        project = ps.load_project(session_pid)
    except ProjectPersistenceError as e:
        return _redirect_corpus(err=str(e))
    if document_id not in project.ingested_document_ids:
        return _redirect_doc(document_id, err="Unknown document")
    ing = DocumentIngestionService(ps, session_pid)
    ing.approve_document(document_id)
    return _redirect_doc(document_id, msg="Document approval_status set to approved (see corpus policy for allow-list side effects).")


@router.post("/workbench/project/corpus/document/{document_id}/readiness-metadata")
def corpus_document_readiness_metadata(
    ps: ProjectServiceDep,
    session_pid: SessionProjectIdDep,
    document_id: str,
    normative_classification: str = Form(...),
    standard_family: str = Form(""),
) -> RedirectResponse:
    if not session_pid:
        return _redirect_doc(document_id, err="No project in session")
    try:
        project = ps.load_project(session_pid)
    except ProjectPersistenceError as e:
        return _redirect_corpus(err=str(e))
    if document_id not in project.ingested_document_ids:
        return _redirect_doc(document_id, err="Unknown document")
    raw_nc = normative_classification.strip()
    try:
        nc = NormativeClassification(raw_nc)
    except ValueError:
        return _redirect_doc(document_id, err=f"Invalid normative_classification: {raw_nc!r}")
    ing = DocumentIngestionService(ps, session_pid)
    doc = ing.load_document(document_id)
    doc.normative_classification = nc
    doc.standard_family = standard_family.strip() or None
    ing.save_document(doc)
    return _redirect_doc(document_id, msg="Document metadata updated (classification / standard_family).")


@router.post("/workbench/project/corpus/projection/binding")
def corpus_projection_binding(
    ps: ProjectServiceDep,
    session_pid: SessionProjectIdDep,
    retrieval_binding: str = Form(...),
) -> RedirectResponse:
    if not session_pid:
        return _redirect_corpus(err="No project in session")
    try:
        ps.load_project(session_pid)
    except ProjectPersistenceError as e:
        return _redirect_corpus(err=str(e))

    raw = retrieval_binding.strip()
    if raw == "explicit_projection":
        binding = GovernanceRetrievalBinding.EXPLICIT_PROJECTION
    elif raw == "legacy_allowed_documents":
        binding = GovernanceRetrievalBinding.LEGACY_ALLOWED_DOCUMENTS
    else:
        return _redirect_corpus(err="Invalid retrieval_binding")

    try:
        set_projection_retrieval_binding(
            ps.governance_store(),
            session_pid,
            binding,
            actor="workbench_user",
            rationale="Workbench corpus bootstrap: retrieval binding",
        )
    except CorpusBootstrapError as e:
        return _redirect_corpus(err=str(e))

    return _redirect_corpus(msg=f"Retrieval binding set to {binding.value}")


@router.post("/workbench/project/corpus/projection/sync-legacy-allowed")
def corpus_sync_legacy_allowed(
    ps: ProjectServiceDep,
    session_pid: SessionProjectIdDep,
) -> RedirectResponse:
    if not session_pid:
        return _redirect_corpus(err="No project in session")
    try:
        ps.load_project(session_pid)
    except ProjectPersistenceError as e:
        return _redirect_corpus(err=str(e))
    try:
        sync_legacy_allowed_documents_from_authoritative(ps, session_pid, actor="workbench_user")
    except CorpusBootstrapError as e:
        return _redirect_corpus(err=str(e))
    return _redirect_corpus(msg="Legacy allowed_document_ids synced from authoritative projection lists.")
