import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ai_monitor.db.schema import clear_machine_slice, create_schema
from ai_monitor.ingestion.base import Provider
from ai_monitor.ingestion.models import ConversationRecord, PromptEventRecord
from ai_monitor.ingestion.snapshots import UsageSnapshot, build_snapshot


@dataclass(frozen=True)
class RefreshReport:
    machine_id: int
    refreshed_at: datetime
    refresh_source: str
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
    """Builds local snapshots and persists them into one machine slice."""

    def __init__(self, database_path: Path, providers: list[Provider]) -> None:
        self.database_path = database_path
        self.providers = providers

    def build_snapshot(self) -> UsageSnapshot:
        return build_snapshot(self.providers)

    def refresh_machine(self, machine_id: int) -> RefreshReport:
        return self.replace_snapshot(
            machine_id=machine_id,
            snapshot=self.build_snapshot(),
            refresh_source="local_refresh",
        )

    def replace_snapshot(
        self,
        machine_id: int,
        snapshot: UsageSnapshot,
        refresh_source: str,
    ) -> RefreshReport:
        report = RefreshReport(
            machine_id=machine_id,
            refreshed_at=datetime.now(tz=UTC),
            refresh_source=refresh_source,
            provider_count=snapshot.provider_count,
            conversation_count=len(snapshot.conversations),
            prompt_event_count=len(snapshot.prompt_events),
        )

        connection = sqlite3.connect(self.database_path)
        try:
            with connection:
                create_schema(connection)
                self._ensure_machine_exists(connection, machine_id)
                clear_machine_slice(connection, machine_id)
                self._insert_conversations(connection, machine_id, snapshot.conversations)
                self._insert_prompt_events(connection, machine_id, snapshot.prompt_events)
                self._insert_aggregates(connection, machine_id, snapshot.prompt_events)
                self._insert_refresh_run(connection, report)
                self._touch_machine(connection, report)
        finally:
            connection.close()
        return report

    def _ensure_machine_exists(self, connection: sqlite3.Connection, machine_id: int) -> None:
        row = connection.execute(
            "SELECT 1 FROM machines WHERE id = ?",
            (machine_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"Unknown machine_id: {machine_id}")

    def _insert_conversations(
        self,
        connection: sqlite3.Connection,
        machine_id: int,
        conversations: list[ConversationRecord],
    ) -> None:
        connection.executemany(
            """
            INSERT INTO conversations (
                machine_id,
                provider,
                external_id,
                started_at,
                project_path,
                project_name
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    machine_id,
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
        machine_id: int,
        prompt_events: list[PromptEventRecord],
    ) -> None:
        connection.executemany(
            """
            INSERT INTO prompt_events (
                machine_id,
                provider,
                external_conversation_id,
                occurred_at,
                project_path,
                project_name,
                event_type,
                raw_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    machine_id,
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
        machine_id: int,
        prompt_events: list[PromptEventRecord],
    ) -> None:
        grouped = self._build_aggregates(prompt_events)
        connection.executemany(
            """
            INSERT INTO aggregate_metrics (
                machine_id,
                period_type,
                period_start,
                project_name,
                provider,
                conversation_count,
                text_prompt_count,
                slash_command_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    machine_id,
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
            INSERT INTO machine_refresh_runs (
                machine_id,
                refreshed_at,
                refresh_source,
                provider_count,
                conversation_count,
                prompt_event_count
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                report.machine_id,
                report.refreshed_at.isoformat(),
                report.refresh_source,
                report.provider_count,
                report.conversation_count,
                report.prompt_event_count,
            ),
        )

    def _touch_machine(
        self,
        connection: sqlite3.Connection,
        report: RefreshReport,
    ) -> None:
        timestamp = report.refreshed_at.isoformat()
        connection.execute(
            """
            UPDATE machines
            SET last_seen_at = ?, last_refresh_at = ?, last_refresh_source = ?
            WHERE id = ?
            """,
            (timestamp, timestamp, report.refresh_source, report.machine_id),
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
