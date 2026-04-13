from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from ai_monitor.db.queries import fetch_latest_refresh_run, fetch_metrics_rows

router = APIRouter()


@router.get("/api/metrics")
def get_metrics(
    request: Request,
    period: str = Query(default="day"),
    project: str | None = Query(default=None),
    provider: str | None = Query(default=None),
) -> dict[str, object]:
    config = request.app.state.config
    rows = fetch_metrics_rows(
        database_path=config.database_path,
        period=period,
        project=project,
        provider=provider,
    )
    last_refresh = fetch_latest_refresh_run(config.database_path)
    return {
        "period": period,
        "rows": [row.__dict__ for row in rows],
        "last_refreshed_at": None if last_refresh is None else last_refresh.refreshed_at,
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


@router.get("/", response_class=HTMLResponse)
def dashboard() -> str:
    return "<html><body><h1>AI Monitor</h1></body></html>"
