"""Workbench HTML routes — thin handlers; domain stays in services."""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from structural_tree_app.services.branch_comparison import BranchComparisonError, BranchComparisonService
from structural_tree_app.services.project_service import ProjectPersistenceError
from structural_tree_app.services.simple_span_m5_service import (
    METHOD_LABEL as M5_METHOD_LABEL,
    SimpleSpanM5Error,
    run_simple_span_m5_preliminary,
)
from structural_tree_app.services.simple_span_steel_workflow import (
    SimpleSpanSteelWorkflowError,
    SimpleSpanSteelWorkflowService,
)
from structural_tree_app.services.simple_span_workflow_input_store import load_simple_span_workflow_input
from structural_tree_app.services.tree_workspace import TreeWorkspace, TreeWorkspaceError

from structural_tree_app.domain.characterization_provenance import ALL_CHARACTERIZATION_PROVENANCES
from structural_tree_app.storage.tree_store import TreeStore
from structural_tree_app.workbench.config import ENV_SESSION_SECRET, ENV_WORKSPACE, get_templates_dir, get_workspace_path
from structural_tree_app.workbench.deps import SESSION_PROJECT_KEY, ProjectServiceDep, SessionProjectIdDep
from structural_tree_app.workbench.form_parsing import simple_span_input_from_form
from structural_tree_app.workbench.m5_workbench_view import (
    assumption_to_display_dict,
    calculation_to_display_dict,
    check_to_display_dict,
    list_materialized_working_branches,
    load_m5_view_for_branch,
)
from structural_tree_app.workbench.provenance_display import provenance_heading
from structural_tree_app.workbench.m6_comparison_file import load_last_comparison_bundle, save_last_comparison
from structural_tree_app.workbench.m6_workbench_view import (
    COMPARISON_FIELD_SOURCE_LEGEND,
    METRIC_PROVENANCE_LEGEND,
    pick_comparison_dict_for_template,
)
from structural_tree_app.workbench.workflow_summary import load_simple_span_workbench_snapshot
from structural_tree_app.domain.local_assist_contract import LocalAssistQuery
from structural_tree_app.services.document_service import DocumentIngestionService
from structural_tree_app.services.local_assist_orchestrator import LocalAssistOrchestrator
from structural_tree_app.workbench.u1_evidence_display import (
    u1_citation_row_badge,
    u1_readiness_hint_html,
    u1_refusal_is_governance_block,
    u1_response_authority_summary_label,
    u1_retrieval_provenance_headline,
)

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


def _redirect_workflow(
    msg: str | None = None,
    err: str | None = None,
    rev: str | None = None,
) -> RedirectResponse:
    q: list[str] = []
    if msg:
        q.append(f"msg={quote(msg)}")
    if err:
        q.append(f"err={quote(err)}")
    if rev:
        q.append(f"rev={quote(rev)}")
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
    rev: str | None = Query(None),
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
    provenance_legend = [
        {"raw": raw, "heading": provenance_heading(raw) or "—", "show_raw": True}
        for raw in ALL_CHARACTERIZATION_PROVENANCES
    ]
    materialized_branches: list[dict[str, object]] = []
    workflow_input_missing = False
    persisted_inp = load_simple_span_workflow_input(ps, project.id)
    if snapshot and persisted_inp is None:
        workflow_input_missing = True
    if snapshot:
        store = TreeStore.for_live_project(ps.repository, project.id)
        for row in list_materialized_working_branches(store, snapshot.main_branch_id):
            m5v = load_m5_view_for_branch(ps, store, project.id, row.branch_id)
            materialized_branches.append(
                {
                    "row": row,
                    "m5_view": m5v,
                    "calc_display": calculation_to_display_dict(m5v.calculation) if m5v else None,
                    "checks_display": [check_to_display_dict(c) for c in m5v.checks] if m5v else [],
                    "assumptions_display": [assumption_to_display_dict(a) for a in m5v.assumptions]
                    if m5v
                    else [],
                }
            )

    raw_bundle = load_last_comparison_bundle(ps.repository, project.id)

    revision_view_id = rev.strip() if rev and rev.strip() else None
    m6_view_mode = "live"
    branch_ids_for_m6: list[str] = []
    revisions_list: list[dict[str, str | None]] = []

    try:
        revisions_list = [
            {"id": m.id, "created_at": m.created_at, "rationale": m.rationale}
            for m in ps.list_revisions(project.id)
        ]
    except ProjectPersistenceError:
        revisions_list = []

    if revision_view_id:
        valid_ids = {r["id"] for r in revisions_list}
        if revision_view_id not in valid_ids:
            return _redirect_workflow(err=f"Unknown revision id: {revision_view_id}")
        m6_view_mode = "revision_snapshot"
        snap_store = TreeStore.for_revision_snapshot(ps.repository, project.id, revision_view_id)
        branch_ids_for_m6 = snap_store.list_branch_ids()
    else:
        live_store = TreeStore.for_live_project(ps.repository, project.id)
        branch_ids_for_m6 = live_store.list_branch_ids()

    m6_comparison_dict = pick_comparison_dict_for_template(
        raw_bundle if isinstance(raw_bundle, dict) else None,
        project_id=project.id,
        revision_id=revision_view_id,
    )

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
            "provenance_legend": provenance_legend,
            "materialized_branches": materialized_branches,
            "m5_method_label": M5_METHOD_LABEL,
            "workflow_input_missing": workflow_input_missing,
            "m6_view_mode": m6_view_mode,
            "m6_revision_id": revision_view_id,
            "branch_ids_for_m6": branch_ids_for_m6,
            "revisions_list": revisions_list,
            "m6_comparison_dict": m6_comparison_dict,
            "comparison_field_source_legend": COMPARISON_FIELD_SOURCE_LEGEND,
            "metric_provenance_legend": METRIC_PROVENANCE_LEGEND,
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


@router.post("/workbench/project/workflow/materialize")
def workflow_materialize_branch(
    request: Request,
    ps: ProjectServiceDep,
    session_pid: SessionProjectIdDep,
    alternative_id: str = Form(...),
) -> RedirectResponse:
    if not session_pid:
        return _redirect_workflow(err="No project in session")
    aid = alternative_id.strip()
    if not aid:
        return _redirect_workflow(err="alternative_id is required")
    try:
        project = ps.load_project(session_pid)
    except ProjectPersistenceError as e:
        request.session.pop(SESSION_PROJECT_KEY, None)
        return _redirect_workbench(err=str(e))
    snapshot = load_simple_span_workbench_snapshot(ps, project.id)
    if not snapshot:
        return _redirect_workflow(err="Simple-span workflow not set up for this project")
    tw = TreeWorkspace(ps, project)
    try:
        wb, _root = tw.materialize_working_branch_for_alternative(snapshot.main_branch_id, aid)
    except TreeWorkspaceError as e:
        return _redirect_workflow(err=str(e))
    return _redirect_workflow(msg=f"Materialized working branch {wb.id} for alternative {aid}")


@router.post("/workbench/project/workflow/m5-run")
def workflow_m5_run(
    request: Request,
    ps: ProjectServiceDep,
    session_pid: SessionProjectIdDep,
    working_branch_id: str = Form(...),
) -> RedirectResponse:
    if not session_pid:
        return _redirect_workflow(err="No project in session")
    wb_id = working_branch_id.strip()
    if not wb_id:
        return _redirect_workflow(err="working_branch_id is required")
    try:
        project = ps.load_project(session_pid)
    except ProjectPersistenceError as e:
        request.session.pop(SESSION_PROJECT_KEY, None)
        return _redirect_workbench(err=str(e))
    inp = load_simple_span_workflow_input(ps, project.id)
    if inp is None:
        return _redirect_workflow(
            err="Persisted SimpleSpanWorkflowInput missing (legacy project). Re-run workflow setup or restore simple_span_workflow_input.json."
        )
    snapshot = load_simple_span_workbench_snapshot(ps, project.id)
    if not snapshot:
        return _redirect_workflow(err="Simple-span workflow not set up")
    store = TreeStore.for_live_project(ps.repository, project.id)
    try:
        branch = store.load_branch(wb_id)
    except (OSError, ValueError) as e:
        return _redirect_workflow(err=f"Cannot load branch: {e}")
    if branch.project_id != project.id:
        return _redirect_workflow(err="Branch does not belong to this project")
    if branch.parent_branch_id != snapshot.main_branch_id or not branch.origin_alternative_id:
        return _redirect_workflow(err="Not a materialized simple-span working branch for this workflow")
    tw = TreeWorkspace(ps, project)
    try:
        run_simple_span_m5_preliminary(tw, wb_id, inp)
    except SimpleSpanM5Error as e:
        return _redirect_workflow(err=str(e))
    except TreeWorkspaceError as e:
        return _redirect_workflow(err=str(e))
    return _redirect_workflow(msg=f"M5 preliminary run persisted on branch {wb_id}")


@router.post("/workbench/project/workflow/compare")
async def workflow_m6_compare(
    request: Request,
    ps: ProjectServiceDep,
    session_pid: SessionProjectIdDep,
) -> RedirectResponse:
    """Read-only branch comparison — does not mutate tree state."""
    if not session_pid:
        return _redirect_workflow(err="No project in session")
    try:
        project = ps.load_project(session_pid)
    except ProjectPersistenceError as e:
        request.session.pop(SESSION_PROJECT_KEY, None)
        return _redirect_workbench(err=str(e))

    form = await request.form()
    branch_ids = [str(x).strip() for x in form.getlist("branch_ids") if str(x).strip()]
    context_revision = str(form.get("context_revision_id") or "").strip() or None

    if len(branch_ids) < 2:
        return _redirect_workflow(
            err="Select at least two branches for comparison (checkboxes).",
            rev=context_revision,
        )

    try:
        if context_revision:
            svc = BranchComparisonService.for_revision_snapshot(ps, project.id, context_revision)
        else:
            svc = BranchComparisonService.for_live(ps, project.id)
        result = svc.compare_branches(branch_ids)
    except BranchComparisonError as e:
        return _redirect_workflow(err=str(e), rev=context_revision)

    save_last_comparison(ps.repository, project.id, context_revision, result.to_dict())
    return _redirect_workflow(
        msg="Comparison computed (read-only; tree state unchanged).",
        rev=context_revision,
    )


@router.post("/workbench/project/workflow/revision-create")
def workflow_revision_create(
    request: Request,
    ps: ProjectServiceDep,
    session_pid: SessionProjectIdDep,
    rationale: str = Form(""),
) -> RedirectResponse:
    """Snapshot live workspace into a new immutable revision (Block 3 persistence)."""
    if not session_pid:
        return _redirect_workflow(err="No project in session")
    try:
        project = ps.load_project(session_pid)
    except ProjectPersistenceError as e:
        request.session.pop(SESSION_PROJECT_KEY, None)
        return _redirect_workbench(err=str(e))

    text = rationale.strip() or "Workbench snapshot"
    try:
        meta = ps.create_revision(project.id, text)
    except ProjectPersistenceError as e:
        return _redirect_workflow(err=str(e))

    return _redirect_workflow(msg=f"Created revision {meta.id} (immutable snapshot of live tree + project).")


@router.get(
    "/workbench/project/evidence",
    response_class=HTMLResponse,
    response_model=None,
)
def evidence_panel_get(
    request: Request,
    ps: ProjectServiceDep,
    session_pid: SessionProjectIdDep,
    err: str | None = Query(None),
) -> HTMLResponse | RedirectResponse:
    """U1 — evidence panel form (session project required)."""
    if not session_pid:
        return _redirect_workbench(err="Select or create a project first (project hub).")
    try:
        ps.load_project(session_pid)
    except ProjectPersistenceError as e:
        request.session.pop(SESSION_PROJECT_KEY, None)
        return _redirect_workbench(err=str(e))
    return _templates.TemplateResponse(
        request,
        "evidence_panel.html",
        {
            "assist": None,
            "err": err,
            "project_id": session_pid,
            "form_query": "",
            "form_mode": "normative_active_primary",
            "form_limit": 20,
            "form_inc_asm": True,
            "form_inc_hooks": False,
            "form_match_fam": True,
            "u1_provenance": u1_retrieval_provenance_headline,
            "u1_cite_badge": u1_citation_row_badge,
            "u1_summary_label": u1_response_authority_summary_label,
            "u1_gov_refusal": u1_refusal_is_governance_block,
            "u1_readiness_hint": lambda a, pid=session_pid: u1_readiness_hint_html(a, pid),
        },
    )


@router.post(
    "/workbench/project/evidence/query",
    response_class=HTMLResponse,
    response_model=None,
)
def evidence_panel_query(
    request: Request,
    ps: ProjectServiceDep,
    session_pid: SessionProjectIdDep,
    retrieval_query_text: str = Form(...),
    citation_authority: str = Form("normative_active_primary"),
    retrieval_limit: int = Form(20),
    include_project_assumptions: str | None = Form(None),
    include_deterministic_hooks: str | None = Form(None),
    match_project_primary_standard_family: str | None = Form(None),
) -> HTMLResponse | RedirectResponse:
    """U1 — run LocalAssistOrchestrator and render structured response."""
    if not session_pid:
        return _redirect_workbench(err="Select or create a project first (project hub).")
    try:
        ps.load_project(session_pid)
    except ProjectPersistenceError as e:
        request.session.pop(SESSION_PROJECT_KEY, None)
        return _redirect_workbench(err=str(e))

    mode = citation_authority.strip()
    if mode not in ("normative_active_primary", "approved_ingested"):
        mode = "normative_active_primary"
    lim = max(1, min(100, int(retrieval_limit)))

    q = LocalAssistQuery(
        project_id=session_pid,
        retrieval_query_text=retrieval_query_text,
        citation_authority=mode,  # type: ignore[arg-type]
        retrieval_limit=lim,
        include_project_assumptions=include_project_assumptions == "1",
        include_deterministic_hooks=include_deterministic_hooks == "1",
        match_project_primary_standard_family=match_project_primary_standard_family == "1",
    )
    assist = LocalAssistOrchestrator(ps).run(q)

    return _templates.TemplateResponse(
        request,
        "evidence_panel.html",
        {
            "assist": assist,
            "err": None,
            "project_id": session_pid,
            "form_query": retrieval_query_text,
            "form_mode": mode,
            "form_limit": lim,
            "form_inc_asm": include_project_assumptions == "1",
            "form_inc_hooks": include_deterministic_hooks == "1",
            "form_match_fam": match_project_primary_standard_family == "1",
            "u1_provenance": u1_retrieval_provenance_headline,
            "u1_cite_badge": u1_citation_row_badge,
            "u1_summary_label": u1_response_authority_summary_label,
            "u1_gov_refusal": u1_refusal_is_governance_block,
            "u1_readiness_hint": lambda a, pid=session_pid: u1_readiness_hint_html(a, pid),
        },
    )


@router.get(
    "/workbench/project/evidence/fragment/{document_id}/{fragment_id}",
    response_class=HTMLResponse,
    response_model=None,
)
def evidence_fragment_detail(
    request: Request,
    ps: ProjectServiceDep,
    session_pid: SessionProjectIdDep,
    document_id: str,
    fragment_id: str,
) -> HTMLResponse | RedirectResponse:
    """U1 — load cited fragment text from local project corpus (read-only)."""
    if not session_pid:
        return _redirect_workbench(err="Select or create a project first.")
    try:
        ps.load_project(session_pid)
    except ProjectPersistenceError as e:
        request.session.pop(SESSION_PROJECT_KEY, None)
        return _redirect_workbench(err=str(e))

    ing = DocumentIngestionService(ps, session_pid)
    try:
        doc = ing.load_document(document_id)
    except ProjectPersistenceError:
        return _templates.TemplateResponse(
            request,
            "evidence_fragment.html",
            {"document": None, "fragment": None, "error": f"Document not found: {document_id}"},
        )
    frag = None
    for f in ing.load_fragments(document_id):
        if f.id == fragment_id:
            frag = f
            break
    if frag is None:
        return _templates.TemplateResponse(
            request,
            "evidence_fragment.html",
            {"document": doc, "fragment": None, "error": f"Fragment not found: {fragment_id}"},
        )
    return _templates.TemplateResponse(
        request,
        "evidence_fragment.html",
        {"document": doc, "fragment": frag, "error": None},
    )
