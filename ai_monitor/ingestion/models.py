from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ConversationRecord:
    provider: str
    external_id: str
    started_at: datetime
    project_path: str | None
    project_name: str


@dataclass(frozen=True)
class PromptEventRecord:
    provider: str
    external_conversation_id: str
    occurred_at: datetime
    project_path: str | None
    project_name: str
    event_type: str
    raw_text: str
