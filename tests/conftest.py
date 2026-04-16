import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("AI_MONITOR_DATABASE_PATH", "/tmp/ai_monitor_test_bootstrap.db")
os.environ.setdefault("AI_MONITOR_ADMIN_KEY", "test-admin-key")
os.environ.setdefault("AI_MONITOR_SESSION_SECRET", "test-session-secret")
os.environ.setdefault("AI_MONITOR_LOCAL_MACHINE_LABEL", "main-server")

from ai_monitor.config import AppConfig


def fixture_path(relative_path: str) -> Path:
    return Path(__file__).resolve().parent / "fixtures" / relative_path


@pytest.fixture
def app_config(tmp_path: Path) -> AppConfig:
    return AppConfig(
        database_path=tmp_path / "usage.db",
        claude_history_path=fixture_path("claude/history.jsonl"),
        codex_history_path=fixture_path("codex/history.jsonl"),
        codex_sessions_root=fixture_path("codex/sessions"),
        client_image="ghcr.io/cytadela8-ai/ai-monitor-client:latest",
        admin_key="test-admin-key",
        local_machine_label="main-server",
        session_secret="test-session-secret",
    )


@pytest.fixture
def unauthenticated_client(app_config: AppConfig) -> TestClient:
    from ai_monitor.server.app import create_app

    app = create_app(app_config)
    app.state.ingestion_service.refresh_machine(app.state.local_machine.id)
    return TestClient(app)


@pytest.fixture
def unauthenticated_fresh_client(app_config: AppConfig) -> TestClient:
    from ai_monitor.server.app import create_app

    app = create_app(app_config)
    return TestClient(app)


@pytest.fixture
def client(
    unauthenticated_client: TestClient,
    app_config: AppConfig,
) -> TestClient:
    response = unauthenticated_client.post(
        "/api/session/login",
        json={"admin_key": app_config.admin_key},
    )
    assert response.status_code == 200
    return unauthenticated_client


@pytest.fixture
def fresh_client(
    unauthenticated_fresh_client: TestClient,
    app_config: AppConfig,
) -> TestClient:
    response = unauthenticated_fresh_client.post(
        "/api/session/login",
        json={"admin_key": app_config.admin_key},
    )
    assert response.status_code == 200
    return unauthenticated_fresh_client
