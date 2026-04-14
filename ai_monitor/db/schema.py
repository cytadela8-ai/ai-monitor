import sqlite3
from pathlib import Path


def _table_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    rows = connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows}


def _add_column_if_missing(
    connection: sqlite3.Connection,
    table_name: str,
    column_name: str,
    definition: str,
) -> None:
    if column_name in _table_columns(connection, table_name):
        return
    connection.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def _migrate_existing_tables(connection: sqlite3.Connection) -> None:
    if "conversations" in _table_names(connection):
        _add_column_if_missing(
            connection,
            "conversations",
            "machine_id",
            "INTEGER NOT NULL DEFAULT 1",
        )
    if "prompt_events" in _table_names(connection):
        _add_column_if_missing(
            connection,
            "prompt_events",
            "machine_id",
            "INTEGER NOT NULL DEFAULT 1",
        )
    if "aggregate_metrics" in _table_names(connection):
        _add_column_if_missing(
            connection,
            "aggregate_metrics",
            "machine_id",
            "INTEGER NOT NULL DEFAULT 1",
        )


def _table_names(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table'"
    ).fetchall()
    return {row[0] for row in rows}


def create_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS machines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL UNIQUE,
            api_key_hash TEXT,
            is_local INTEGER NOT NULL DEFAULT 0,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            last_seen_at TEXT,
            last_refresh_at TEXT,
            last_refresh_source TEXT
        );

        CREATE TABLE IF NOT EXISTS conversations (
            machine_id INTEGER NOT NULL,
            provider TEXT NOT NULL,
            external_id TEXT NOT NULL,
            started_at TEXT NOT NULL,
            project_path TEXT,
            project_name TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS prompt_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id INTEGER NOT NULL,
            provider TEXT NOT NULL,
            external_conversation_id TEXT NOT NULL,
            occurred_at TEXT NOT NULL,
            project_path TEXT,
            project_name TEXT NOT NULL,
            event_type TEXT NOT NULL,
            raw_text TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS aggregate_metrics (
            machine_id INTEGER NOT NULL,
            period_type TEXT NOT NULL,
            period_start TEXT NOT NULL,
            project_name TEXT NOT NULL,
            provider TEXT NOT NULL,
            conversation_count INTEGER NOT NULL,
            text_prompt_count INTEGER NOT NULL,
            slash_command_count INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS machine_refresh_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            machine_id INTEGER NOT NULL,
            refreshed_at TEXT NOT NULL,
            refresh_source TEXT NOT NULL,
            provider_count INTEGER NOT NULL,
            conversation_count INTEGER NOT NULL,
            prompt_event_count INTEGER NOT NULL
        );
        """
    )
    _migrate_existing_tables(connection)
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS conversations_machine_provider_external_id
        ON conversations (machine_id, provider, external_id)
        """
    )
    connection.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS aggregate_metrics_machine_period_project_provider
        ON aggregate_metrics (machine_id, period_type, period_start, project_name, provider)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS prompt_events_machine_occurred_at
        ON prompt_events (machine_id, occurred_at)
        """
    )
    connection.execute(
        """
        CREATE INDEX IF NOT EXISTS aggregate_metrics_machine_period_type
        ON aggregate_metrics (machine_id, period_type)
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


def clear_machine_slice(connection: sqlite3.Connection, machine_id: int) -> None:
    connection.execute("DELETE FROM aggregate_metrics WHERE machine_id = ?", (machine_id,))
    connection.execute("DELETE FROM prompt_events WHERE machine_id = ?", (machine_id,))
    connection.execute("DELETE FROM conversations WHERE machine_id = ?", (machine_id,))


def ensure_database(database_path: Path) -> None:
    connection = sqlite3.connect(database_path)
    try:
        with connection:
            create_schema(connection)
    finally:
        connection.close()
