# AI Usage Dashboard Design

## Goal

Build a local-first web app with a Python backend that scans local Codex and Claude logs,
normalizes activity into a shared model, and presents per-project activity summaries by day,
week, and month.

## Non-Goals

- No cloud sync or multi-user support
- No import or upload flow
- No authentication layer
- No per-conversation dashboard views
- No background daemon unless later needed

## User Requirements

- Read Codex and Claude usage data from the machine where the app runs
- Associate activity with projects using a cleaned project name derived from the path
- Report, per project and time bucket, these metrics:
  - conversation count
  - text prompt count
  - slash command count
- Show daily, weekly, and monthly aggregates
- Keep log-fetching and processing logic decoupled from the web server so new data sources can
  be added later

## Source Observations

### Claude

`~/.claude/history.jsonl` contains prompt-like events with:

- `timestamp`
- `sessionId`
- `project`
- `display`

This is sufficient to classify user-entered events into text prompts and slash commands and to
associate them with a project path.

### Codex

`~/.codex/history.jsonl` contains user-entered text with:

- `session_id`
- `ts`
- `text`

Project context is not present there, but Codex session files under
`~/.codex/sessions/**/*.jsonl` include a `session_meta` event with a `cwd` field. The ingestion
path must join those sources by session identifier.

## Architecture

The application will have two hard boundaries:

1. Ingestion layer
   - Reads raw provider files
   - Normalizes them into a shared model
   - Writes normalized data and aggregates to a local SQLite database
2. Server layer
   - Serves JSON endpoints and dashboard assets
   - Reads only from the normalized database
   - Never parses provider logs directly

This boundary keeps the dashboard fast and stable even if raw provider formats evolve.

## Proposed Project Structure

```text
ai_monitor/
  ingestion/
    base.py
    models.py
    normalize.py
    service.py
    providers/
      claude.py
      codex.py
  server/
    app.py
    api/
      metrics.py
    templates/
    static/
  db/
    schema.py
    queries.py
  tests/
    ingestion/
    server/
docs/
  superpowers/
    specs/
      2026-04-13-ai-usage-dashboard-design.md
```

## Data Model

### Internal Conversation

Conversations stay in the normalized layer because they are required to count distinct
conversations correctly, even though they are not shown directly in the dashboard.

Fields:

- `provider`: `claude` or `codex`
- `external_id`: provider-specific session/conversation id
- `started_at`
- `project_path`
- `project_name`

### Internal Prompt Event

Each prompt-like user action becomes one normalized event:

- `provider`
- `conversation_id`
- `occurred_at`
- `project_path`
- `project_name`
- `event_type`: `text_prompt` or `slash_command`
- `raw_text`

### Aggregates

Aggregates are computed by:

- `project_name`
- `provider` (nullable for overall totals)
- `period_type`: `day`, `week`, `month`
- `period_start`

Metrics:

- `conversation_count`
- `text_prompt_count`
- `slash_command_count`

Unknown paths remain explicit as `unknown`. Project display names are derived from the basename
of the source path.

## Provider Model

Each provider implements a shared interface that returns normalized raw records before database
storage. The interface is intentionally narrow:

- discover available source files
- read user-entered events
- resolve session-to-project mapping
- emit normalized conversation and prompt-event records

Initial providers:

- `ClaudeProvider`
  - source: `~/.claude/history.jsonl`
  - project source: direct `project` field
- `CodexProvider`
  - source: `~/.codex/history.jsonl`
  - project source: `cwd` from session metadata in `~/.codex/sessions/**/*.jsonl`

This shape lets future providers be added without changing API handlers or dashboard code.

## Ingestion Flow

1. Discover source files for enabled providers
2. Read raw history/session records
3. Normalize provider-specific fields into shared conversation and prompt-event models
4. Classify each user event:
   - slash command if the text begins with `/`
   - otherwise text prompt
5. Derive `project_name` from the source path basename
6. Rebuild normalized tables in SQLite
7. Recompute aggregate tables or views
8. Store refresh metadata such as last run time and import counts

The first version can do a full rebuild on refresh. Incremental sync can be added later if
needed.

## Dashboard Views

### Filters

- period granularity: day, week, month
- project
- provider
- date range

### Main Views

- summary cards for the selected range:
  - conversations
  - text prompts
  - slash commands
- project activity table for the selected granularity
- time-series chart for the selected granularity
- provider comparison when more than one provider is in scope
- refresh status panel:
  - last refreshed at
  - providers scanned
  - source rows read
  - normalized rows written

## Backend Design

Use FastAPI for the backend because it gives a clean separation between:

- application startup
- API routes
- template/static serving
- future CLI hooks

Server responsibilities:

- trigger a refresh on demand
- return aggregate metrics from SQLite
- serve the dashboard

Ingestion responsibilities:

- file-system reads
- raw parsing
- provider-specific joins
- normalization
- aggregate refresh

## Frontend Design

The frontend should be lightweight and local-first. A server-rendered page plus a small amount of
JavaScript is sufficient for the first version.

The visual emphasis should be on:

- clear time-bucket switching
- readable project comparisons
- easy separation between text prompts and slash commands

The UI should avoid generic admin-dashboard styling and use a distinct, intentional visual system
while remaining simple to maintain.

## Error Handling

- Missing provider directories should not crash the app
- Malformed lines should be counted and surfaced in refresh diagnostics
- Unknown project data should be preserved as `unknown`
- File read and parse failures should include provider and path context
- Refresh failures should not corrupt the last known good dashboard state

## Testing Strategy

### Ingestion

- Claude prompt classification
- Codex session-to-project join behavior
- project-name derivation from paths
- aggregate generation by day, week, and month
- malformed-record handling
- empty-source handling

### Server

- metrics endpoints return expected aggregates
- refresh endpoint triggers rebuild and returns diagnostics
- filter handling for provider, project, and period

### Integration

- fixture-based end-to-end ingest from sample Codex and Claude logs into SQLite
- dashboard page renders expected summary values for a known fixture set

## Deployment And Publishing

The repository will be initialized locally and published to GitHub under the `cytadela8-ai`
account. The project will include:

- `README.md` with setup and run instructions
- `DEV.md` with architecture and file layout
- example configuration only if the final code requires user-configurable paths

## Open Decisions Already Resolved

- canonical project display: cleaned project name derived from path
- prompt metrics: track both text prompts and slash commands
- reporting level: per project and per time bucket, not per conversation views
- runtime model: personal dashboard reading local machine state directly

## Recommended First Implementation Slice

1. Create ingestion models and provider interfaces
2. Implement Claude and Codex providers against fixture files
3. Build SQLite schema and aggregate refresh logic
4. Expose aggregate endpoints in FastAPI
5. Build the initial dashboard with day/week/month filtering
6. Add manual refresh and diagnostics
