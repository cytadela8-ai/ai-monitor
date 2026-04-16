#!/usr/bin/env bash
set -euo pipefail

: "${AI_MONITOR_CLIENT_IMAGE:?Missing AI_MONITOR_CLIENT_IMAGE}"
: "${AI_MONITOR_SERVER_URL:?Missing AI_MONITOR_SERVER_URL}"
: "${AI_MONITOR_API_KEY:?Missing AI_MONITOR_API_KEY}"

docker pull "$AI_MONITOR_CLIENT_IMAGE"

docker run --pull always --rm \
  -e AI_MONITOR_SERVER_URL="$AI_MONITOR_SERVER_URL" \
  -e AI_MONITOR_API_KEY="$AI_MONITOR_API_KEY" \
  -e AI_MONITOR_CLAUDE_HISTORY_PATH=/host-home/.claude/history.jsonl \
  -e AI_MONITOR_CODEX_HISTORY_PATH=/host-home/.codex/history.jsonl \
  -e AI_MONITOR_CODEX_SESSIONS_ROOT=/host-home/.codex/sessions \
  -v "$HOME/.claude:/host-home/.claude:ro" \
  -v "$HOME/.codex:/host-home/.codex:ro" \
  "$AI_MONITOR_CLIENT_IMAGE"
