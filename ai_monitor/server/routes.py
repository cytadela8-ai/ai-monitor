from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict

from ai_monitor.auth import (
    clear_admin_session,
    has_admin_session,
    require_admin_session,
    sign_in_admin_session,
)
from ai_monitor.db.queries import (
    fetch_daily_heatmap,
    fetch_latest_refresh_run,
    fetch_machine_options,
    fetch_metrics_rows,
    fetch_ranked_projects,
    fetch_summary_metrics,
)

router = APIRouter()


class LoginRequest(BaseModel):
    admin_key: str

    model_config = ConfigDict(extra="forbid")


@router.get("/api/metrics")
def get_metrics(
    request: Request,
    period: str = Query(default="day"),
    machine: str | None = Query(default=None),
    project: str | None = Query(default=None),
    provider: str | None = Query(default=None),
) -> dict[str, object]:
    require_admin_session(request)
    config = request.app.state.config
    last_refresh = fetch_latest_refresh_run(config.database_path, machine=machine)
    rows = fetch_metrics_rows(
        database_path=config.database_path,
        period=period,
        machine=machine,
        project=project,
        provider=provider,
    )
    summary = fetch_summary_metrics(
        database_path=config.database_path,
        machine=machine,
        project=project,
        provider=provider,
    )
    heatmap_days = fetch_daily_heatmap(
        database_path=config.database_path,
        machine=machine,
        project=project,
        provider=provider,
        days=182,
    )
    projects = fetch_ranked_projects(
        database_path=config.database_path,
        period=period,
        machine=machine,
        provider=provider,
    )
    machines = fetch_machine_options(config.database_path)
    return {
        "period": period,
        "machine": machine,
        "rows": [row.__dict__ for row in rows],
        "summary": summary.__dict__,
        "heatmap_days": [day.__dict__ for day in heatmap_days],
        "projects": [project_row.__dict__ for project_row in projects],
        "machines": [machine_row.__dict__ for machine_row in machines],
        "last_refreshed_at": None if last_refresh is None else last_refresh.refreshed_at,
        "refresh": None if last_refresh is None else last_refresh.__dict__,
    }


@router.post("/api/refresh")
def refresh_metrics(request: Request) -> dict[str, object]:
    require_admin_session(request)
    report = request.app.state.ingestion_service.refresh_machine(request.app.state.local_machine.id)
    return {
        "last_refreshed_at": report.refreshed_at.isoformat(),
        "machine_id": report.machine_id,
        "refresh_source": report.refresh_source,
        "provider_count": report.provider_count,
        "conversation_count": report.conversation_count,
        "prompt_event_count": report.prompt_event_count,
    }


@router.get("/api/session")
def get_session_status(request: Request) -> dict[str, bool]:
    return {"authenticated": has_admin_session(request)}


@router.post("/api/session/login")
def login_session(request: Request, payload: LoginRequest) -> dict[str, bool]:
    if payload.admin_key != request.app.state.config.admin_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin key")
    sign_in_admin_session(request)
    return {"authenticated": True}


@router.post("/api/session/logout")
def logout_session(request: Request) -> dict[str, bool]:
    clear_admin_session(request)
    return {"authenticated": False}


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.api_route("/favicon.ico", methods=["GET", "HEAD"])
def favicon(request: Request) -> FileResponse:
    static_path = request.app.state.static_path
    return FileResponse(static_path / "favicon.svg", media_type="image/svg+xml")


@router.get("/")
def dashboard(request: Request) -> object:
    templates = request.app.state.templates
    if not has_admin_session(request):
        return templates.TemplateResponse(
            request=request,
            name="index.html",
            context={
                "authenticated": False,
                "client_image": request.app.state.config.client_image,
                "last_refreshed_at": None,
            },
        )
    last_refresh = fetch_latest_refresh_run(
        request.app.state.config.database_path,
        machine=request.app.state.local_machine.label,
    )
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "authenticated": True,
            "client_image": request.app.state.config.client_image,
            "last_refreshed_at": None if last_refresh is None else last_refresh.refreshed_at,
        },
    )
