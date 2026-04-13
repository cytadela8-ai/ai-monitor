# AI Usage Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a local-first Python web app that ingests Codex and Claude logs from the host
machine, normalizes them into a shared SQLite model, and serves a dashboard with per-project
conversation, text prompt, and slash command counts by day, week, and month.

**Architecture:** Separate the system into an ingestion package and a server package. The
ingestion package owns all filesystem access, provider parsing, normalization, and aggregate
rebuilds. The server package only reads normalized data and exposes refresh and metrics endpoints
plus the dashboard UI.

**Tech Stack:** Python 3.13, FastAPI, Jinja2, SQLite, uv, ruff, ty, pytest

---

## File Structure

### New files

- `pyproject.toml`
- `.gitignore`
- `README.md`
- `DEV.md`
- `ai_monitor/__init__.py`
- `ai_monitor/config.py`
- `ai_monitor/ingestion/__init__.py`
- `ai_monitor/ingestion/base.py`
- `ai_monitor/ingestion/models.py`
- `ai_monitor/ingestion/path_utils.py`
- `ai_monitor/ingestion/providers/__init__.py`
- `ai_monitor/ingestion/providers/claude.py`
- `ai_monitor/ingestion/providers/codex.py`
- `ai_monitor/ingestion/service.py`
- `ai_monitor/db/__init__.py`
- `ai_monitor/db/schema.py`
- `ai_monitor/db/queries.py`
- `ai_monitor/server/__init__.py`
- `ai_monitor/server/app.py`
- `ai_monitor/server/routes.py`
- `ai_monitor/server/templates/index.html`
- `ai_monitor/server/static/app.css`
- `ai_monitor/server/static/app.js`
- `tests/conftest.py`
- `tests/fixtures/claude/history.jsonl`
- `tests/fixtures/codex/history.jsonl`
- `tests/fixtures/codex/sessions/2026/04/01/rollout-sample.jsonl`
- `tests/ingestion/test_path_utils.py`
- `tests/ingestion/test_claude_provider.py`
- `tests/ingestion/test_codex_provider.py`
- `tests/ingestion/test_service.py`
- `tests/server/test_metrics_api.py`
- `tests/server/test_dashboard.py`

### Existing files to keep unchanged

- `docs/superpowers/specs/2026-04-13-ai-usage-dashboard-design.md`

## Task 1: Project Bootstrap And Tooling

**Files:**
- Create: `pyproject.toml`
- Create: `.gitignore`
- Create: `ai_monitor/__init__.py`
- Create: `README.md`
- Create: `DEV.md`

- [ ] **Step 1: Write the failing packaging and docs test**

```python
from pathlib import Path


def test_project_bootstrap_files_exist() -> None:
    required = [
        "pyproject.toml",
        ".gitignore",
        "README.md",
        "DEV.md",
        "ai_monitor/__init__.py",
    ]

    missing = [path for path in required if not Path(path).exists()]
    assert missing == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/ingestion/test_bootstrap.py -q`
Expected: FAIL because the files do not exist yet.

- [ ] **Step 3: Add project metadata and base docs**

```toml
[project]
name = "ai-monitor"
version = "0.1.0"
requires-python = ">=3.13"
dependencies = [
  "fastapi==...",
  "jinja2==...",
  "uvicorn==...",
]

[dependency-groups]
dev = [
  "pytest==...",
  "ruff==...",
  "ty==...",
  "httpx==...",
]

[tool.ruff]
line-length = 100

[tool.ty.rules]
unresolved-import = "error"
```

```gitignore
.venv/
__pycache__/
.pytest_cache/
.ruff_cache/
.ty/
ai_monitor.db
```

`README.md` should cover:
- what the app does
- how to create the venv with `uv`
- how to run the server
- how to refresh usage data

`DEV.md` should cover:
- package layout
- ingestion/server separation
- database and aggregate responsibilities

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/ingestion/test_bootstrap.py -q`
Expected: PASS

- [ ] **Step 5: Verify tooling configuration**

Run: `uv run ruff check .`
Expected: exit 0

Run: `uv run ty check`
Expected: exit 0

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore README.md DEV.md ai_monitor/__init__.py tests/ingestion/test_bootstrap.py
git commit -m "chore: bootstrap AI monitor project"
```

## Task 2: Core Domain Models And Project Name Normalization

**Files:**
- Create: `ai_monitor/ingestion/models.py`
- Create: `ai_monitor/ingestion/path_utils.py`
- Test: `tests/ingestion/test_path_utils.py`

- [ ] **Step 1: Write the failing normalization tests**

```python
def test_project_name_uses_path_basename() -> None:
    assert derive_project_name("/home/ubuntu/zk-chains-registry") == "zk-chains-registry"


def test_project_name_handles_empty_path() -> None:
    assert derive_project_name(None) == "unknown"


def test_project_name_handles_root_like_values() -> None:
    assert derive_project_name("/") == "unknown"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/ingestion/test_path_utils.py -q`
Expected: FAIL because the helper does not exist yet.

- [ ] **Step 3: Implement minimal models and helpers**

```python
from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePath


@dataclass(frozen=True)
class ConversationRecord:
    provider: str
    external_id: str
    started_at: datetime
    project_path: str | None
    project_name: str


@dataclass(frozen=True)
class PromptEventRecord:
    provider: str
    external_conversation_id: str
    occurred_at: datetime
    project_path: str | None
    project_name: str
    event_type: str
    raw_text: str


def derive_project_name(project_path: str | None) -> str:
    if not project_path:
        return "unknown"
    name = PurePath(project_path).name
    return name or "unknown"
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/ingestion/test_path_utils.py -q`
Expected: PASS

- [ ] **Step 5: Run targeted quality checks**

Run: `uv run ruff check ai_monitor/ingestion tests/ingestion/test_path_utils.py`
Expected: exit 0

- [ ] **Step 6: Commit**

```bash
git add ai_monitor/ingestion/models.py ai_monitor/ingestion/path_utils.py tests/ingestion/test_path_utils.py
git commit -m "feat: add ingestion core models"
```

## Task 3: Provider Interface And Claude Provider

**Files:**
- Create: `ai_monitor/ingestion/base.py`
- Create: `ai_monitor/ingestion/providers/claude.py`
- Create: `tests/fixtures/claude/history.jsonl`
- Test: `tests/ingestion/test_claude_provider.py`

- [ ] **Step 1: Write the failing Claude provider tests**

```python
def test_claude_provider_reads_text_and_slash_events() -> None:
    provider = ClaudeProvider(history_path=fixture_path("claude/history.jsonl"))

    bundle = provider.load()

    assert bundle.conversation_count == 2
    assert [event.event_type for event in bundle.prompt_events] == [
        "text_prompt",
        "slash_command",
        "text_prompt",
    ]
    assert {event.project_name for event in bundle.prompt_events} == {"zk-chains-registry"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/ingestion/test_claude_provider.py -q`
Expected: FAIL because the provider does not exist yet.

- [ ] **Step 3: Implement the base interface and Claude provider**

```python
class Provider(Protocol):
    def load(self) -> ProviderLoadResult: ...
```

Claude provider responsibilities:
- read each JSONL line
- use `sessionId` as the external conversation id
- use `display` as the raw text
- classify slash commands by leading `/`
- use `project` as the source project path
- derive `project_name`
- use the earliest prompt timestamp per session as `started_at`

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/ingestion/test_claude_provider.py -q`
Expected: PASS

- [ ] **Step 5: Run targeted quality checks**

Run: `uv run ruff check ai_monitor/ingestion/providers/claude.py tests/ingestion/test_claude_provider.py`
Expected: exit 0

- [ ] **Step 6: Commit**

```bash
git add ai_monitor/ingestion/base.py ai_monitor/ingestion/providers/claude.py tests/fixtures/claude/history.jsonl tests/ingestion/test_claude_provider.py
git commit -m "feat: add Claude history ingestion"
```

## Task 4: Codex Provider With Session Metadata Join

**Files:**
- Create: `ai_monitor/ingestion/providers/codex.py`
- Create: `tests/fixtures/codex/history.jsonl`
- Create: `tests/fixtures/codex/sessions/2026/04/01/rollout-sample.jsonl`
- Test: `tests/ingestion/test_codex_provider.py`

- [ ] **Step 1: Write the failing Codex provider tests**

```python
def test_codex_provider_joins_history_with_session_cwd() -> None:
    provider = CodexProvider(
        history_path=fixture_path("codex/history.jsonl"),
        sessions_root=fixture_path("codex/sessions"),
    )

    bundle = provider.load()

    assert bundle.conversation_count == 1
    assert bundle.conversations[0].project_name == "zksync-prividium"
    assert [event.event_type for event in bundle.prompt_events] == [
        "text_prompt",
        "slash_command",
    ]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/ingestion/test_codex_provider.py -q`
Expected: FAIL because the provider does not exist yet.

- [ ] **Step 3: Implement minimal Codex provider**

Implementation details:
- read `~/.codex/history.jsonl`
- index session metadata from `~/.codex/sessions/**/*.jsonl`
- capture `cwd` from `session_meta.payload.cwd`
- join `history.session_id` to the session metadata id
- convert integer epoch seconds in `ts` to timezone-aware datetimes
- classify slash commands by leading `/`

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/ingestion/test_codex_provider.py -q`
Expected: PASS

- [ ] **Step 5: Verify both providers together**

Run: `uv run pytest tests/ingestion/test_claude_provider.py tests/ingestion/test_codex_provider.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add ai_monitor/ingestion/providers/codex.py tests/fixtures/codex/history.jsonl tests/fixtures/codex/sessions/2026/04/01/rollout-sample.jsonl tests/ingestion/test_codex_provider.py
git commit -m "feat: add Codex history ingestion"
```

## Task 5: SQLite Schema And Aggregate Queries

**Files:**
- Create: `ai_monitor/db/schema.py`
- Create: `ai_monitor/db/queries.py`
- Test: `tests/ingestion/test_service.py`

- [ ] **Step 1: Write the failing database aggregation tests**

```python
def test_rebuild_creates_day_week_month_aggregates(tmp_path: Path) -> None:
    database_path = tmp_path / "usage.db"
    service = IngestionService(database_path=database_path, providers=[fixture_provider()])

    report = service.refresh()
    rows = fetch_aggregate_rows(database_path)

    assert report.prompt_event_count == 3
    assert {row.period_type for row in rows} == {"day", "week", "month"}
    assert rows[0].conversation_count >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/ingestion/test_service.py -q`
Expected: FAIL because the service and schema do not exist yet.

- [ ] **Step 3: Implement the SQLite schema and aggregate rebuild**

Schema tables:
- `conversations`
- `prompt_events`
- `aggregate_metrics`
- `refresh_runs`

Aggregate key columns:
- `period_type`
- `period_start`
- `project_name`
- `provider`

Aggregation rules:
- `conversation_count` is distinct conversation ids within the bucket
- `text_prompt_count` counts only `text_prompt`
- `slash_command_count` counts only `slash_command`

The refresh strategy for v1 should:
- clear normalized tables
- repopulate them from providers
- recompute all aggregates in one transaction

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/ingestion/test_service.py -q`
Expected: PASS

- [ ] **Step 5: Run targeted quality checks**

Run: `uv run ruff check ai_monitor/db ai_monitor/ingestion/service.py tests/ingestion/test_service.py`
Expected: exit 0

- [ ] **Step 6: Commit**

```bash
git add ai_monitor/db/schema.py ai_monitor/db/queries.py ai_monitor/ingestion/service.py tests/ingestion/test_service.py
git commit -m "feat: add normalized usage database"
```

## Task 6: FastAPI App And Metrics API

**Files:**
- Create: `ai_monitor/config.py`
- Create: `ai_monitor/server/app.py`
- Create: `ai_monitor/server/routes.py`
- Test: `tests/conftest.py`
- Test: `tests/server/test_metrics_api.py`

- [ ] **Step 1: Write the failing API tests**

```python
def test_metrics_endpoint_returns_selected_period_data(client: TestClient) -> None:
    response = client.get("/api/metrics", params={"period": "week"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["period"] == "week"
    assert "rows" in payload


def test_refresh_endpoint_returns_refresh_report(client: TestClient) -> None:
    response = client.post("/api/refresh")

    assert response.status_code == 200
    assert "last_refreshed_at" in response.json()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/server/test_metrics_api.py -q`
Expected: FAIL because the app does not exist yet.

- [ ] **Step 3: Implement the FastAPI app**

Routes:
- `GET /api/metrics`
- `POST /api/refresh`
- `GET /health`
- `GET /`

Config responsibilities:
- default provider paths under the current user home directory
- local SQLite path in the project root
- overridable via environment variables if needed

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/server/test_metrics_api.py -q`
Expected: PASS

- [ ] **Step 5: Verify typing and linting on server code**

Run: `uv run ruff check ai_monitor/server ai_monitor/config.py tests/server/test_metrics_api.py`
Expected: exit 0

Run: `uv run ty check`
Expected: exit 0

- [ ] **Step 6: Commit**

```bash
git add ai_monitor/config.py ai_monitor/server/app.py ai_monitor/server/routes.py tests/conftest.py tests/server/test_metrics_api.py
git commit -m "feat: add usage metrics API"
```

## Task 7: Dashboard UI

**Files:**
- Create: `ai_monitor/server/templates/index.html`
- Create: `ai_monitor/server/static/app.css`
- Create: `ai_monitor/server/static/app.js`
- Test: `tests/server/test_dashboard.py`

- [ ] **Step 1: Write the failing dashboard tests**

```python
def test_dashboard_renders_summary_labels(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    body = response.text
    assert "Conversations" in body
    assert "Text Prompts" in body
    assert "Slash Commands" in body
    assert "Day" in body
    assert "Week" in body
    assert "Month" in body
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/server/test_dashboard.py -q`
Expected: FAIL because the template does not exist yet.

- [ ] **Step 3: Build the minimal dashboard**

UI requirements:
- summary cards
- day/week/month controls
- project filter
- provider filter
- refresh button
- aggregate table
- time-series chart placeholder or lightweight inline chart
- refresh diagnostics panel

Style requirements:
- avoid generic default admin styling
- define CSS variables
- work on desktop and mobile

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/server/test_dashboard.py -q`
Expected: PASS

- [ ] **Step 5: Smoke-test the full app locally**

Run: `uv run pytest tests/server/test_metrics_api.py tests/server/test_dashboard.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add ai_monitor/server/templates/index.html ai_monitor/server/static/app.css ai_monitor/server/static/app.js tests/server/test_dashboard.py
git commit -m "feat: add AI usage dashboard UI"
```

## Task 8: End-To-End Integration And Docs Finalization

**Files:**
- Modify: `README.md`
- Modify: `DEV.md`
- Modify: `tests/ingestion/test_service.py`
- Modify: `tests/server/test_metrics_api.py`

- [ ] **Step 1: Add the failing end-to-end coverage**

```python
def test_refresh_then_query_returns_fixture_metrics(client: TestClient) -> None:
    refresh_response = client.post("/api/refresh")
    assert refresh_response.status_code == 200

    metrics_response = client.get("/api/metrics", params={"period": "day"})
    payload = metrics_response.json()

    assert any(row["project_name"] == "zk-chains-registry" for row in payload["rows"])
```

- [ ] **Step 2: Run test to verify it fails if integration wiring is incomplete**

Run: `uv run pytest tests/ingestion/test_service.py tests/server/test_metrics_api.py -q`
Expected: FAIL until the end-to-end wiring is complete.

- [ ] **Step 3: Complete docs and small fixes**

Ensure docs cover:
- installation with `uv sync --dev`
- launching with `uv run uvicorn ai_monitor.server.app:app --reload`
- refreshing data from the UI and API
- default log source locations
- how to add a new provider

- [ ] **Step 4: Run full project verification**

Run: `uv run pytest -q`
Expected: PASS

Run: `uv run ruff check .`
Expected: exit 0

Run: `uv run ty check`
Expected: exit 0

- [ ] **Step 5: Commit**

```bash
git add README.md DEV.md tests/ingestion/test_service.py tests/server/test_metrics_api.py
git commit -m "docs: finalize AI monitor usage workflow"
```

## Task 9: Publish To GitHub Under `cytadela8-ai`

**Files:**
- Modify: `.git/config` via git commands

- [ ] **Step 1: Verify remote repository target**

Run: `gh repo view cytadela8-ai/ai-monitor`
Expected: Either repository details or a not-found response.

- [ ] **Step 2: Create the repository if needed**

Run: `gh repo create cytadela8-ai/ai-monitor --public --source=. --remote=origin --push`
Expected: GitHub repository created and current branch pushed.

If the repository already exists:

Run: `git remote add origin https://github.com/cytadela8-ai/ai-monitor.git`
Expected: remote added

Run: `git push -u origin main`
Expected: branch published

- [ ] **Step 3: Verify publication**

Run: `gh repo view cytadela8-ai/ai-monitor --web=false`
Expected: repository metadata returned successfully

- [ ] **Step 4: Record publish details in README if needed**

If the published repo name differs from the local directory assumptions, update docs before the
final publish commit.

## Notes For Execution

- Before adding dependencies in `pyproject.toml`, look up the current stable versions rather than
  guessing from memory.
- Keep the ingestion layer free of FastAPI imports.
- Keep the server layer free of raw filesystem parsing.
- Prefer full refresh rebuilds first; incremental refresh is out of scope.
- If log formats differ from the sampled fields, extend fixtures first, then update providers.
