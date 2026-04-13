import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ai_monitor.db.schema import clear_normalized_tables, create_schema
from ai_monitor.ingestion.base import Provider
from ai_monitor.ingestion.models import ConversationRecord, PromptEventRecord


@dataclass(frozen=True)
class RefreshReport:
    refreshed_at: datetime
    provider_count: int
    conversation_count: int
    prompt_event_count: int


@dataclass(frozen=True)
class AggregateKey:
    period_type: str
    period_start: str
    project_name: str
    provider: str


@dataclass
class AggregateCounts:
    conversation_ids: set[str]
    text_prompt_count: int = 0
    slash_command_count: int = 0


class IngestionService:
    """Rebuilds normalized usage data from provider outputs."""

    def __init__(self, database_path: Path, providers: list[Provider]) -> None:
        self.database_path = database_path
        self.providers = providers

    def refresh(self) -> RefreshReport:
        loaded = [provider.load() for provider in self.providers]
        conversations = [item for bundle in loaded for item in bundle.conversations]
        prompt_events = [item for bundle in loaded for item in bundle.prompt_events]
        report = RefreshReport(
            refreshed_at=datetime.now(tz=UTC),
            provider_count=len(self.providers),
            conversation_count=len(conversations),
            prompt_event_count=len(prompt_events),
        )

        connection = sqlite3.connect(self.database_path)
        try:
            with connection:
                create_schema(connection)
                clear_normalized_tables(connection)
                self._insert_conversations(connection, conversations)
                self._insert_prompt_events(connection, prompt_events)
                self._insert_aggregates(connection, prompt_events)
                self._insert_refresh_run(connection, report)
        finally:
            connection.close()
        return report

    def _insert_conversations(
        self,
        connection: sqlite3.Connection,
        conversations: list[ConversationRecord],
    ) -> None:
        connection.executemany(
            """
            INSERT INTO conversations (
                provider, external_id, started_at, project_path, project_name
            ) VALUES (?, ?, ?, ?, ?)
            """,
            [
                (
                    row.provider,
                    row.external_id,
                    row.started_at.isoformat(),
                    row.project_path,
                    row.project_name,
                )
                for row in conversations
            ],
        )

    def _insert_prompt_events(
        self,
        connection: sqlite3.Connection,
        prompt_events: list[PromptEventRecord],
    ) -> None:
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
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    row.provider,
                    row.external_conversation_id,
                    row.occurred_at.isoformat(),
                    row.project_path,
                    row.project_name,
                    row.event_type,
                    row.raw_text,
                )
                for row in prompt_events
            ],
        )

    def _insert_aggregates(
        self,
        connection: sqlite3.Connection,
        prompt_events: list[PromptEventRecord],
    ) -> None:
        grouped = self._build_aggregates(prompt_events)
        connection.executemany(
            """
            INSERT INTO aggregate_metrics (
                period_type,
                period_start,
                project_name,
                provider,
                conversation_count,
                text_prompt_count,
                slash_command_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    key.period_type,
                    key.period_start,
                    key.project_name,
                    key.provider,
                    len(counts.conversation_ids),
                    counts.text_prompt_count,
                    counts.slash_command_count,
                )
                for key, counts in grouped.items()
            ],
        )

    def _insert_refresh_run(
        self,
        connection: sqlite3.Connection,
        report: RefreshReport,
    ) -> None:
        connection.execute(
            """
            INSERT INTO refresh_runs (
                refreshed_at, provider_count, conversation_count, prompt_event_count
            ) VALUES (?, ?, ?, ?)
            """,
            (
                report.refreshed_at.isoformat(),
                report.provider_count,
                report.conversation_count,
                report.prompt_event_count,
            ),
        )

    def _build_aggregates(
        self,
        prompt_events: list[PromptEventRecord],
    ) -> dict[AggregateKey, AggregateCounts]:
        grouped: dict[AggregateKey, AggregateCounts] = {}
        for event in prompt_events:
            for period_type, period_start in self._period_values(event.occurred_at):
                key = AggregateKey(
                    period_type=period_type,
                    period_start=period_start,
                    project_name=event.project_name,
                    provider=event.provider,
                )
                counts = grouped.setdefault(key, AggregateCounts(conversation_ids=set()))
                counts.conversation_ids.add(event.external_conversation_id)
                if event.event_type == "slash_command":
                    counts.slash_command_count += 1
                else:
                    counts.text_prompt_count += 1
        return grouped

    def _period_values(self, occurred_at: datetime) -> list[tuple[str, str]]:
        day_start = occurred_at.date().isoformat()
        week_start = (occurred_at.date() - timedelta(days=occurred_at.weekday())).isoformat()
        month_start = occurred_at.date().replace(day=1).isoformat()
        return [
            ("day", day_start),
            ("week", week_start),
            ("month", month_start),
        ]
