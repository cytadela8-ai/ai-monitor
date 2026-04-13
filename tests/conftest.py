from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai_monitor.config import AppConfig
from ai_monitor.server.app import create_app


def fixture_path(relative_path: str) -> Path:
    return Path(__file__).resolve().parent / "fixtures" / relative_path


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        database_path=tmp_path / "usage.db",
        claude_history_path=fixture_path("claude/history.jsonl"),
        codex_history_path=fixture_path("codex/history.jsonl"),
        codex_sessions_root=fixture_path("codex/sessions"),
    )


@pytest.fixture
def client(app_config: AppConfig) -> TestClient:
    app = create_app(app_config)
    app.state.ingestion_service.refresh()
    return TestClient(app)
