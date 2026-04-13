import sqlite3
from pathlib import Path


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            provider TEXT NOT NULL,
            external_id TEXT NOT NULL,
            started_at TEXT NOT NULL,
            project_path TEXT,
            project_name TEXT NOT NULL,
            PRIMARY KEY (provider, external_id)
        );

        CREATE TABLE IF NOT EXISTS prompt_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            provider TEXT NOT NULL,
            external_conversation_id TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            project_path TEXT,
            project_name TEXT NOT NULL,
            event_type TEXT NOT NULL,
            raw_text TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS aggregate_metrics (
            period_type TEXT NOT NULL,
            period_start TEXT NOT NULL,
            project_name TEXT NOT NULL,
            provider TEXT NOT NULL,
            conversation_count INTEGER NOT NULL,
            text_prompt_count INTEGER NOT NULL,
            slash_command_count INTEGER NOT NULL,
            PRIMARY KEY (period_type, period_start, project_name, provider)
        );

        CREATE TABLE IF NOT EXISTS refresh_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            refreshed_at TEXT NOT NULL,
            provider_count INTEGER NOT NULL,
            conversation_count INTEGER NOT NULL,
            prompt_event_count INTEGER NOT NULL
        );
        """
    )


def clear_normalized_tables(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        DELETE FROM aggregate_metrics;
        DELETE FROM prompt_events;
        DELETE FROM conversations;
        """
    )


def ensure_database(database_path: Path) -> None:
    connection = sqlite3.connect(database_path)
    try:
        with connection:
            create_schema(connection)
    finally:
        connection.close()
