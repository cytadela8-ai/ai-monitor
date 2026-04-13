import sqlite3
from dataclasses import dataclass
from datetime import date, timedelta
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


@dataclass(frozen=True)
class SummaryMetricsRow:
    conversation_count: int
    text_prompt_count: int
    slash_command_count: int


@dataclass(frozen=True)
class DailyHeatmapRow:
    day: str
    conversation_count: int
    text_prompt_count: int
    slash_command_count: int
    total_events: int


def _build_where_clauses(
    project: str | None = None,
    provider: str | None = None,
) -> tuple[list[str], list[str]]:
    clauses: list[str] = []
    params: list[str] = []

    if project is not None:
        clauses.append("project_name = ?")
        params.append(project)

    if provider is not None:
        clauses.append("provider = ?")
        params.append(provider)

    return clauses, params


def _resolve_latest_prompt_day(
    connection: sqlite3.Connection,
    project: str | None = None,
    provider: str | None = None,
) -> date | None:
    clauses, params = _build_where_clauses(project=project, provider=provider)
    where_sql = "" if not clauses else f"WHERE {' AND '.join(clauses)}"
    row = connection.execute(
        f"""
        SELECT MAX(date(occurred_at))
        FROM prompt_events
        {where_sql}
        """,
        params,
    ).fetchone()
    if row is None or row[0] is None:
        return None

    return date.fromisoformat(row[0])


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


def fetch_summary_metrics(
    database_path: Path,
    project: str | None = None,
    provider: str | None = None,
) -> SummaryMetricsRow:
    """Return filter-scoped summary totals independent of ledger grouping."""
    ensure_database(database_path)
    conversation_clauses, conversation_params = _build_where_clauses(
        project=project,
        provider=provider,
    )
    prompt_clauses, prompt_params = _build_where_clauses(
        project=project,
        provider=provider,
    )
    conversation_where = "" if not conversation_clauses else (
        f"WHERE {' AND '.join(conversation_clauses)}"
    )
    prompt_where = "" if not prompt_clauses else f"WHERE {' AND '.join(prompt_clauses)}"

    connection = sqlite3.connect(database_path)
    try:
        conversation_row = connection.execute(
            f"""
            SELECT COUNT(*)
            FROM conversations
            {conversation_where}
            """,
            conversation_params,
        ).fetchone()
        prompt_row = connection.execute(
            f"""
            SELECT
                COALESCE(SUM(CASE WHEN event_type = 'text_prompt' THEN 1 ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN event_type = 'slash_command' THEN 1 ELSE 0 END), 0)
            FROM prompt_events
            {prompt_where}
            """,
            prompt_params,
        ).fetchone()
    finally:
        connection.close()

    return SummaryMetricsRow(
        conversation_count=0 if conversation_row is None else conversation_row[0],
        text_prompt_count=0 if prompt_row is None else prompt_row[0],
        slash_command_count=0 if prompt_row is None else prompt_row[1],
    )


def fetch_daily_heatmap(
    database_path: Path,
    project: str | None = None,
    provider: str | None = None,
    days: int = 365,
) -> list[DailyHeatmapRow]:
    """Return newest-first daily activity rows with zero-filled inactive days."""
    ensure_database(database_path)
    connection = sqlite3.connect(database_path)
    try:
        latest_day = _resolve_latest_prompt_day(
            connection,
            project=project,
            provider=provider,
        )
        if latest_day is None:
            return []

        clauses, params = _build_where_clauses(project=project, provider=provider)
        clauses.append("date(occurred_at) BETWEEN ? AND ?")
        start_day = latest_day - timedelta(days=max(days - 1, 0))
        params.extend([start_day.isoformat(), latest_day.isoformat()])
        rows = connection.execute(
            f"""
            SELECT
                date(occurred_at) AS day,
                COUNT(DISTINCT provider || ':' || external_conversation_id),
                COALESCE(SUM(CASE WHEN event_type = 'text_prompt' THEN 1 ELSE 0 END), 0),
                COALESCE(SUM(CASE WHEN event_type = 'slash_command' THEN 1 ELSE 0 END), 0)
            FROM prompt_events
            WHERE {' AND '.join(clauses)}
            GROUP BY day
            ORDER BY day DESC
            """,
            params,
        ).fetchall()
    finally:
        connection.close()

    rows_by_day = {
        row[0]: DailyHeatmapRow(
            day=row[0],
            conversation_count=row[1],
            text_prompt_count=row[2],
            slash_command_count=row[3],
            total_events=row[2] + row[3],
        )
        for row in rows
    }

    return [
        rows_by_day.get(
            current_day.isoformat(),
            DailyHeatmapRow(
                day=current_day.isoformat(),
                conversation_count=0,
                text_prompt_count=0,
                slash_command_count=0,
                total_events=0,
            ),
        )
        for current_day in (
            latest_day - timedelta(days=offset) for offset in range(max(days, 0))
        )
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
