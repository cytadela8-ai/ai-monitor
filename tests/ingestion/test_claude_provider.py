from pathlib import Path

from ai_monitor.ingestion.providers.claude import ClaudeProvider


def fixture_path(relative_path: str) -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / relative_path


def test_claude_provider_reads_text_and_slash_events() -> None:
    provider = ClaudeProvider(history_path=fixture_path("claude/history.jsonl"))

    bundle = provider.load()

    assert bundle.conversation_count == 2
    assert [event.event_type for event in bundle.prompt_events] == [
        "text_prompt",
        "slash_command",
        "text_prompt",
    ]
    assert {event.project_name for event in bundle.prompt_events} == {"zk-chains-registry"}
