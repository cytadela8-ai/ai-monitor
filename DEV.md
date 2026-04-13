# Development Notes

## Architecture

The project is split into two main parts:

- `ai_monitor.ingestion`
  Reads raw local logs, normalizes provider-specific records, and rebuilds the SQLite cache.
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
    service.py
    providers/
      claude.py
      codex.py
  db/
    schema.py
    queries.py
  server/
    app.py
    routes.py
    templates/
    static/
tests/
  ingestion/
  server/
```

## Data Flow

1. Provider reads local source files.
2. Ingestion service normalizes records.
3. SQLite stores conversations, prompt events, and aggregate metrics.
4. FastAPI reads aggregate metrics for the dashboard.
5. The browser triggers the first refresh only when the cache is empty, so request handlers stay
   read-only and initial page rendering is not blocked by ingestion.

## Provider Boundaries

- `ClaudeProvider` reads Claude history and emits normalized conversations and prompt events.
- `CodexProvider` joins Codex history with session metadata to recover project paths.
- `IngestionService` does not know provider-specific file formats.
- `server` code does not read raw history files directly.

## Dashboard Notes

- The main surface is the project usage ledger. Totals, chart, and diagnostics are secondary
  support views rather than separate dashboard cards.
- `Activity Wave` is rendered with a pinned local `Chart.js 4.5.1` bundle in
  `ai_monitor/server/static/vendor/chart.umd.js` so the dashboard keeps a proper charting library
  without introducing a Node build step or external runtime dependency.
- Mobile adapts the ledger into stacked row cards using the same table data, avoiding horizontal
  scrolling while keeping the same metrics visible, including under enlarged text.
- The client keeps refresh state in the browser, exposes it through a live status region, and
  avoids unnecessary project-filter and table DOM rewrites when the rendered data has not changed.
