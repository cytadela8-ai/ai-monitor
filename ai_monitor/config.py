import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _load_working_directory_dotenv() -> None:
    dotenv_path = Path.cwd() / ".env"
    if dotenv_path.is_file():
        load_dotenv(dotenv_path=dotenv_path, override=False)


def _env_path(name: str, default: Path) -> Path:
    value = os.getenv(name)
    if value is None:
        return default
    return Path(os.path.expandvars(value)).expanduser()


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


@dataclass(frozen=True)
class AppConfig:
    database_path: Path
    claude_history_path: Path
    codex_history_path: Path
    codex_sessions_root: Path
    client_image: str
    admin_key: str
    local_machine_label: str
    session_secret: str
    host: str = "127.0.0.1"
    port: int = 8000

    @classmethod
    def from_env(cls) -> "AppConfig":
        _load_working_directory_dotenv()
        home = Path.home()
        admin_key = os.getenv("AI_MONITOR_ADMIN_KEY", "local-admin-key")
        return cls(
            database_path=_env_path("AI_MONITOR_DATABASE_PATH", Path("ai_monitor.db")),
            claude_history_path=_env_path(
                "AI_MONITOR_CLAUDE_HISTORY_PATH",
                home / ".claude" / "history.jsonl",
            ),
            codex_history_path=_env_path(
                "AI_MONITOR_CODEX_HISTORY_PATH",
                home / ".codex" / "history.jsonl",
            ),
            codex_sessions_root=_env_path(
                "AI_MONITOR_CODEX_SESSIONS_ROOT",
                home / ".codex" / "sessions",
            ),
            client_image=os.getenv(
                "AI_MONITOR_CLIENT_IMAGE",
                "ghcr.io/cytadela8-ai/ai-monitor-client:latest",
            ),
            admin_key=admin_key,
            local_machine_label=os.getenv("AI_MONITOR_LOCAL_MACHINE_LABEL", "main-server"),
            session_secret=os.getenv("AI_MONITOR_SESSION_SECRET", admin_key),
            host=os.getenv("AI_MONITOR_HOST", "127.0.0.1"),
            port=int(os.getenv("AI_MONITOR_PORT", "8000")),
        )


@dataclass(frozen=True)
class ClientConfig:
    server_url: str
    api_key: str
    claude_history_path: Path
    codex_history_path: Path
    codex_sessions_root: Path

    @classmethod
    def from_env(cls) -> "ClientConfig":
        _load_working_directory_dotenv()
        home = Path.home()
        return cls(
            server_url=_require_env("AI_MONITOR_SERVER_URL").rstrip("/"),
            api_key=_require_env("AI_MONITOR_API_KEY"),
            claude_history_path=_env_path(
                "AI_MONITOR_CLAUDE_HISTORY_PATH",
                home / ".claude" / "history.jsonl",
            ),
            codex_history_path=_env_path(
                "AI_MONITOR_CODEX_HISTORY_PATH",
                home / ".codex" / "history.jsonl",
            ),
            codex_sessions_root=_env_path(
                "AI_MONITOR_CODEX_SESSIONS_ROOT",
                home / ".codex" / "sessions",
            ),
        )
