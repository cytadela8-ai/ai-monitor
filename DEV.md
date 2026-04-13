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

## Provider Boundaries

- `ClaudeProvider` reads Claude history and emits normalized conversations and prompt events.
- `CodexProvider` joins Codex history with session metadata to recover project paths.
- `IngestionService` does not know provider-specific file formats.
- `server` code does not read raw history files directly.
