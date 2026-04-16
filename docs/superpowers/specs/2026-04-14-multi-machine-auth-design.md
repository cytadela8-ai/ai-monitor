# Multi-Machine Auth And Remote Sync Design

## Goal

Extend AI Monitor so one main instance can aggregate usage from multiple machines. The main
instance serves the dashboard, stores data for all machines, requires admin sign-in for the whole
dashboard, authenticates remote uploads with machine API keys, and supports filtering metrics by
machine.

## Non-Goals

- No background scheduler inside the application
- No raw-log uploads to the server
- No incremental sync protocol
- No push-triggered refresh of remote machines from the server
- No multi-user role model beyond one admin secret

## User Requirements

- The main instance must accept usage data from different machines
- Each remote machine must authenticate with an API key
- API keys must be manageable from the main instance after bootstrap
- The whole dashboard must require admin sign-in
- Admin sign-in must persist in the browser across refreshes and later visits
- The dashboard must include a UI for creating, revoking, and viewing machine setup details
- Remote machines must run as a CLI-only sync client and must not run an HTTP server
- Sync must be safe under retries, refreshes, and local re-parsing
- The dashboard must support filtering by machine
- The main instance itself must appear as one normal machine in the shared model

## Architecture

The system has two explicit runtime entry points:

1. Server entry point
   - starts the FastAPI app
   - serves the login screen, authenticated dashboard, and JSON APIs
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

- Each remote machine gets exactly one active machine key
- The key determines which machine slice a snapshot replaces
- Machine metadata stores a human-readable label for filtering and status display
- Revoking a key disables future uploads from that machine without removing historical data

Two auth classes exist:

1. Bootstrap admin key
   - configured by environment variable on the server
   - used to sign in to the dashboard
   - used to mint and revoke machine keys through the UI and admin APIs
2. Machine API keys
   - minted by the server
   - shown once at creation time
   - stored as secure hashes
   - used only for machine snapshot uploads

### Admin Browser Session

The server issues a signed HTTP-only cookie after a successful admin login.

- entering the admin key once creates the session
- the session cookie is used for all dashboard page and dashboard API requests
- the session persists across page reloads and later browser visits until logout or expiry
- logout clears the cookie

The admin key itself must not live in browser JavaScript storage.

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

The database is machine-scoped.

### Machines

`machines` stores:

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

`machine_refresh_runs` stores:

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
- requires admin session
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

- `GET /`
  - returns the login screen when signed out
  - returns the dashboard shell when signed in
- `GET /api/metrics`
  - requires admin session
  - adds `machine` query parameter
  - includes machine filter options in the response
- `POST /api/refresh`
  - requires admin session
  - refreshes only the local server machine

### Session Endpoints

- `POST /api/session/login`
  - validates the bootstrap admin key
  - sets the signed admin session cookie
- `POST /api/session/logout`
  - clears the session cookie
- `GET /api/session`
  - returns current sign-in status for the browser

### Admin Endpoints

- `GET /api/admin/machines`
  - admin-session authenticated
  - returns machine metadata and status
- `POST /api/admin/machines`
  - admin-session authenticated
  - creates a new machine record and returns the plaintext API key once
- `POST /api/admin/machines/{machine_id}/revoke`
  - admin-session authenticated
  - marks the machine key inactive

### Ingest Endpoint

- `POST /api/ingest/snapshot`
  - machine authenticated
  - accepts a full normalized snapshot
  - replaces only the authenticated machine's data

The upload body contains normalized records and generation metadata only. The authenticated key
decides the target machine. The request body must not be trusted to choose the machine.

## Client CLI Design

The client does not expose a web server. It gets its own entry point and command surface.

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

The authenticated dashboard also gains an admin operations surface:

- sign-in form when not authenticated
- sign-out action when authenticated
- machine registry panel with create and revoke actions
- one-time display of the newly minted machine API key
- setup instructions for each machine, including required environment variables, sync command, and
  cron example

## Config Model

Server and client runtime behavior are selected by entry point, not by a shared mode flag.

### Server config

- database path
- local provider paths
- bootstrap admin key
- local machine label
- session signing secret or derivation source

### Client config

- server URL
- machine API key
- local provider paths

Example env files should document both sets of settings.

## Module Layout

- `ai_monitor/auth.py`
  - key hashing
  - admin session helpers
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
  - admin-session machine management APIs
- `ai_monitor/server/ingest_routes.py`
  - machine-authenticated snapshot ingest API

Extend:

- `ai_monitor/config.py`
- `ai_monitor/db/schema.py`
- `ai_monitor/db/queries.py`
- `ai_monitor/ingestion/service.py`
- `ai_monitor/server/app.py`
- `ai_monitor/server/routes.py`
- `ai_monitor/server/templates/index.html`
- `ai_monitor/server/static/app.css`
- `ai_monitor/server/static/app.js`

## Error Handling

- invalid admin login returns `401`
- missing admin session on dashboard APIs returns `401`
- missing admin session on `GET /` returns the login page instead of dashboard data
- invalid or revoked machine keys return `401` or `403` as appropriate
- malformed snapshot payloads return `422`
- snapshot replacement failures roll back the whole transaction
- client CLI failures include operation context and exit nonzero
- missing local source files still produce a successful empty snapshot, matching current local
  ingestion behavior

## Testing Strategy

### API Tests

- login success and failure behavior
- protected dashboard and API behavior without a session
- session persistence across multiple requests from the same client
- machine-key minting and revoke behavior
- snapshot upload auth enforcement
- snapshot upload replaces only the authenticated machine's data
- `/api/metrics` returns machine options and machine-filtered results

### CLI Tests

- sync command uploads normalized snapshots
- sync command exits nonzero on 401, 403, and network failure
- sync command output is concise and cron-friendly

### Frontend Tests

- login form rendering when signed out
- authenticated dashboard rendering when signed in
- admin machine-management panel rendering
- machine filter options render
- selected machine is carried into metrics requests
- all-machines mode renders machine column

## Docs Updates

Update:

- `README.md`
  - admin sign-in
  - server setup
  - machine key minting
  - client sync usage
  - cron example
- `DEV.md`
  - machine-scoped storage
  - auth and session flow
  - admin UI module boundaries
  - entry-point split
- `.env.example`
  - server and client variables
