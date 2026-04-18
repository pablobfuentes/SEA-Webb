"""Workbench HTML routes — thin handlers; domain stays in services."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from structural_tree_app.services.project_service import ProjectPersistenceError
from structural_tree_app.services.simple_span_steel_workflow import (
    SimpleSpanSteelWorkflowError,
    SimpleSpanSteelWorkflowService,
)

from structural_tree_app.workbench.config import ENV_SESSION_SECRET, ENV_WORKSPACE, get_templates_dir, get_workspace_path
from structural_tree_app.workbench.deps import SESSION_PROJECT_KEY, ProjectServiceDep, SessionProjectIdDep
from structural_tree_app.workbench.form_parsing import simple_span_input_from_form
from structural_tree_app.workbench.workflow_summary import load_simple_span_workbench_snapshot

router = APIRouter(tags=["ui"])
_templates = Jinja2Templates(directory=str(get_templates_dir()))


def _redirect_workbench(msg: str | None = None, err: str | None = None) -> RedirectResponse:
    q: list[str] = []
    if msg:
        q.append(f"msg={quote(msg)}")
    if err:
        q.append(f"err={quote(err)}")
    suffix = ("?" + "&".join(q)) if q else ""
    return RedirectResponse(url=f"/workbench{suffix}", status_code=303)


def _redirect_workflow(msg: str | None = None, err: str | None = None) -> RedirectResponse:
    q: list[str] = []
    if msg:
        q.append(f"msg={quote(msg)}")
    if err:
        q.append(f"err={quote(err)}")
    suffix = ("?" + "&".join(q)) if q else ""
    return RedirectResponse(url=f"/workbench/project/workflow{suffix}", status_code=303)


@router.get("/workbench", response_class=HTMLResponse)
def workbench_hub(
    request: Request,
    ps: ProjectServiceDep,
    session_pid: SessionProjectIdDep,
    msg: str | None = Query(None),
    err: str | None = Query(None),
) -> HTMLResponse:
    current_name: str | None = None
    if session_pid:
        try:
            current_name = ps.load_project(session_pid).name
        except ProjectPersistenceError:
            request.session.pop(SESSION_PROJECT_KEY, None)
    ws = get_workspace_path()
    return _templates.TemplateResponse(
        request,
        "workbench_hub.html",
        {
            "workspace_path": str(ws),
            "workspace_env": ENV_WORKSPACE,
            "session_secret_env": ENV_SESSION_SECRET,
            "current_project_id": session_pid,
            "current_project_name": current_name,
            "msg": msg,
            "err": err,
        },
    )


@router.post("/workbench/project/create")
def project_create(
    request: Request,
    ps: ProjectServiceDep,
    name: str = Form(...),
    description: str = Form(""),
    language: str = Form("es"),
    unit_system: str = Form("SI"),
    primary_standard_family: str = Form("AISC"),
) -> RedirectResponse:
    name = name.strip()
    if not name:
        return _redirect_workbench(err="Project name is required")
    p = ps.create_project(
        name=name,
        description=description.strip(),
        language=language.strip() or "es",
        unit_system=unit_system.strip() or "SI",
        primary_standard_family=primary_standard_family.strip() or "AISC",
    )
    request.session[SESSION_PROJECT_KEY] = p.id
    return _redirect_workbench(msg=f"Created project {p.id}")


@router.post("/workbench/project/open")
def project_open(
    request: Request,
    ps: ProjectServiceDep,
    project_id: str = Form(...),
) -> RedirectResponse:
    pid = project_id.strip()
    if not pid:
        return _redirect_workbench(err="project_id is required")
    try:
        ps.load_project(pid)
    except ProjectPersistenceError as e:
        return _redirect_workbench(err=str(e))
    request.session[SESSION_PROJECT_KEY] = pid
    return _redirect_workbench(msg=f"Opened project {pid}")


@router.post("/workbench/project/close")
def project_close(request: Request) -> RedirectResponse:
    request.session.pop(SESSION_PROJECT_KEY, None)
    return _redirect_workbench(msg="Closed project (session pointer cleared)")


@router.get(
    "/workbench/project/workflow",
    response_class=HTMLResponse,
    response_model=None,
)
def workflow_simple_span_page(
    request: Request,
    ps: ProjectServiceDep,
    session_pid: SessionProjectIdDep,
    msg: str | None = Query(None),
    err: str | None = Query(None),
) -> HTMLResponse | RedirectResponse:
    if not session_pid:
        return _redirect_workbench(err="Select or create a project first")

    try:
        project = ps.load_project(session_pid)
    except ProjectPersistenceError as e:
        request.session.pop(SESSION_PROJECT_KEY, None)
        return _redirect_workbench(err=str(e))

    snapshot = load_simple_span_workbench_snapshot(ps, project.id)
    ws = get_workspace_path()
    return _templates.TemplateResponse(
        request,
        "simple_span_workflow.html",
        {
            "workspace_path": str(ws),
            "workspace_env": ENV_WORKSPACE,
            "session_secret_env": ENV_SESSION_SECRET,
            "project": project,
            "snapshot": snapshot,
            "msg": msg,
            "err": err,
        },
    )


@router.post("/workbench/project/workflow")
async def workflow_simple_span_submit(
    request: Request,
    ps: ProjectServiceDep,
    session_pid: SessionProjectIdDep,
) -> RedirectResponse:
    if not session_pid:
        return _redirect_workflow(err="No project in session")

    try:
        project = ps.load_project(session_pid)
    except ProjectPersistenceError as e:
        request.session.pop(SESSION_PROJECT_KEY, None)
        return _redirect_workbench(err=str(e))

    if project.root_node_id is not None:
        return _redirect_workflow(err="Workflow already set up for this project")

    raw = await request.form()
    try:
        inp = simple_span_input_from_form(raw)
    except (KeyError, ValueError, TypeError) as e:
        return _redirect_workflow(err=f"Invalid form: {e}")

    try:
        SimpleSpanSteelWorkflowService.setup_initial_workflow(ps, project, inp)
    except SimpleSpanSteelWorkflowError as e:
        return _redirect_workflow(err=str(e))

    return _redirect_workflow(msg="Workflow setup persisted")
