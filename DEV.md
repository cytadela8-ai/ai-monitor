# Development Notes

## Architecture

The project is split into two main parts:

- `ai_monitor.ingestion`
  Reads raw local logs, normalizes provider-specific records, and rebuilds one machine slice in
  the SQLite cache.
- `ai_monitor.server`
  Serves the dashboard and API endpoints by reading normalized data only.

The server must not parse raw Codex or Claude files directly. All log processing belongs in the
ingestion layer so new providers can be added without changing the HTTP layer.

## Planned Layout

```text
ai_monitor/
  ingestion/
    base.py
    models.py
    path_utils.py
    snapshots.py
    service.py
  providers/
      claude.py
      codex.py
  db/
    schema.py
    queries.py
  auth.py
  machines.py
  cli.py
  server/
    app.py
    admin_routes.py
    ingest_routes.py
    routes.py
    templates/
    static/
tests/
  ingestion/
  server/
```

## Data Flow

1. Provider reads local source files.
2. Ingestion service builds a normalized snapshot.
3. SQLite stores conversations, prompt events, and aggregate metrics in a machine-scoped slice.
4. FastAPI reads aggregate metrics for ledger rows and reads normalized base tables for
   machine-scoped summary totals and the daily heatmap.
5. The browser triggers the first refresh only when the local machine slice is empty, so request
   handlers stay
   read-only and initial page rendering is not blocked by ingestion.

## Multi-Machine Model

- `machines` stores one row per machine identity, with the remote machine identity defined by the
  machine API key.
- `machine_refresh_runs` records per-machine refresh and upload history.
- `conversations`, `prompt_events`, and `aggregate_metrics` all carry `machine_id`.
- Local refresh replaces only the local machine slice.
- Remote sync replaces only the authenticated remote machine slice.
- The dashboard can show all machines together or filter down to one machine label.

## Session Auth

- The whole dashboard requires admin sign-in.
- `AI_MONITOR_ADMIN_KEY` is the root credential for browser sign-in.
- The server sets a signed HTTP-only session cookie after successful login.
- Dashboard APIs and admin APIs require that session cookie.
- Remote snapshot ingest stays machine-key based and does not use the admin session.

## Provider Boundaries

- `ClaudeProvider` reads Claude history and emits normalized conversations and prompt events.
- `CodexProvider` joins Codex history with session metadata to recover project paths.
- `IngestionService` does not know provider-specific file formats.
- `server` code does not read raw history files directly.
- `ai-monitor-sync` reuses the same provider and normalization code as local refresh instead of
  introducing a second parsing path.

## Auth And Entry Points

- `ai-monitor-server` starts the FastAPI app and uses the bootstrap admin key from config to guard
  dashboard sign-in and machine-management APIs.
- `ai-monitor-sync` is a CLI-only entry point. It never runs an HTTP listener.
- `ai_monitor.config` automatically loads `.env` from the current working directory before reading
  server or client configuration, while keeping explicit process env values higher priority.
- `ai_monitor.auth` hashes generated machine keys.
- `ai_monitor.auth` also manages admin session helpers.
- `ai_monitor.machines` owns local machine creation, machine-key minting, revoke operations, and
  machine-key authentication.

## Packaging And CI

- `Dockerfile` builds a server-only image and defaults to `ai-monitor-server`.
- `Dockerfile.client` builds a client-only image and defaults to `ai-monitor-sync`.
- `.dockerignore` keeps local databases, tests, screenshots, and caches out of the image context.
- `compose.yml` is the local Docker launch path for this machine. It mounts the host Claude and
  Codex directories read-only and persists the SQLite database in `./data`.
- `ai_monitor.server.client_setup` builds the Docker client command and launcher script shown in
  the admin panel.
- `scripts/run-client-sync.sh` is the shell version of the same Docker-only client launch flow.
- `.github/workflows/publish-image.yml` publishes the Docker image to GHCR on pushes to `main`
  and tags matching `v*`, for both server and client images.

## Dashboard Notes

- The main surface is the project usage ledger. Totals, heatmap, and diagnostics are secondary
  support views rather than separate dashboard cards.
- Signed-out users see a login screen instead of the dashboard shell.
- Signed-in users also get a `Machine Access` panel for provisioning remote machines and copying
  sync instructions.
- The toolbar now includes a machine filter. In the all-machines view, the ledger includes a
  machine column so combined rows stay intelligible.
- `GET /api/metrics` also returns ranked project options for the current period/provider context so
  the client can keep the project picker stable and expose one-click project quick picks without
  recomputing rankings in the browser.
- `GET /api/metrics` also returns a filter-scoped `summary` object and a `heatmap_days` series.
  The summary stays fixed across day/week/month switches because it is computed from normalized
  conversations and prompt events rather than by summing grouped ledger rows.
- `GET /api/metrics` also returns machine options so the browser can keep the machine filter in
  sync with the server-side machine registry.
- The daily heatmap is a 26-week, newest-first grid rendered entirely in the browser from API data.
  Each cell shows exact day statistics on hover or focus.
- The server enables gzip compression for larger text responses.
- Mobile adapts the ledger into stacked row cards using the same table data, avoiding horizontal
  scrolling while keeping the same metrics visible, including under enlarged text.
- The client keeps refresh state in the browser, exposes it through a live status region, and
  avoids unnecessary project-filter and table DOM rewrites when the rendered data has not changed.
