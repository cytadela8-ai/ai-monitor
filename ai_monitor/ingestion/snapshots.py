from dataclasses import dataclass
from datetime import UTC, datetime
from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from ai_monitor.ingestion.base import Provider
from ai_monitor.ingestion.models import ConversationRecord, PromptEventRecord


@dataclass(frozen=True)
class UsageSnapshot:
    generated_at: datetime
    providers: tuple[str, ...]
    conversations: list[ConversationRecord]
    prompt_events: list[PromptEventRecord]

    @property
    def provider_count(self) -> int:
        return len(self.providers)


def build_snapshot(providers: Sequence[Provider]) -> UsageSnapshot:
    loaded = [provider.load() for provider in providers]
    conversations = [item for bundle in loaded for item in bundle.conversations]
    prompt_events = [item for bundle in loaded for item in bundle.prompt_events]
    provider_names = tuple(sorted({row.provider for row in conversations + prompt_events}))
    return UsageSnapshot(
        generated_at=datetime.now(tz=UTC),
        providers=provider_names,
        conversations=conversations,
        prompt_events=prompt_events,
    )


class ConversationPayload(BaseModel):
    provider: str
    external_id: str
    started_at: datetime
    project_path: str | None
    project_name: str

    model_config = ConfigDict(extra="forbid")

    def to_record(self) -> ConversationRecord:
        return ConversationRecord(
            provider=self.provider,
            external_id=self.external_id,
            started_at=self.started_at,
            project_path=self.project_path,
            project_name=self.project_name,
        )


class PromptEventPayload(BaseModel):
    provider: str
    external_conversation_id: str
    occurred_at: datetime
    project_path: str | None
    project_name: str
    event_type: str
    raw_text: str

    model_config = ConfigDict(extra="forbid")

    def to_record(self) -> PromptEventRecord:
        return PromptEventRecord(
            provider=self.provider,
            external_conversation_id=self.external_conversation_id,
            occurred_at=self.occurred_at,
            project_path=self.project_path,
            project_name=self.project_name,
            event_type=self.event_type,
            raw_text=self.raw_text,
        )


class SnapshotPayload(BaseModel):
    generated_at: datetime
    providers: list[str]
    conversations: list[ConversationPayload]
    prompt_events: list[PromptEventPayload]

    model_config = ConfigDict(extra="forbid")

    def to_snapshot(self) -> UsageSnapshot:
        return UsageSnapshot(
            generated_at=self.generated_at,
            providers=tuple(self.providers),
            conversations=[row.to_record() for row in self.conversations],
            prompt_events=[row.to_record() for row in self.prompt_events],
        )
