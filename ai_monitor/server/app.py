from fastapi import FastAPI

from ai_monitor.config import AppConfig
from ai_monitor.ingestion.providers.claude import ClaudeProvider
from ai_monitor.ingestion.providers.codex import CodexProvider
from ai_monitor.ingestion.service import IngestionService
from ai_monitor.server.routes import router


def create_app(config: AppConfig | None = None) -> FastAPI:
    app_config = config or AppConfig.from_env()
    app = FastAPI(title="AI Monitor")
    app.state.config = app_config
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
    app.include_router(router)
    return app


app = create_app()
