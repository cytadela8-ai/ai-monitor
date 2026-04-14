from fastapi import APIRouter, Query, Request
from fastapi.responses import FileResponse

from ai_monitor.db.queries import (
    fetch_daily_heatmap,
    fetch_latest_refresh_run,
    fetch_machine_options,
    fetch_metrics_rows,
    fetch_ranked_projects,
    fetch_summary_metrics,
)

router = APIRouter()


@router.get("/api/metrics")
def get_metrics(
    request: Request,
    period: str = Query(default="day"),
    machine: str | None = Query(default=None),
    project: str | None = Query(default=None),
    provider: str | None = Query(default=None),
) -> dict[str, object]:
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
    report = request.app.state.ingestion_service.refresh_machine(request.app.state.local_machine.id)
    return {
        "last_refreshed_at": report.refreshed_at.isoformat(),
        "machine_id": report.machine_id,
        "refresh_source": report.refresh_source,
        "provider_count": report.provider_count,
        "conversation_count": report.conversation_count,
        "prompt_event_count": report.prompt_event_count,
    }


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
    last_refresh = fetch_latest_refresh_run(
        request.app.state.config.database_path,
        machine=request.app.state.local_machine.label,
    )
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "last_refreshed_at": None if last_refresh is None else last_refresh.refreshed_at,
        },
    )
