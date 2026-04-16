from dataclasses import asdict, dataclass

HIDDEN_API_KEY = "<hidden: revoke and recreate to replace>"
CLAUDE_CONTAINER_PATH = "/host-home/.claude/history.jsonl"
CODEX_HISTORY_CONTAINER_PATH = "/host-home/.codex/history.jsonl"
CODEX_SESSIONS_CONTAINER_PATH = "/host-home/.codex/sessions"


@dataclass(frozen=True)
class ClientSetupPayload:
    client_image: str
    docker_command: str
    launch_script: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def _docker_command(server_url: str, client_image: str, api_key: str) -> str:
    return "\n".join(
        [
            "docker run --pull always --rm \\",
            f'  -e AI_MONITOR_SERVER_URL="{server_url}" \\',
            f'  -e AI_MONITOR_API_KEY="{api_key}" \\',
            f"  -e AI_MONITOR_CLAUDE_HISTORY_PATH={CLAUDE_CONTAINER_PATH} \\",
            f"  -e AI_MONITOR_CODEX_HISTORY_PATH={CODEX_HISTORY_CONTAINER_PATH} \\",
            f"  -e AI_MONITOR_CODEX_SESSIONS_ROOT={CODEX_SESSIONS_CONTAINER_PATH} \\",
            '  -v "$HOME/.claude:/host-home/.claude:ro" \\',
            '  -v "$HOME/.codex:/host-home/.codex:ro" \\',
            f'  "{client_image}"',
        ]
    )


def build_client_setup(
    server_url: str,
    client_image: str,
    api_key: str | None,
) -> ClientSetupPayload:
    """Build copyable Docker launch instructions for a remote client machine."""
    visible_api_key = api_key or HIDDEN_API_KEY
    docker_command = _docker_command(server_url, client_image, visible_api_key)
    launch_script = "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "",
            f'CLIENT_IMAGE="{client_image}"',
            f'AI_MONITOR_SERVER_URL="{server_url}"',
            f'AI_MONITOR_API_KEY="{visible_api_key}"',
            "",
            'docker pull "$CLIENT_IMAGE"',
            "",
            docker_command.replace(visible_api_key, '$AI_MONITOR_API_KEY').replace(
                client_image,
                "$CLIENT_IMAGE",
            ).replace(server_url, "$AI_MONITOR_SERVER_URL"),
        ]
    )
    return ClientSetupPayload(
        client_image=client_image,
        docker_command=docker_command,
        launch_script=launch_script,
    )
