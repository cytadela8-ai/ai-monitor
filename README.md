# AI Monitor

AI Monitor is a local-first dashboard for tracking how much you use AI coding tools. It scans
local Codex and Claude logs, normalizes the data, and shows per-project usage summaries by day,
week, and month.

## Requirements

- Python 3.13
- `uv`

## Setup

```bash
uv sync --dev
```

## Run The App

```bash
uv run uvicorn ai_monitor.server.app:app --reload
```

The dashboard is served locally and reads Codex and Claude usage logs from the machine where it
runs.

## Refresh Data

Use the dashboard refresh button or the `POST /api/refresh` endpoint to rebuild normalized usage
data from the local logs.

## Planned Sources

- `~/.claude/history.jsonl`
- `~/.codex/history.jsonl`
- `~/.codex/sessions/**/*.jsonl`
