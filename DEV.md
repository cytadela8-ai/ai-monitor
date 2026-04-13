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
4. FastAPI reads aggregate metrics for ledger rows and reads normalized base tables for
   filter-scoped summary totals and the daily heatmap.
5. The browser triggers the first refresh only when the cache is empty, so request handlers stay
   read-only and initial page rendering is not blocked by ingestion.

## Provider Boundaries

- `ClaudeProvider` reads Claude history and emits normalized conversations and prompt events.
- `CodexProvider` joins Codex history with session metadata to recover project paths.
- `IngestionService` does not know provider-specific file formats.
- `server` code does not read raw history files directly.

## Dashboard Notes

- The main surface is the project usage ledger. Totals, heatmap, and diagnostics are secondary
  support views rather than separate dashboard cards.
- `GET /api/metrics` also returns ranked project options for the current period/provider context so
  the client can keep the project picker stable and expose one-click project quick picks without
  recomputing rankings in the browser.
- `GET /api/metrics` also returns a filter-scoped `summary` object and a `heatmap_days` series.
  The summary stays fixed across day/week/month switches because it is computed from normalized
  conversations and prompt events rather than by summing grouped ledger rows.
- The daily heatmap is a 26-week, newest-first grid rendered entirely in the browser from API data.
  Each cell shows exact day statistics on hover or focus.
- The server enables gzip compression for larger text responses.
- Mobile adapts the ledger into stacked row cards using the same table data, avoiding horizontal
  scrolling while keeping the same metrics visible, including under enlarged text.
- The client keeps refresh state in the browser, exposes it through a live status region, and
  avoids unnecessary project-filter and table DOM rewrites when the rendered data has not changed.
