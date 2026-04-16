# Multi-Machine Auth And Remote Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add persistent admin sign-in for the whole dashboard, in-dashboard machine management
with setup instructions, authenticated remote snapshot uploads, a CLI-only sync entry point for
remote machines, and machine filtering without breaking the existing local-first ingestion
boundary.

**Architecture:** Keep provider parsing local to each machine. The server entry point owns the
dashboard, login/session flow, admin APIs, and machine-scoped SQLite storage. The client entry
point is a one-shot CLI command that builds a normalized snapshot locally and uploads it with a
machine API key.

**Tech Stack:** Python 3.13, FastAPI, Jinja2, SQLite, uv, pytest, ruff, ty

---

## File Structure

### New files

- none required by default

### Files to modify

- `README.md`
- `DEV.md`
- `.env.example`
- `ai_monitor/auth.py`
- `ai_monitor/config.py`
- `ai_monitor/server/app.py`
- `ai_monitor/server/admin_routes.py`
- `ai_monitor/server/routes.py`
- `ai_monitor/server/templates/index.html`
- `ai_monitor/server/static/app.css`
- `ai_monitor/server/static/app.js`
- `tests/conftest.py`
- `tests/server/test_admin_api.py`
- `tests/server/test_dashboard.py`
- `tests/server/test_metrics_api.py`

## Task 1: Add Session Auth And Protected Dashboard Coverage

**Files:**
- Modify: `ai_monitor/auth.py`
- Modify: `ai_monitor/server/app.py`
- Modify: `ai_monitor/server/routes.py`
- Modify: `tests/conftest.py`
- Modify: `tests/server/test_dashboard.py`
- Modify: `tests/server/test_metrics_api.py`

- [ ] **Step 1: Write failing tests for signed-out dashboard rendering, protected API behavior, and persistent session login**
- [ ] **Step 2: Run `uv run pytest tests/server/test_dashboard.py tests/server/test_metrics_api.py -q` and verify the new tests fail**
- [ ] **Step 3: Implement login, logout, signed session cookie handling, and route protection**
- [ ] **Step 4: Re-run `uv run pytest tests/server/test_dashboard.py tests/server/test_metrics_api.py -q` and verify the tests pass**

## Task 2: Convert Admin APIs To Session Auth

**Files:**
- Modify: `ai_monitor/server/admin_routes.py`
- Modify: `tests/server/test_admin_api.py`
- Modify: `tests/conftest.py`

- [ ] **Step 1: Write failing admin API tests for session-authenticated machine creation, revoke behavior, and sign-out behavior**
- [ ] **Step 2: Run `uv run pytest tests/server/test_admin_api.py -q` and verify the tests fail**
- [ ] **Step 3: Replace bearer-admin checks with session checks for dashboard admin endpoints**
- [ ] **Step 4: Re-run `uv run pytest tests/server/test_admin_api.py -q` and verify the tests pass**

## Task 3: Add Authenticated Machine Management UI

**Files:**
- Modify: `ai_monitor/server/routes.py`
- Modify: `ai_monitor/server/templates/index.html`
- Modify: `ai_monitor/server/static/app.css`
- Modify: `ai_monitor/server/static/app.js`
- Modify: `tests/server/test_dashboard.py`

- [ ] **Step 1: Write failing dashboard tests for login form rendering, signed-in dashboard rendering, and machine-management panel presence**
- [ ] **Step 2: Run `uv run pytest tests/server/test_dashboard.py -q` and verify the tests fail**
- [ ] **Step 3: Add the admin login surface, sign-out action, machine list, create flow, revoke controls, and one-time key reveal UI**
- [ ] **Step 4: Re-run `uv run pytest tests/server/test_dashboard.py -q` and verify the tests pass**

## Task 4: Add Client Setup Instruction Flow

**Files:**
- Modify: `ai_monitor/server/admin_routes.py`
- Modify: `ai_monitor/server/static/app.js`
- Modify: `ai_monitor/server/templates/index.html`
- Modify: `tests/server/test_admin_api.py`

- [ ] **Step 1: Write failing API or UI tests for the machine setup instruction payload and rendering**
- [ ] **Step 2: Run `uv run pytest tests/server/test_admin_api.py tests/server/test_dashboard.py -q` and verify the tests fail**
- [ ] **Step 3: Return setup instructions for minted machines and render copy-friendly sync instructions in the UI**
- [ ] **Step 4: Re-run `uv run pytest tests/server/test_admin_api.py tests/server/test_dashboard.py -q` and verify the tests pass**

## Task 5: Update Docs And Examples

**Files:**
- Modify: `README.md`
- Modify: `DEV.md`
- Modify: `.env.example`

- [ ] **Step 1: Update docs for admin sign-in, machine management in the dashboard, client sync usage, and cron usage**
- [ ] **Step 2: Confirm the examples match the implemented endpoints and env vars**

## Task 6: Verify The Whole Slice

**Files:**
- No new code files

- [ ] **Step 1: Run `uv run pytest tests/server/test_admin_api.py tests/server/test_metrics_api.py tests/server/test_dashboard.py -q`**
- [ ] **Step 2: Run `uv run ruff check .`**
- [ ] **Step 3: Run `uv run ty check`**
- [ ] **Step 4: Review changed docs and code for unnecessary complexity**
