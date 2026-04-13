from pathlib import Path

from ai_monitor.ingestion.providers.codex import CodexProvider


def fixture_path(relative_path: str) -> Path:
    return Path(__file__).resolve().parents[1] / "fixtures" / relative_path


def test_codex_provider_joins_history_with_session_cwd() -> None:
    provider = CodexProvider(
        history_path=fixture_path("codex/history.jsonl"),
        sessions_root=fixture_path("codex/sessions"),
    )

    bundle = provider.load()

    assert bundle.conversation_count == 1
    assert bundle.conversations[0].project_name == "zksync-prividium"
    assert [event.event_type for event in bundle.prompt_events] == [
        "text_prompt",
        "slash_command",
    ]
