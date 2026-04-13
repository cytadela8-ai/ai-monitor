import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AggregateRow:
    period_type: str
    period_start: str
    project_name: str
    provider: str
    conversation_count: int
    text_prompt_count: int
    slash_command_count: int


def fetch_aggregate_rows(database_path: Path) -> list[AggregateRow]:
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
