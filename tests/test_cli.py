from datetime import UTC, datetime
from io import StringIO

import pytest

from ai_monitor import cli
from ai_monitor.cli import SyncUploadResult, run_sync
from ai_monitor.config import ClientConfig
from ai_monitor.ingestion.models import ConversationRecord, PromptEventRecord
from ai_monitor.ingestion.snapshots import UsageSnapshot


def test_run_sync_uploads_snapshot_and_reports_counts(tmp_path) -> None:
    config = ClientConfig(
        server_url="https://monitor.example.com",
        api_key="machine-key",
        claude_history_path=tmp_path / "claude.jsonl",
        codex_history_path=tmp_path / "codex.jsonl",
        codex_sessions_root=tmp_path / "sessions",
    )
    snapshot = UsageSnapshot(
        generated_at=datetime(2026, 4, 14, 12, 0, tzinfo=UTC),
        providers=("claude",),
        conversations=[
            ConversationRecord(
                provider="claude",
                external_id="session-1",
                started_at=datetime(2026, 4, 14, 11, 0, tzinfo=UTC),
                project_path="/work/alpha",
                project_name="alpha",
            )
        ],
        prompt_events=[
            PromptEventRecord(
                provider="claude",
                external_conversation_id="session-1",
                occurred_at=datetime(2026, 4, 14, 11, 5, tzinfo=UTC),
                project_path="/work/alpha",
                project_name="alpha",
                event_type="text_prompt",
                raw_text="ship it",
            )
        ],
    )
    calls: list[tuple[str, str, UsageSnapshot]] = []
    stdout = StringIO()
    stderr = StringIO()

    def fake_builder() -> UsageSnapshot:
        return snapshot

    def fake_uploader(
        server_url: str,
        api_key: str,
        built_snapshot: UsageSnapshot,
    ) -> SyncUploadResult:
        calls.append((server_url, api_key, built_snapshot))
        return SyncUploadResult(
            conversation_count=1,
            prompt_event_count=1,
            provider_count=1,
        )

    exit_code = run_sync(
        config=config,
        stdout=stdout,
        stderr=stderr,
        snapshot_builder=fake_builder,
        uploader=fake_uploader,
    )

    assert exit_code == 0
    assert calls == [("https://monitor.example.com", "machine-key", snapshot)]
    assert stderr.getvalue() == ""
    assert stdout.getvalue().strip() == (
        "Synced 1 conversations and 1 prompt events across 1 providers."
    )


def test_run_sync_returns_nonzero_when_upload_fails(tmp_path) -> None:
    config = ClientConfig(
        server_url="https://monitor.example.com",
        api_key="machine-key",
        claude_history_path=tmp_path / "claude.jsonl",
        codex_history_path=tmp_path / "codex.jsonl",
        codex_sessions_root=tmp_path / "sessions",
    )
    stdout = StringIO()
    stderr = StringIO()

    def fake_builder() -> UsageSnapshot:
        return UsageSnapshot(
            generated_at=datetime(2026, 4, 14, 12, 0, tzinfo=UTC),
            providers=(),
            conversations=[],
            prompt_events=[],
        )

    def failing_uploader(
        server_url: str,
        api_key: str,
        built_snapshot: UsageSnapshot,
    ) -> SyncUploadResult:
        raise RuntimeError("upload failed")

    exit_code = run_sync(
        config=config,
        stdout=stdout,
        stderr=stderr,
        snapshot_builder=fake_builder,
        uploader=failing_uploader,
    )

    assert exit_code == 1
    assert stdout.getvalue() == ""
    assert "upload failed" in stderr.getvalue()


def test_sync_entrypoint_shows_help_without_running_sync(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_run_sync() -> int:
        calls.append("called")
        return 0

    monkeypatch.setattr(cli, "run_sync", fake_run_sync)
    monkeypatch.setattr(cli.sys, "argv", ["ai-monitor-sync", "--help"])

    with pytest.raises(SystemExit) as excinfo:
        cli.sync_entrypoint()

    captured = capsys.readouterr()
    assert excinfo.value.code == 0
    assert calls == []
    assert "usage: ai-monitor-sync" in captured.out
