"""Integrated case flow — lightweight query handoff across chat / evidence / canvas / workflow.

No new product surfaces: session pointer + optional ``?q=`` URL prefill only.
Governed retrieval behavior is unchanged; this module only affects navigation defaults.
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import Request

from structural_tree_app.workbench.deps import SESSION_LAST_ASSIST_QUERY_KEY, SESSION_PROJECT_KEY

MAX_ASSIST_QUERY_LEN = 8000


def surface_href(path: str, query_text: str) -> str:
    """Append ``?q=…`` when ``query_text`` is non-empty (for cross-surface continuity)."""
    t = (query_text or "").strip()
    if not t:
        return path
    return f"{path}?q={quote(t)}"


def build_case_nav(query_text: str) -> dict[str, str | bool]:
    """Template-ready navigation targets for primary + secondary surfaces."""
    q = (query_text or "").strip()
    return {
        "chat": surface_href("/workbench/project/chat", q),
        "evidence": surface_href("/workbench/project/evidence", q),
        "canvas": surface_href("/workbench/project/canvas", q),
        "workflow": surface_href("/workbench/project/workflow", q),
        "hub": "/workbench",
        "corpus": "/workbench/project/corpus",
        "query_nonempty": bool(q),
    }


def store_last_assist_query(request: Request, text: str) -> None:
    """Persist last assist query for handoff (truncated)."""
    t = (text or "").strip()
    if t:
        request.session[SESSION_LAST_ASSIST_QUERY_KEY] = t[:MAX_ASSIST_QUERY_LEN]


def resolve_prefill_query(request: Request, q_param: str | None) -> str:
    """Explicit ``q`` wins; else last stored assist query for this session."""
    qp = (q_param or "").strip()
    if qp:
        return qp[:MAX_ASSIST_QUERY_LEN]
    raw = request.session.get(SESSION_LAST_ASSIST_QUERY_KEY)
    return raw if isinstance(raw, str) else ""


def sync_session_query_from_explicit_url(request: Request, q_param: str | None) -> None:
    """When user lands with ``?q=``, align session handoff with that string."""
    qp = (q_param or "").strip()
    if qp:
        store_last_assist_query(request, qp)


def invalidate_session_project(request: Request) -> None:
    """Clear project pointer and case query (invalid project or explicit close)."""
    request.session.pop(SESSION_PROJECT_KEY, None)
    request.session.pop(SESSION_LAST_ASSIST_QUERY_KEY, None)


def bind_new_session_project(request: Request, project_id: str) -> None:
    """Set active project and reset assist-query handoff (new / switched project)."""
    request.session[SESSION_PROJECT_KEY] = project_id
    request.session.pop(SESSION_LAST_ASSIST_QUERY_KEY, None)
