import sqlite3
from pathlib import Path

from ai_monitor.db.queries import fetch_daily_heatmap, fetch_summary_metrics
from ai_monitor.db.schema import ensure_database


def seed_usage_database(database_path: Path) -> None:
    ensure_database(database_path)
    connection = sqlite3.connect(database_path)
    try:
        with connection:
            connection.executemany(
                """
                INSERT INTO conversations (
                    provider,
                    external_id,
                    started_at,
                    project_path,
                    project_name
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        "codex",
                        "c1",
                        "2026-03-27T10:00:00+00:00",
                        "/work/alpha",
                        "alpha",
                    ),
                    (
                        "claude",
                        "c2",
                        "2026-03-28T12:00:00+00:00",
                        "/work/alpha",
                        "alpha",
                    ),
                    (
                        "claude",
                        "c3",
                        "2026-03-30T09:00:00+00:00",
                        "/work/beta",
                        "beta",
                    ),
                ],
            )
            connection.executemany(
                """
                INSERT INTO prompt_events (
                    provider,
                    external_conversation_id,
                    occurred_at,
                    project_path,
                    project_name,
                    event_type,
                    raw_text
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        "codex",
                        "c1",
                        "2026-03-27T10:00:00+00:00",
                        "/work/alpha",
                        "alpha",
                        "text_prompt",
                        "first prompt",
                    ),
                    (
                        "codex",
                        "c1",
                        "2026-03-28T09:30:00+00:00",
                        "/work/alpha",
                        "alpha",
                        "text_prompt",
                        "second prompt",
                    ),
                    (
                        "codex",
                        "c1",
                        "2026-03-28T09:31:00+00:00",
                        "/work/alpha",
                        "alpha",
                        "slash_command",
                        "/clear",
                    ),
                    (
                        "claude",
                        "c2",
                        "2026-03-28T12:00:00+00:00",
                        "/work/alpha",
                        "alpha",
                        "text_prompt",
                        "third prompt",
                    ),
                    (
                        "claude",
                        "c3",
                        "2026-03-30T09:00:00+00:00",
                        "/work/beta",
                        "beta",
                        "slash_command",
                        "/help",
                    ),
                ],
            )
    finally:
        connection.close()


def test_fetch_summary_metrics_uses_distinct_conversations_across_filters(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "usage.db"
    seed_usage_database(database_path)

    summary = fetch_summary_metrics(database_path)

    assert summary.conversation_count == 3
    assert summary.text_prompt_count == 3
    assert summary.slash_command_count == 2


def test_fetch_summary_metrics_respects_project_and_provider_filters(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "usage.db"
    seed_usage_database(database_path)

    summary = fetch_summary_metrics(
        database_path,
        project="alpha",
        provider="codex",
    )

    assert summary.conversation_count == 1
    assert summary.text_prompt_count == 2
    assert summary.slash_command_count == 1


def test_fetch_daily_heatmap_returns_exact_counts_with_zero_filled_days(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "usage.db"
    seed_usage_database(database_path)

    rows = fetch_daily_heatmap(database_path, days=4)

    assert [row.day for row in rows] == [
        "2026-03-30",
        "2026-03-29",
        "2026-03-28",
        "2026-03-27",
    ]
    assert [row.conversation_count for row in rows] == [1, 0, 2, 1]
    assert [row.text_prompt_count for row in rows] == [0, 0, 2, 1]
    assert [row.slash_command_count for row in rows] == [1, 0, 1, 0]
    assert [row.total_events for row in rows] == [1, 0, 3, 1]


def test_fetch_daily_heatmap_filters_to_requested_project(tmp_path: Path) -> None:
    database_path = tmp_path / "usage.db"
    seed_usage_database(database_path)

    rows = fetch_daily_heatmap(database_path, project="alpha", days=4)

    assert [row.day for row in rows] == [
        "2026-03-28",
        "2026-03-27",
        "2026-03-26",
        "2026-03-25",
    ]
    assert [row.total_events for row in rows] == [3, 1, 0, 0]
