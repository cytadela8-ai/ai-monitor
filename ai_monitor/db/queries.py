import sqlite3
from dataclasses import dataclass
from pathlib import Path

from ai_monitor.db.schema import ensure_database


@dataclass(frozen=True)
class AggregateRow:
    period_type: str
    period_start: str
    project_name: str
    provider: str
    conversation_count: int
    text_prompt_count: int
    slash_command_count: int


@dataclass(frozen=True)
class RefreshRunRow:
    refreshed_at: str
    provider_count: int
    conversation_count: int
    prompt_event_count: int


@dataclass(frozen=True)
class ProjectOptionRow:
    project_name: str
    latest_period_start: str
    total_events: int
    conversation_count: int


def fetch_aggregate_rows(database_path: Path) -> list[AggregateRow]:
    ensure_database(database_path)
    connection = sqlite3.connect(database_path)
    try:
        rows = connection.execute(
            """
            SELECT
                period_type,
                period_start,
                project_name,
                provider,
                conversation_count,
                text_prompt_count,
                slash_command_count
            FROM aggregate_metrics
            ORDER BY period_type, period_start, project_name, provider
            """
        ).fetchall()
    finally:
        connection.close()

    return [
        AggregateRow(
            period_type=row[0],
            period_start=row[1],
            project_name=row[2],
            provider=row[3],
            conversation_count=row[4],
            text_prompt_count=row[5],
            slash_command_count=row[6],
        )
        for row in rows
    ]


def fetch_metrics_rows(
    database_path: Path,
    period: str,
    project: str | None = None,
    provider: str | None = None,
) -> list[AggregateRow]:
    ensure_database(database_path)
    where_clauses = ["period_type = ?"]
    params: list[str] = [period]

    if project is not None:
        where_clauses.append("project_name = ?")
        params.append(project)

    if provider is not None:
        where_clauses.append("provider = ?")
        params.append(provider)

    where_sql = " AND ".join(where_clauses)
    connection = sqlite3.connect(database_path)
    try:
        rows = connection.execute(
            f"""
            SELECT
                period_type,
                period_start,
                project_name,
                provider,
                conversation_count,
                text_prompt_count,
                slash_command_count
            FROM aggregate_metrics
            WHERE {where_sql}
            ORDER BY period_start DESC, project_name, provider
            """,
            params,
        ).fetchall()
    finally:
        connection.close()

    return [
        AggregateRow(
            period_type=row[0],
            period_start=row[1],
            project_name=row[2],
            provider=row[3],
            conversation_count=row[4],
            text_prompt_count=row[5],
            slash_command_count=row[6],
        )
        for row in rows
    ]


def fetch_ranked_projects(
    database_path: Path,
    period: str,
    provider: str | None = None,
) -> list[ProjectOptionRow]:
    """Return ranked project options for the current period and provider filter."""
    ensure_database(database_path)
    where_clauses = ["period_type = ?"]
    params: list[str] = [period]

    if provider is not None:
        where_clauses.append("provider = ?")
        params.append(provider)

    where_sql = " AND ".join(where_clauses)
    connection = sqlite3.connect(database_path)
    try:
        rows = connection.execute(
            f"""
            SELECT
                project_name,
                MAX(period_start) AS latest_period_start,
                SUM(text_prompt_count + slash_command_count) AS total_events,
                SUM(conversation_count) AS conversation_count
            FROM aggregate_metrics
            WHERE {where_sql}
            GROUP BY project_name
            ORDER BY
                CASE project_name
                    WHEN '.codex' THEN 1
                    WHEN 'tmp' THEN 1
                    WHEN 'unknown' THEN 1
                    ELSE 0
                END,
                latest_period_start DESC,
                total_events DESC,
                conversation_count DESC,
                project_name
            """,
            params,
        ).fetchall()
    finally:
        connection.close()

    return [
        ProjectOptionRow(
            project_name=row[0],
            latest_period_start=row[1],
            total_events=row[2],
            conversation_count=row[3],
        )
        for row in rows
    ]


def fetch_latest_refresh_run(database_path: Path) -> RefreshRunRow | None:
    ensure_database(database_path)
    connection = sqlite3.connect(database_path)
    try:
        row = connection.execute(
            """
            SELECT refreshed_at, provider_count, conversation_count, prompt_event_count
            FROM refresh_runs
            ORDER BY id DESC
            LIMIT 1
            """
        ).fetchone()
    finally:
        connection.close()

    if row is None:
        return None

    return RefreshRunRow(
        refreshed_at=row[0],
        provider_count=row[1],
        conversation_count=row[2],
        prompt_event_count=row[3],
    )
