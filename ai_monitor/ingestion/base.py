from dataclasses import dataclass
from typing import Protocol

from ai_monitor.ingestion.models import ConversationRecord, PromptEventRecord


@dataclass(frozen=True)
class ProviderLoadResult:
    conversations: list[ConversationRecord]
    prompt_events: list[PromptEventRecord]

    @property
    def conversation_count(self) -> int:
        return len(self.conversations)


class Provider(Protocol):
    """Defines the interface for log providers."""

    def load(self) -> ProviderLoadResult:
        """Loads normalized records for a provider."""

