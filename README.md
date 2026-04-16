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

Both `ai-monitor-server` and `ai-monitor-sync` automatically load a `.env` file from the current
working directory. Process environment variables still override values from `.env`.

## Server Mode

```bash
cp .env.example .env
uv run ai-monitor-server
```

The server entry point:

- serves the login screen, authenticated dashboard, and JSON APIs
- reads the local machine's logs into the `main-server` machine slot by default
- lets you sign in with the admin key and manage remote machine keys from the UI
- accepts authenticated snapshot uploads from remote machines

Set `AI_MONITOR_ADMIN_KEY` and `AI_MONITOR_SESSION_SECRET` before exposing the server anywhere
beyond your own machine.

If port `8000` is already in use, set a different `AI_MONITOR_PORT`.

## Dashboard Sign-In And Machine Provisioning

Open the main instance in a browser and sign in with `AI_MONITOR_ADMIN_KEY`.

After sign-in, the dashboard includes a `Machine Access` panel where you can:

- create a machine key for a remote machine
- revoke a machine key
- view copyable setup instructions for running sync from that machine

When you create a machine key, copy it immediately. The plaintext key is shown only once.

## Client Mode

Remote machines do not run an HTTP server. They run one one-shot sync command:

```bash
uv run ai-monitor-sync
```

Set these client variables first:

- `AI_MONITOR_SERVER_URL`
- `AI_MONITOR_API_KEY`
- local provider paths if they differ from the defaults

The easiest way to provision `AI_MONITOR_API_KEY` is from the `Machine Access` panel on the main
instance.

The sync command reads local logs, builds a normalized snapshot, uploads it to the main instance,
prints one summary line, and exits.

## Docker

Build the server image:

```bash
docker build -t ai-monitor .
```

Run the server with an env file and a persistent database mount:

```bash
docker run --rm \
  -p 8000:8000 \
  --env-file .env \
  -e AI_MONITOR_DATABASE_PATH=/data/ai_monitor.db \
  -v "$(pwd)/data:/data" \
  ai-monitor
```

If the server container should also scan the host machine's local Claude and Codex logs, mount
those directories read-only and point the env vars at the mounted paths.

For remote machines, the admin panel now renders a Docker-only launch script that uses the client
image configured by `AI_MONITOR_CLIENT_IMAGE`. The published client image path is
`ghcr.io/cytadela8-ai/ai-monitor-client:latest`.

## Docker Compose On This Machine

This repo now includes a local `compose.yml` and a real `.env` for Docker-based server runs on
this machine.

Bring the server up:

```bash
docker compose up -d --build
```

The compose setup mounts:

- `./data` to persist the SQLite database
- `${HOME}/.claude` read-only to `/host-home/.claude`
- `${HOME}/.codex` read-only to `/host-home/.codex`

The checked-in `.env.example` remains the template, while the local `.env` is configured for the
container and ignored by git.

## Container Publishing

GitHub Actions publishes a server image to `ghcr.io/<owner>/<repo>` on:

- pushes to `main`
- version tags matching `v*`

GitHub Actions also publishes a client image to `ghcr.io/<owner>/<repo>-client` with the same
tag set: `main`, `latest`, commit SHA, and semver release tags.

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

- `GET /` login page or dashboard shell
- `GET /api/session`
- `POST /api/session/login`
- `POST /api/session/logout`
- `GET /api/metrics?period=day|week|month&machine=<label>`
- `POST /api/refresh`
- `GET /api/admin/machines`
- `POST /api/admin/machines`
- `POST /api/admin/machines/{machine_id}/revoke`
- `POST /api/ingest/snapshot`
- `GET /health`
