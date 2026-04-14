# AI Monitor

AI Monitor is a local-first dashboard for tracking how much you use AI coding tools. It scans
local Codex and Claude logs, normalizes the data, and shows per-project usage summaries by day,
week, and month. One main instance can also collect normalized snapshots from other machines with
per-machine API keys.

## Requirements

- Python 3.13
- `uv`

## Setup

```bash
uv sync --dev
```

## Server Mode

```bash
cp .env.example .env
uv run ai-monitor-server
```

The server entry point:

- serves the dashboard and JSON APIs
- reads the local machine's logs into the `main-server` machine slot by default
- exposes admin endpoints for minting and revoking machine API keys
- accepts authenticated snapshot uploads from remote machines

Set `AI_MONITOR_ADMIN_KEY` before exposing the server anywhere beyond your own machine.

If port `8000` is already in use, set a different `AI_MONITOR_PORT`.

## Client Mode

Remote machines do not run an HTTP server. They run one one-shot sync command:

```bash
uv run ai-monitor-sync
```

Set these client variables first:

- `AI_MONITOR_SERVER_URL`
- `AI_MONITOR_API_KEY`
- local provider paths if they differ from the defaults

The sync command reads local logs, builds a normalized snapshot, uploads it to the main instance,
prints one summary line, and exits. It is designed for cron or systemd timers rather than running
its own scheduler.

Example cron entry:

```bash
0 * * * * cd /path/to/ai-monitor && uv run ai-monitor-sync
```

Then open `http://127.0.0.1:8000` or the host and port you configured. The app initializes the
SQLite schema automatically. If the cache is empty, the page loads immediately and starts the
first local scan for the local machine in the background, so a fresh checkout does not require a
manual warm-up step and the first request does not block on ingestion.

## Refresh Data

Use the dashboard refresh button or the `POST /api/refresh` endpoint to rebuild normalized usage
data for the local server machine only. Remote machines update by running `ai-monitor-sync`.
Aggregates are rebuilt into one SQLite cache with a separate slice per machine and then served to
the dashboard from there. On narrow screens, the project ledger collapses into stacked row cards
instead of relying on horizontal scrolling, and the status rail announces scan progress as the
local cache loads or refreshes. The totals band reflects the active machine, project, and tool
filters, so it stays fixed when you switch the ledger between day, week, and month groupings. The
right-side panel is a vertical daily activity heatmap with newest weeks at the top and exact
per-day counts on hover or keyboard focus. The project picker is ranked by recent activity, the
toolbar exposes one-click project quick picks for the most active current projects, and text
responses are gzip-compressed by the FastAPI app to reduce initial transfer size.

## Default Sources

- `~/.claude/history.jsonl`
- `~/.codex/history.jsonl`
- `~/.codex/sessions/**/*.jsonl`

If one of these sources is missing on the current machine, refresh still succeeds and ingests the
sources that are present.

## API Endpoints

- `GET /` dashboard
- `GET /api/metrics?period=day|week|month&machine=<label>`
- `POST /api/refresh`
- `GET /api/admin/machines`
- `POST /api/admin/machines`
- `POST /api/admin/machines/{machine_id}/revoke`
- `POST /api/ingest/snapshot`
- `GET /health`
