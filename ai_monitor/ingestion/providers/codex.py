import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from ai_monitor.ingestion.base import ProviderLoadResult
from ai_monitor.ingestion.models import ConversationRecord, PromptEventRecord
from ai_monitor.ingestion.path_utils import derive_project_name


@dataclass(frozen=True)
class CodexProvider:
    history_path: Path
    sessions_root: Path

    def load(self) -> ProviderLoadResult:
        session_paths = self._load_session_paths()
        conversation_times: dict[str, datetime] = {}
        prompt_events: list[PromptEventRecord] = []

        with self.history_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue

                record = json.loads(line)
                session_id = str(record["session_id"])
                occurred_at = datetime.fromtimestamp(int(record["ts"]), tz=UTC)
                project_path = session_paths.get(session_id)
                project_name = derive_project_name(project_path)
                raw_text = str(record["text"])

                conversation_times[session_id] = min(
                    occurred_at,
                    conversation_times.get(session_id, occurred_at),
                )
                prompt_events.append(
                    PromptEventRecord(
                        provider="codex",
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
                provider="codex",
                external_id=session_id,
                started_at=conversation_times[session_id],
                project_path=session_paths.get(session_id),
                project_name=derive_project_name(session_paths.get(session_id)),
            )
            for session_id in sorted(conversation_times)
        ]
        return ProviderLoadResult(conversations=conversations, prompt_events=prompt_events)

    def _load_session_paths(self) -> dict[str, str | None]:
        session_paths: dict[str, str | None] = {}
        for session_file in sorted(self.sessions_root.rglob("*.jsonl")):
            with session_file.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue

                    record = json.loads(line)
                    if record.get("type") != "session_meta":
                        continue

                    payload = record.get("payload", {})
                    if not isinstance(payload, dict):
                        continue

                    session_id = payload.get("id")
                    if session_id:
                        cwd = payload.get("cwd")
                        session_paths[str(session_id)] = str(cwd) if cwd else None
        return session_paths

    @staticmethod
    def _classify_event(raw_text: str) -> str:
        return "slash_command" if raw_text.startswith("/") else "text_prompt"
