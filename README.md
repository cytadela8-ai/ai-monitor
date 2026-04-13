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

If port `8000` is already in use, pick another one explicitly:

```bash
uv run uvicorn ai_monitor.server.app:app --reload --port 8001
```

Then open `http://127.0.0.1:8000` or the alternate port you selected. The app now initializes the
SQLite schema automatically and bootstraps the first refresh on initial load, so a fresh checkout
does not require a manual warm-up step.

## Refresh Data

Use the dashboard refresh button or the `POST /api/refresh` endpoint to rebuild normalized usage
data from the local logs. Aggregates are rebuilt into a local SQLite cache and then served to the
dashboard from there.

## Default Sources

- `~/.claude/history.jsonl`
- `~/.codex/history.jsonl`
- `~/.codex/sessions/**/*.jsonl`

If one of these sources is missing on the current machine, refresh still succeeds and ingests the
sources that are present.

## API Endpoints

- `GET /` dashboard
- `GET /api/metrics?period=day|week|month`
- `POST /api/refresh`
- `GET /health`
