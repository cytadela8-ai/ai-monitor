from pathlib import Path

import pytest

from ai_monitor.config import AppConfig, ClientConfig

APP_ENV_KEYS = (
    "AI_MONITOR_DATABASE_PATH",
    "AI_MONITOR_CLAUDE_HISTORY_PATH",
    "AI_MONITOR_CODEX_HISTORY_PATH",
    "AI_MONITOR_CODEX_SESSIONS_ROOT",
    "AI_MONITOR_CLIENT_IMAGE",
    "AI_MONITOR_ADMIN_KEY",
    "AI_MONITOR_LOCAL_MACHINE_LABEL",
    "AI_MONITOR_SESSION_SECRET",
    "AI_MONITOR_HOST",
    "AI_MONITOR_PORT",
)

CLIENT_ENV_KEYS = (
    "AI_MONITOR_SERVER_URL",
    "AI_MONITOR_API_KEY",
    "AI_MONITOR_CLAUDE_HISTORY_PATH",
    "AI_MONITOR_CODEX_HISTORY_PATH",
    "AI_MONITOR_CODEX_SESSIONS_ROOT",
)


def _clear_env(monkeypatch: pytest.MonkeyPatch, keys: tuple[str, ...]) -> None:
    for key in keys:
        monkeypatch.delenv(key, raising=False)


def test_app_config_loads_values_from_dotenv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _clear_env(monkeypatch, APP_ENV_KEYS)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "AI_MONITOR_DATABASE_PATH=from-dotenv.db",
                "AI_MONITOR_CLIENT_IMAGE=ghcr.io/example/ai-monitor-client:tag",
                "AI_MONITOR_ADMIN_KEY=dotenv-admin",
                "AI_MONITOR_LOCAL_MACHINE_LABEL=dotenv-machine",
                "AI_MONITOR_SESSION_SECRET=dotenv-session",
                "AI_MONITOR_HOST=0.0.0.0",
                "AI_MONITOR_PORT=9001",
            ]
        ),
        encoding="utf-8",
    )

    config = AppConfig.from_env()

    assert config.database_path == Path("from-dotenv.db")
    assert config.client_image == "ghcr.io/example/ai-monitor-client:tag"
    assert config.admin_key == "dotenv-admin"
    assert config.local_machine_label == "dotenv-machine"
    assert config.session_secret == "dotenv-session"
    assert config.host == "0.0.0.0"
    assert config.port == 9001


def test_client_config_loads_values_from_dotenv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _clear_env(monkeypatch, CLIENT_ENV_KEYS)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "AI_MONITOR_SERVER_URL=https://example.test/root/",
                "AI_MONITOR_API_KEY=dotenv-machine-key",
            ]
        ),
        encoding="utf-8",
    )

    config = ClientConfig.from_env()

    assert config.server_url == "https://example.test/root"
    assert config.api_key == "dotenv-machine-key"


def test_process_environment_overrides_dotenv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _clear_env(monkeypatch, APP_ENV_KEYS + CLIENT_ENV_KEYS)
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "AI_MONITOR_ADMIN_KEY=dotenv-admin",
                "AI_MONITOR_SERVER_URL=https://dotenv.example",
                "AI_MONITOR_API_KEY=dotenv-machine-key",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("AI_MONITOR_ADMIN_KEY", "process-admin")
    monkeypatch.setenv("AI_MONITOR_SERVER_URL", "https://process.example")
    monkeypatch.setenv("AI_MONITOR_API_KEY", "process-machine-key")

    app_config = AppConfig.from_env()
    client_config = ClientConfig.from_env()

    assert app_config.admin_key == "process-admin"
    assert client_config.server_url == "https://process.example"
    assert client_config.api_key == "process-machine-key"
