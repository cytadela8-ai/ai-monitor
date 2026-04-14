from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ai_monitor.db.queries import fetch_aggregate_rows, fetch_summary_metrics
from ai_monitor.ingestion.base import ProviderLoadResult
from ai_monitor.ingestion.models import ConversationRecord, PromptEventRecord
from ai_monitor.ingestion.service import IngestionService
from ai_monitor.machines import create_machine, ensure_local_machine


@dataclass(frozen=True)
class FixtureProvider:
    def load(self) -> ProviderLoadResult:
        started_at = datetime(2026, 4, 1, 11, 48, tzinfo=UTC)
        prompt_time = datetime(2026, 4, 1, 11, 49, tzinfo=UTC)
        return ProviderLoadResult(
            conversations=[
                ConversationRecord(
                    provider="claude",
                    external_id="session-1",
                    started_at=started_at,
                    project_path="/home/ubuntu/zk-chains-registry",
                    project_name="zk-chains-registry",
                )
            ],
            prompt_events=[
                PromptEventRecord(
                    provider="claude",
                    external_conversation_id="session-1",
                    occurred_at=prompt_time,
                    project_path="/home/ubuntu/zk-chains-registry",
                    project_name="zk-chains-registry",
                    event_type="text_prompt",
                    raw_text="Implement refresh",
                ),
                PromptEventRecord(
                    provider="claude",
                    external_conversation_id="session-1",
                    occurred_at=prompt_time,
                    project_path="/home/ubuntu/zk-chains-registry",
                    project_name="zk-chains-registry",
                    event_type="slash_command",
                    raw_text="/clear",
                ),
                PromptEventRecord(
                    provider="claude",
                    external_conversation_id="session-1",
                    occurred_at=prompt_time,
                    project_path="/home/ubuntu/zk-chains-registry",
                    project_name="zk-chains-registry",
                    event_type="text_prompt",
                    raw_text="Add monthly view",
                ),
            ],
        )


def test_rebuild_creates_day_week_month_aggregates(tmp_path: Path) -> None:
    database_path = tmp_path / "usage.db"
    service = IngestionService(database_path=database_path, providers=[FixtureProvider()])
    local_machine = ensure_local_machine(database_path, "main-server")

    report = service.refresh_machine(local_machine.id)
    rows = fetch_aggregate_rows(database_path)

    assert report.prompt_event_count == 3
    assert {row.period_type for row in rows} == {"day", "week", "month"}
    assert rows[0].conversation_count >= 1


def test_replace_snapshot_only_updates_selected_machine(tmp_path: Path) -> None:
    database_path = tmp_path / "usage.db"
    service = IngestionService(database_path=database_path, providers=[FixtureProvider()])
    local_machine = ensure_local_machine(database_path, "main-server")
    remote_machine, _ = create_machine(database_path, "work-laptop")

    service.refresh_machine(local_machine.id)
    service.replace_snapshot(
        machine_id=remote_machine.id,
        snapshot=service.build_snapshot(),
        refresh_source="remote_push",
    )

    local_summary = fetch_summary_metrics(database_path, machine="main-server")
    remote_summary = fetch_summary_metrics(database_path, machine="work-laptop")

    assert local_summary == remote_summary
