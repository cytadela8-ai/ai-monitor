from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppConfig:
    database_path: Path
    claude_history_path: Path
    codex_history_path: Path
    codex_sessions_root: Path

    @classmethod
    def from_env(cls) -> "AppConfig":
        home = Path.home()
        return cls(
            database_path=Path("ai_monitor.db"),
            claude_history_path=home / ".claude" / "history.jsonl",
            codex_history_path=home / ".codex" / "history.jsonl",
            codex_sessions_root=home / ".codex" / "sessions",
        )
