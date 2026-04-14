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
        admin_key="test-admin-key",
        local_machine_label="main-server",
    )


@pytest.fixture
def client(app_config: AppConfig) -> TestClient:
    app = create_app(app_config)
    app.state.ingestion_service.refresh_machine(app.state.local_machine.id)
    return TestClient(app)


@pytest.fixture
def fresh_client(app_config: AppConfig) -> TestClient:
    app = create_app(app_config)
    return TestClient(app)


@pytest.fixture
def admin_headers(app_config: AppConfig) -> dict[str, str]:
    return {"Authorization": f"Bearer {app_config.admin_key}"}
