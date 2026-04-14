# Multi-Machine Auth And Remote Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add machine-scoped storage, authenticated remote snapshot uploads, a CLI-only sync
entry point for remote machines, and machine filtering in the dashboard without breaking the
existing local-first ingestion boundary.

**Architecture:** Keep provider parsing local to each machine. The server entry point owns the
dashboard, admin APIs, and machine-scoped SQLite storage. The client entry point is a one-shot
CLI command that builds a normalized snapshot locally and uploads it with a machine API key.

**Tech Stack:** Python 3.13, FastAPI, Jinja2, SQLite, uv, pytest, ruff, ty

---

## File Structure

### New files

- `.env.example`
- `ai_monitor/auth.py`
- `ai_monitor/cli.py`
- `ai_monitor/machines.py`
- `ai_monitor/ingestion/snapshots.py`
- `ai_monitor/server/admin_routes.py`
- `ai_monitor/server/ingest_routes.py`
- `tests/server/test_admin_api.py`
- `tests/server/test_ingest_api.py`
- `tests/test_cli.py`

### Files to modify

- `pyproject.toml`
- `README.md`
- `DEV.md`
- `ai_monitor/config.py`
- `ai_monitor/db/schema.py`
- `ai_monitor/db/queries.py`
- `ai_monitor/ingestion/models.py`
- `ai_monitor/ingestion/service.py`
- `ai_monitor/server/app.py`
- `ai_monitor/server/routes.py`
- `ai_monitor/server/templates/index.html`
- `ai_monitor/server/static/app.js`
- `tests/conftest.py`
- `tests/db/test_queries.py`
- `tests/server/test_metrics_api.py`

## Task 1: Add Machine-Scoped Schema And Query Coverage

**Files:**
- Modify: `ai_monitor/db/schema.py`
- Modify: `ai_monitor/db/queries.py`
- Modify: `tests/db/test_queries.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Write failing query tests for machine-scoped storage and filtering**
- [ ] **Step 2: Run `uv run pytest tests/db/test_queries.py -q` and verify the new tests fail for the expected reason**
- [ ] **Step 3: Add `machines`, `machine_refresh_runs`, and machine-scoped keys on normalized tables**
- [ ] **Step 4: Update query helpers to support machine filter options, machine-scoped refresh status, and all-machine aggregation**
- [ ] **Step 5: Re-run `uv run pytest tests/db/test_queries.py -q` and verify the tests pass**

## Task 2: Add Auth And Machine Management

**Files:**
- Create: `ai_monitor/auth.py`
- Create: `ai_monitor/machines.py`
- Create: `tests/server/test_admin_api.py`
- Modify: `ai_monitor/config.py`

- [ ] **Step 1: Write failing admin API tests for bootstrap auth, machine creation, and revoke behavior**
- [ ] **Step 2: Run `uv run pytest tests/server/test_admin_api.py -q` and verify the tests fail for the expected reason**
- [ ] **Step 3: Implement hashed key storage, bearer lookup, bootstrap admin auth, and machine CRUD helpers**
- [ ] **Step 4: Add server config fields for admin key and local machine label**
- [ ] **Step 5: Re-run `uv run pytest tests/server/test_admin_api.py -q` and verify the tests pass**

## Task 3: Split Snapshot Building From Persistence

**Files:**
- Create: `ai_monitor/ingestion/snapshots.py`
- Modify: `ai_monitor/ingestion/models.py`
- Modify: `ai_monitor/ingestion/service.py`
- Modify: `tests/ingestion/test_service.py`

- [ ] **Step 1: Write failing ingestion tests for building a normalized snapshot and replacing only one machine slice**
- [ ] **Step 2: Run `uv run pytest tests/ingestion/test_service.py -q` and verify the new tests fail**
- [ ] **Step 3: Introduce snapshot models and reusable local snapshot building from providers**
- [ ] **Step 4: Refactor ingestion persistence to replace one machine slice inside a transaction**
- [ ] **Step 5: Re-run `uv run pytest tests/ingestion/test_service.py -q` and verify the tests pass**

## Task 4: Add Snapshot Ingest API

**Files:**
- Create: `ai_monitor/server/ingest_routes.py`
- Create: `tests/server/test_ingest_api.py`
- Modify: `ai_monitor/server/app.py`

- [ ] **Step 1: Write failing API tests for machine-authenticated snapshot uploads and machine isolation**
- [ ] **Step 2: Run `uv run pytest tests/server/test_ingest_api.py -q` and verify the tests fail**
- [ ] **Step 3: Implement machine-authenticated snapshot upload and replacement**
- [ ] **Step 4: Wire the ingest router into the FastAPI app**
- [ ] **Step 5: Re-run `uv run pytest tests/server/test_ingest_api.py -q` and verify the tests pass**

## Task 5: Add CLI Entry Points

**Files:**
- Create: `ai_monitor/cli.py`
- Create: `tests/test_cli.py`
- Modify: `pyproject.toml`
- Modify: `ai_monitor/config.py`

- [ ] **Step 1: Write failing CLI tests for `ai-monitor-sync` request behavior and exit status**
- [ ] **Step 2: Run `uv run pytest tests/test_cli.py -q` and verify the tests fail**
- [ ] **Step 3: Add separate server and sync entry points, with the client building and uploading snapshots without starting an HTTP server**
- [ ] **Step 4: Re-run `uv run pytest tests/test_cli.py -q` and verify the tests pass**

## Task 6: Add Machine Filter To Metrics API And Dashboard

**Files:**
- Modify: `ai_monitor/server/routes.py`
- Modify: `ai_monitor/server/templates/index.html`
- Modify: `ai_monitor/server/static/app.js`
- Modify: `tests/server/test_metrics_api.py`
- Modify: `tests/server/test_dashboard.py`

- [ ] **Step 1: Write failing tests for `machine` query filtering and machine option payloads**
- [ ] **Step 2: Run `uv run pytest tests/server/test_metrics_api.py tests/server/test_dashboard.py -q` and verify the tests fail**
- [ ] **Step 3: Extend metrics responses and dashboard controls for machine filtering**
- [ ] **Step 4: Re-run `uv run pytest tests/server/test_metrics_api.py tests/server/test_dashboard.py -q` and verify the tests pass**

## Task 7: Update Docs And Examples

**Files:**
- Create: `.env.example`
- Modify: `README.md`
- Modify: `DEV.md`

- [ ] **Step 1: Add failing documentation presence assertions if needed**
- [ ] **Step 2: Update docs for server entry point, client sync entry point, machine key management, and cron usage**
- [ ] **Step 3: Add `.env.example` for server and client configuration**
- [ ] **Step 4: Run doc-adjacent checks that touch changed code paths**

## Task 8: Verify The Whole Slice

**Files:**
- No new code files

- [ ] **Step 1: Run `uv run pytest tests/db/test_queries.py tests/ingestion/test_service.py tests/server/test_admin_api.py tests/server/test_ingest_api.py tests/server/test_metrics_api.py tests/server/test_dashboard.py tests/test_cli.py -q`**
- [ ] **Step 2: Run `uv run ruff check .`**
- [ ] **Step 3: Run `uv run ty check`**
- [ ] **Step 4: Review changed docs and code for unnecessary complexity**
