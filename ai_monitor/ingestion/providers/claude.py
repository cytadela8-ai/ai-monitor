import json
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ai_monitor.ingestion.base import ProviderLoadResult
from ai_monitor.ingestion.models import ConversationRecord, PromptEventRecord
from ai_monitor.ingestion.path_utils import derive_project_name


@dataclass(frozen=True)
class ClaudeProvider:
    history_path: Path

    def load(self) -> ProviderLoadResult:
        conversation_times: dict[str, datetime] = {}
        conversation_paths: dict[str, str | None] = {}
        prompt_events: list[PromptEventRecord] = []

        for raw_record in self._read_records():
            session_id = str(raw_record["sessionId"])
            project_path = self._get_project_path(raw_record)
            project_name = derive_project_name(project_path)
            occurred_at = self._parse_timestamp(raw_record["timestamp"])
            raw_text = str(raw_record["display"])

            conversation_paths.setdefault(session_id, project_path)
            conversation_times[session_id] = min(
                occurred_at,
                conversation_times.get(session_id, occurred_at),
            )
            prompt_events.append(
                PromptEventRecord(
                    provider="claude",
                    external_conversation_id=session_id,
                    occurred_at=occurred_at,
                    project_path=project_path,
                    project_name=project_name,
                    event_type=self._classify_event(raw_text),
                    raw_text=raw_text,
                )
            )

        conversations = [
            ConversationRecord(
                provider="claude",
                external_id=session_id,
                started_at=conversation_times[session_id],
                project_path=conversation_paths.get(session_id),
                project_name=derive_project_name(conversation_paths.get(session_id)),
            )
            for session_id in sorted(conversation_times)
        ]
        return ProviderLoadResult(conversations=conversations, prompt_events=prompt_events)

    def _read_records(self) -> Iterable[dict[str, object]]:
        with self.history_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    yield json.loads(line)

    @staticmethod
    def _classify_event(raw_text: str) -> str:
        return "slash_command" if raw_text.startswith("/") else "text_prompt"

    @staticmethod
    def _get_project_path(record: dict[str, object]) -> str | None:
        project_value = record.get("project")
        return str(project_value) if project_value else None

    @staticmethod
    def _parse_timestamp(timestamp_ms: object) -> datetime:
        if not isinstance(timestamp_ms, int | str):
            msg = f"Unsupported Claude timestamp value: {timestamp_ms!r}"
            raise ValueError(msg)

        timestamp = int(timestamp_ms) / 1000
        return datetime.fromtimestamp(timestamp, tz=UTC)
