import argparse
import json
import sys
from collections.abc import Callable
from dataclasses import dataclass
from typing import TextIO
from urllib import error, request

from ai_monitor.config import ClientConfig
from ai_monitor.ingestion.providers.claude import ClaudeProvider
from ai_monitor.ingestion.providers.codex import CodexProvider
from ai_monitor.ingestion.snapshots import UsageSnapshot, build_snapshot


@dataclass(frozen=True)
class SyncUploadResult:
    conversation_count: int
    prompt_event_count: int
    provider_count: int


def _build_sync_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-monitor-sync",
        description="Read local AI usage logs and push a full snapshot to the server.",
    )
    return parser


def build_client_snapshot(config: ClientConfig) -> UsageSnapshot:
    providers = [
        ClaudeProvider(history_path=config.claude_history_path),
        CodexProvider(
            history_path=config.codex_history_path,
            sessions_root=config.codex_sessions_root,
        ),
    ]
    return build_snapshot(providers)


def _snapshot_payload(snapshot: UsageSnapshot) -> bytes:
    body = {
        "generated_at": snapshot.generated_at.isoformat(),
        "providers": list(snapshot.providers),
        "conversations": [
            {
                "provider": row.provider,
                "external_id": row.external_id,
                "started_at": row.started_at.isoformat(),
                "project_path": row.project_path,
                "project_name": row.project_name,
            }
            for row in snapshot.conversations
        ],
        "prompt_events": [
            {
                "provider": row.provider,
                "external_conversation_id": row.external_conversation_id,
                "occurred_at": row.occurred_at.isoformat(),
                "project_path": row.project_path,
                "project_name": row.project_name,
                "event_type": row.event_type,
                "raw_text": row.raw_text,
            }
            for row in snapshot.prompt_events
        ],
    }
    return json.dumps(body).encode("utf-8")


def upload_snapshot(
    server_url: str,
    api_key: str,
    snapshot: UsageSnapshot,
) -> SyncUploadResult:
    http_request = request.Request(
        url=f"{server_url}/api/ingest/snapshot",
        data=_snapshot_payload(snapshot),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with request.urlopen(http_request) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return SyncUploadResult(
        conversation_count=int(payload["conversation_count"]),
        prompt_event_count=int(payload["prompt_event_count"]),
        provider_count=int(payload["provider_count"]),
    )


def run_sync(
    config: ClientConfig | None = None,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
    snapshot_builder: Callable[[], UsageSnapshot] | None = None,
    uploader: Callable[[str, str, UsageSnapshot], SyncUploadResult] | None = None,
) -> int:
    active_config = config or ClientConfig.from_env()
    out = stdout or sys.stdout
    err = stderr or sys.stderr
    builder = snapshot_builder or (lambda: build_client_snapshot(active_config))
    upload = uploader or upload_snapshot

    try:
        result = upload(active_config.server_url, active_config.api_key, builder())
    except (RuntimeError, ValueError, error.URLError, error.HTTPError) as exc:
        err.write(f"Sync failed: {exc}\n")
        return 1

    out.write(
        "Synced "
        f"{result.conversation_count} conversations and "
        f"{result.prompt_event_count} prompt events across "
        f"{result.provider_count} providers.\n"
    )
    return 0


def sync_entrypoint() -> None:
    _build_sync_parser().parse_args()
    raise SystemExit(run_sync())
