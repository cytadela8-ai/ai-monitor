# Multi-Machine Auth And Remote Sync Design

## Goal

Extend AI Monitor so one main instance can aggregate usage from multiple machines. The main
instance serves the dashboard, stores data for all machines, authenticates remote uploads with API
keys, and supports filtering metrics by machine.

## Non-Goals

- No background scheduler inside the application
- No dashboard login flow for human viewers
- No raw-log uploads to the server
- No incremental sync protocol
- No push-triggered refresh of remote machines from the server

## User Requirements

- The main instance must accept usage data from different machines
- Each remote machine must authenticate with an API key
- API keys must be manageable from the main instance after bootstrap
- Remote machines must run as a CLI-only sync client and must not run an HTTP server
- Sync must be safe under retries, refreshes, and local re-parsing
- The dashboard must support filtering by machine
- The main instance itself must appear as one normal machine in the shared model

## Architecture

The system gains two explicit runtime entry points:

1. Server entry point
   - starts the FastAPI app
   - serves the dashboard and JSON APIs
   - ingests local logs for the server machine
   - accepts authenticated snapshot uploads from remote machines
2. Client entry point
   - runs as a one-shot CLI command
   - reads local logs on that machine
   - normalizes them using the same ingestion logic as local refresh
   - uploads a full snapshot to the main instance
   - exits with a success or failure status for cron or systemd use

The ingestion boundary remains intact:

- raw Codex and Claude parsing stays local to the machine that owns the logs
- the central server only stores normalized records and aggregates
- HTTP handlers never parse raw provider files

## Identity And Auth

Machine identity is the machine API key.

- Each machine gets exactly one active machine key
- The key determines which machine slice a snapshot replaces
- Machine metadata stores a human-readable label for filtering and status display
- Revoking a key disables future uploads from that machine without removing historical data

Two auth classes exist:

1. Bootstrap admin key
   - configured by environment variable on the server
   - used to mint and revoke machine keys
2. Machine API keys
   - minted by the server
   - shown once at creation time
   - stored as secure hashes
   - used only for machine snapshot uploads

## Sync Model

Remote sync uses full normalized snapshots, not deltas.

Each client sync:

1. loads local provider data
2. normalizes conversations and prompt events
3. sends the full normalized snapshot to the main instance
4. the server replaces only that machine's existing normalized rows inside one transaction

This choice is intentional:

- retries are idempotent
- reinstalls and local cache loss are harmless
- a client can recover by re-sending its full view
- the server never has to reconcile partial event streams or cursors

## Storage Model

The database becomes machine-scoped.

### Machines

Add a `machines` table with:

- `id`
- `label`
- `api_key_hash`
- `is_local`
- `is_active`
- `created_at`
- `last_seen_at`
- `last_refresh_at`
- `last_refresh_source`

`is_local` marks the main instance's own machine record.

### Refresh Runs

Replace the single global refresh history with machine-scoped refresh history:

- `machine_refresh_runs`
  - `id`
  - `machine_id`
  - `refreshed_at`
  - `refresh_source`
  - `provider_count`
  - `conversation_count`
  - `prompt_event_count`

### Normalized Tables

Add `machine_id` to:

- `conversations`
- `prompt_events`
- `aggregate_metrics`

Primary keys become machine-scoped:

- `conversations`: `(machine_id, provider, external_id)`
- `aggregate_metrics`: `(machine_id, period_type, period_start, project_name, provider)`

## Refresh Semantics

Refresh is no longer global.

### Server local refresh

- triggered by `POST /api/refresh`
- rebuilds only the local server machine's slice from local files
- does not touch remote machine data

### Remote snapshot upload

- triggered by the client CLI
- authenticated by the machine API key
- replaces only that remote machine's slice
- updates only that machine's refresh metadata

This prevents one machine from deleting or stale-overwriting another machine's data.

## API Design

### Existing Endpoints

- `GET /api/metrics`
  - add `machine` query parameter
  - include machine filter options in the response
- `POST /api/refresh`
  - refreshes only the local server machine

### New Admin Endpoints

- `GET /api/admin/machines`
  - bootstrap-admin authenticated
  - returns machine metadata and status
- `POST /api/admin/machines`
  - bootstrap-admin authenticated
  - creates a new machine record and returns the plaintext API key once
- `POST /api/admin/machines/{machine_id}/revoke`
  - bootstrap-admin authenticated
  - marks the machine key inactive

### New Ingest Endpoint

- `POST /api/ingest/snapshot`
  - machine authenticated
  - accepts a full normalized snapshot
  - replaces only the authenticated machine's data

The upload body should contain normalized records and generation metadata only. The authenticated
key decides the target machine. The request body must not be trusted to choose the machine.

## Client CLI Design

The client must not expose a web server. It gets its own entry point and command surface.

Recommended commands:

- `ai-monitor-server`
  - runs the FastAPI app
- `ai-monitor-sync`
  - one-shot local read and remote push

`ai-monitor-sync` configuration:

- server URL
- machine API key
- local Codex and Claude source paths

Behavior:

1. load local provider data
2. build a normalized snapshot in memory
3. upload it with bearer auth
4. print a concise summary
5. exit nonzero on auth, network, or server failure

This makes the client suitable for cron:

```bash
0 * * * * /path/to/uv run ai-monitor-sync
```

## Dashboard Behavior

Filtering gains a machine dimension.

Filters:

- period
- machine
- project
- provider

Rules:

- the default machine filter is "All Machines"
- when one machine is selected, all summaries and the heatmap show only that machine's data
- when all machines are selected, metrics combine across machines
- the ledger includes a machine column only in the all-machines view so combined rows remain
  intelligible without making the single-machine view noisier

The diagnostics rail should expose:

- selected machine status if one machine is filtered
- total known machines
- most recent refresh metadata

## Config Model

Server and client runtime behavior should be selected by entry point, not by a shared mode flag.

### Server config

- database path
- local provider paths
- bootstrap admin key
- local machine label

### Client config

- server URL
- machine API key
- local provider paths

Example env files should document both sets of settings.

## Module Layout

Add focused modules instead of overloading the current files.

- `ai_monitor/auth.py`
  - key hashing
  - bearer-token lookup helpers
- `ai_monitor/machines.py`
  - machine CRUD
  - key creation and revoke operations
  - refresh metadata updates
- `ai_monitor/ingestion/snapshots.py`
  - snapshot models
  - snapshot building from providers
- `ai_monitor/cli.py`
  - CLI entry points and argument parsing
- `ai_monitor/server/admin_routes.py`
  - admin-authenticated machine management APIs
- `ai_monitor/server/ingest_routes.py`
  - machine-authenticated snapshot ingest API

Extend:

- `ai_monitor/config.py`
- `ai_monitor/db/schema.py`
- `ai_monitor/db/queries.py`
- `ai_monitor/ingestion/service.py`
- `ai_monitor/server/app.py`
- `ai_monitor/server/routes.py`
- `ai_monitor/server/static/app.js`
- `ai_monitor/server/templates/index.html`

## Error Handling

- invalid admin or machine bearer tokens return `401`
- revoked machine keys return `403`
- malformed snapshot payloads return `422`
- snapshot replacement failures roll back the whole transaction
- client CLI failures include operation context and exit nonzero
- missing local source files still produce a successful empty snapshot, matching current local
  ingestion behavior

## Testing Strategy

### Database And Query Tests

- machine-scoped inserts and replacements
- all-machine aggregation correctness
- machine filter correctness
- local machine refresh isolation

### API Tests

- admin auth enforcement
- machine-key minting and revoke behavior
- snapshot upload auth enforcement
- snapshot upload replaces only the authenticated machine's data
- `/api/metrics` returns machine options and machine-filtered results

### CLI Tests

- sync command uploads normalized snapshots
- sync command exits nonzero on 401, 403, and network failure
- sync command output is concise and cron-friendly

### Frontend Tests

- machine filter options render
- selected machine is carried into metrics requests
- all-machines mode renders machine column

## Docs Updates

Update:

- `README.md`
  - server setup
  - machine key minting
  - client sync usage
  - cron example
- `DEV.md`
  - machine-scoped storage
  - auth and admin modules
  - entry-point split
- `.env.example`
  - server and client variables
