from fastapi import APIRouter, Request

from .. import crud
from ..analytics import dashboard_facets, dashboard_insights
from ..database import query_timeout
from ..web import Database, render
from .students import StudentFilters


router = APIRouter()
DASHBOARD_QUERY_TIMEOUT = 8


def dashboard_context(request: Request, session: Database, filters: dict):
    q, status, degree, term = (filters[name] for name in ("q", "status", "degree", "term"))
    selection = {"query": q, "status": status, "degree_id": degree, "term": term}
    parameters = {name: filters[name] for name in ("q", "status", "degree", "term")
                  if filters[name] is not None and filters[name] != ""}
    return {
        **dashboard_insights(session, **selection),
        "facets": dashboard_facets(session, **selection),
        "filters": filters,
        "dashboard_url": request.url_for("dashboard").include_query_params(**parameters),
        "students_url": request.url_for("students_list").include_query_params(**parameters),
    }


@router.get("/")
def dashboard(request: Request, session: Database, filters: StudentFilters):
    with query_timeout(session, DASHBOARD_QUERY_TIMEOUT):
        statuses = crud.status_options(session)
        selected_status = filters["status"]
        if selected_status and selected_status.upper() not in {code.upper() for code, _ in statuses}:
            statuses.append((selected_status, crud.status_label(selected_status)))
        degrees = crud.degree_options(session)
        terms = [(term, term) for term in crud.term_options(session)]
        context = dashboard_context(request, session, filters)
    return render(
        request, "dashboard.html", section="dashboard",
        degrees=degrees, terms=terms, statuses=statuses, **context,
    )


@router.get("/dashboard/insights", include_in_schema=False)
def dashboard_updates(request: Request, session: Database, filters: StudentFilters):
    with query_timeout(session, DASHBOARD_QUERY_TIMEOUT):
        context = dashboard_context(request, session, filters)
    return render(request, "dashboard_insights.html", **context)
