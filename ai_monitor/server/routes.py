from fastapi import APIRouter, Query, Request

from ai_monitor.db.queries import RefreshRunRow, fetch_latest_refresh_run, fetch_metrics_rows

router = APIRouter()


def _ensure_usage_data(request: Request) -> RefreshRunRow | None:
    config = request.app.state.config
    last_refresh = fetch_latest_refresh_run(config.database_path)
    if last_refresh is not None:
        return last_refresh

    request.app.state.ingestion_service.refresh()
    return fetch_latest_refresh_run(config.database_path)


@router.get("/api/metrics")
def get_metrics(
    request: Request,
    period: str = Query(default="day"),
    project: str | None = Query(default=None),
    provider: str | None = Query(default=None),
) -> dict[str, object]:
    config = request.app.state.config
    last_refresh = _ensure_usage_data(request)
    rows = fetch_metrics_rows(
        database_path=config.database_path,
        period=period,
        project=project,
        provider=provider,
    )
    return {
        "period": period,
        "rows": [row.__dict__ for row in rows],
        "last_refreshed_at": None if last_refresh is None else last_refresh.refreshed_at,
        "refresh": None if last_refresh is None else last_refresh.__dict__,
    }


@router.post("/api/refresh")
def refresh_metrics(request: Request) -> dict[str, object]:
    report = request.app.state.ingestion_service.refresh()
    return {
        "last_refreshed_at": report.refreshed_at.isoformat(),
        "provider_count": report.provider_count,
        "conversation_count": report.conversation_count,
        "prompt_event_count": report.prompt_event_count,
    }


@router.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/")
def dashboard(request: Request) -> object:
    templates = request.app.state.templates
    last_refresh = _ensure_usage_data(request)
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "last_refreshed_at": None if last_refresh is None else last_refresh.refreshed_at,
        },
    )
