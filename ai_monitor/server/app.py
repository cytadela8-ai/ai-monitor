from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from ai_monitor.config import AppConfig
from ai_monitor.db.schema import ensure_database
from ai_monitor.ingestion.providers.claude import ClaudeProvider
from ai_monitor.ingestion.providers.codex import CodexProvider
from ai_monitor.ingestion.service import IngestionService
from ai_monitor.machines import ensure_local_machine
from ai_monitor.server.admin_routes import router as admin_router
from ai_monitor.server.ingest_routes import router as ingest_router
from ai_monitor.server.routes import router


def create_app(config: AppConfig | None = None) -> FastAPI:
    app_config = config or AppConfig.from_env()
    server_root = Path(__file__).resolve().parent
    ensure_database(app_config.database_path)
    app = FastAPI(title="AI Monitor")
    app.add_middleware(
        SessionMiddleware,
        secret_key=app_config.session_secret,
        session_cookie="ai_monitor_admin_session",
        max_age=60 * 60 * 24 * 30,
        same_site="lax",
    )
    app.add_middleware(GZipMiddleware, minimum_size=500)
    app.state.config = app_config
    app.state.static_path = server_root / "static"
    app.state.templates = Jinja2Templates(directory=str(server_root / "templates"))
    app.state.local_machine = ensure_local_machine(
        app_config.database_path,
        app_config.local_machine_label,
    )
    app.state.ingestion_service = IngestionService(
        database_path=app_config.database_path,
        providers=[
            ClaudeProvider(history_path=app_config.claude_history_path),
            CodexProvider(
                history_path=app_config.codex_history_path,
                sessions_root=app_config.codex_sessions_root,
            ),
        ],
    )
    app.mount("/static", StaticFiles(directory=app.state.static_path), name="static")
    app.include_router(router)
    app.include_router(admin_router)
    app.include_router(ingest_router)
    return app


def main() -> None:
    config = AppConfig.from_env()
    uvicorn.run(
        create_app(config),
        host=config.host,
        port=config.port,
    )


app = create_app()
